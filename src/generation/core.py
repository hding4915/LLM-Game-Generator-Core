from src.testing.static_code_analyzer import static_code_check
from src.utils import call_llm
from src.generation.prompts import *
from src.generation.asset_gen import generate_assets
from src.generation.file_utils import save_code_to_file
from src.rag_service.rag import RagService, RagConfig
from src.code_parsing.utils import extract_code_block, extract_code_signatures
from config import config
import os
import json
import re
import ast
import uuid
import logging


logger = logging.getLogger("Member2-Generator")
logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.DEBUG))


TEMPERATURE = 0.1


try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    logging.info("[Warning] Langchain not found. RAG code splitting will be limited.")


def _code_review_process(code, provider, model):
    """
    自定義的程式碼審查流程：先檢查語法，再檢查邏輯
    """
    # Syntax Check, creating tempfile
    temp_filename = f"temp_check_{uuid.uuid4().hex}.py"
    with open(temp_filename, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        is_valid, error_msg = static_code_check(temp_filename)
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    if not is_valid:
        return f"SYNTAX ERROR DETECTED: {error_msg}\nPlease fix the syntax error."

    # 2. Logic Check using LLM
    review_input = f"CODE:\n{code}\n\nCheck this code."
    review_feedback = call_llm(CODE_REVIEWER_PROMPT, review_input, provider=provider, model=model, temperature=0.1)

    return review_feedback


def generate_code(
        gdd_context: str,
        asset_json: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    """
    Generate monolithic code with Review Agent Loop.
    """
    full_prompt = f"""
    GDD:
    {gdd_context}

    ASSETS (JSON):
    {asset_json}

    Write the full code now following the Template.
    """
    current_code = call_llm(PROGRAMMER_PROMPT_TEMPLATE, full_prompt, provider=provider, model=model,
                            temperature=TEMPERATURE)

    logging.info("進入程式碼審查迴圈...")
    max_retries = 3

    for i in range(max_retries):
        feedback = _code_review_process(current_code, provider, model)

        if "PASS" in feedback.upper() and len(feedback) < 50:
            logging.info(f"程式碼審查通過 ✅ (Round {i + 1})")
            return current_code

        logging.warning(f"程式碼審查未通過 ❌ (Round {i + 1}): {feedback[:100]}...")

        # Update prompt with feedback for revision
        revise_prompt = f"{full_prompt}\n\n[Previous Code with Errors]:\n{current_code}\n\n[QA Feedback]:\n{feedback}\n\nPlease rewrite the code to fix these errors."

        # re-generate code based on feedback
        current_code = call_llm(PROGRAMMER_PROMPT_TEMPLATE, revise_prompt, provider=provider, model=model,
                                temperature=TEMPERATURE)

    return current_code

def generate_structural_code(
        gdd_context: str,
        asset_json: str,
        provider: str = "mistral",
        model: str = "codestral-latest"
) -> list:
    """
    Generate a JSON list describing the file structure of the project.
    """
    logging.info(f"Designing modular architecture using {model}...")

    prompt = STRUCTURAL_PROMPT_TEMPLATE.format(gdd_context=gdd_context, asset_json=asset_json)
    response = call_llm("You are a System Architect. Output only JSON.", prompt, provider=provider, model=model,
                        temperature=TEMPERATURE)
    # Clean up response to ensure valid JSON
    json_str = re.sub(r'```json\s*|\s*```', '', response).strip()

    try:
        structure = json.loads(json_str)
        if isinstance(structure, list):
            logging.info(f"Generated structure with {len(structure)} files.")
            return structure
        else:
            logging.warning("Warning: LLM returned valid JSON but not a list.")
            return []
    except json.JSONDecodeError as e:
        logging.error(f"JSON Parsing Error: {e}\nResponse: {response[:100]}...")
        return []


def analyze_code_structure(code: str) -> dict:
    """
    Analyze code structure using AST to extract actual Classes, Functions, and Global Variables.
    This ensures we only import symbols that actually exist.
    """
    symbols = {"classes": [], "functions": [], "variables": []}
    try:
        # Clean code using code_parsing utilities first
        clean_code = extract_code_block(code)
        tree = ast.parse(clean_code)

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbols["classes"].append(node.name)
            elif isinstance(node, ast.FunctionDef):
                symbols["functions"].append(node.name)
            elif isinstance(node, ast.Assign):
                # Extract global variables (e.g., constants in config.py)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols["variables"].append(target.id)
    except Exception as e:
        logging.exception(f"[AST Analysis Warning] Could not parse code: {e}")
    return symbols


def generate_module_code(
        filename: str,
        description: str,
        dependencies: list,
        gdd_context: str,
        asset_json: str,
        rag_context: str = "",
        dependency_symbols: dict = None,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    """
    Generate code for a specific module.
    """
    logging.info(f"Generating module: {filename}...")

    # Convert dependency list to string
    deps_str = ", ".join(dependencies) if dependencies else "None"

    # Construct "Allowlist of Imported Symbols" prompt
    allowlist_str = ""
    if dependency_symbols:
        allowlist_str += "\n=== STRICT IMPORT ALLOWLIST (Verification Required) ===\n"
        allowlist_str += "You may ONLY import the following symbols from dependencies:\n"
        for dep_file, symbols in dependency_symbols.items():
            allowlist_str += f"\nFile '{dep_file}':\n"
            if symbols['classes']:
                allowlist_str += f"  - Classes: {', '.join(symbols['classes'])}\n"
            if symbols['functions']:
                allowlist_str += f"  - Functions: {', '.join(symbols['functions'])}\n"
            if symbols['variables']:
                allowlist_str += f"  - Constants/Variables: {', '.join(symbols['variables'])}\n"

            if not any(symbols.values()):
                allowlist_str += "  - (No exportable symbols detected. Do NOT import anything from this file.)\n"
        allowlist_str += "\nIf a symbol you need is NOT in this list, define it locally.\n=======================================================\n"

    # Special enhanced instructions for config.py
    special_instruction = ""
    if "config" in filename.lower():
        special_instruction = """
        IMPORTANT FOR CONFIG: 
        You MUST include standard game constants to prevent import errors in other files.
        Always define:
        - SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE
        - FPS (Frames Per Second)
        - Colors (WHITE, BLACK, RED, GREEN, BLUE)
        - TILE_SIZE (if grid based)
        """

    prompt = MODULAR_CODE_PROMPT_TEMPLATE.format(
        filename=filename,
        gdd_context=gdd_context[:300],
        description=description,
        deps_str=deps_str,
        asset_json=asset_json,
        rag_context=rag_context,
        allowlist_str=allowlist_str,
        special_instruction=special_instruction
    )

    return call_llm(MODULAR_PROMPT_TEMPLATE, prompt, provider=provider, model=model, temperature=TEMPERATURE)


def generate_fuzzer_logic(
        gdd_context: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    """
    Generate a fuzzer logic according to the given gdd context.
    """
    logging.info("Start to generate fuzzer logic")
    prompt = FUZZER_GENERATION_PROMPT.replace("{gdd}", gdd_context)
    logging.info("Generating the custom fuzzer test script (Fuzzer)...")
    return call_llm("You are a QA Engineer.", prompt, provider=provider, model=model, temperature=TEMPERATURE)


def run_core_phase(
        gdd_context: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        use_modular: bool = True
) -> tuple[str, list]:
    """
    Run the game generation pipeline.

    :param use_modular: If True, uses the new structural generation + RAG-ready flow.
    """

    logging.info("Start to generate the assets (JSON)...")
    assets = generate_assets(gdd_context, provider, model)
    short_assets = str(assets)[:1000] + "..." if len(str(assets)) > 1000 else str(assets)

    main_file_path = None
    output_dir = None

    # [New] Generate unique Run ID for folder naming and RAG isolation
    run_id = str(uuid.uuid4())
    logging.info(f"Current Run ID: {run_id}")

    # [New] Project symbol table to store actual symbols generated for each file (AST analysis results)
    project_symbol_table = {}

    structure = None

    if use_modular:
        logging.info("Start to generate code structure (Modular Mode)...")
        structure = generate_structural_code(gdd_context, short_assets, provider=provider, model=model)

        if not structure:
            logging.info("Structure generation failed. Falling back to monolithic generation.")
            raw_code = generate_code(gdd_context, short_assets, provider, model)
            main_file_path = save_code_to_file(raw_code)
        else:
            # --- RAG Initialization ---
            logging.info("Initializing RAG Service for Code Memory...")
            rag_config = RagConfig(collection_name="game_gen")
            rag_service = RagService(rag_config=rag_config)

            # --- CLEAR RAG MEMORY ---
            rag_service.reset()
            # ------------------------

            # Setup Langchain Splitter for Python
            text_splitter = None
            if HAS_LANGCHAIN:
                text_splitter = RecursiveCharacterTextSplitter.from_language(
                    language=Language.PYTHON,
                    chunk_size=800,
                    chunk_overlap=100
                )
            # --------------------------

            # Optimize sort order
            structure.sort(key=lambda x: len(x.get('dependencies', [])))
            structure.sort(key=lambda x: 1 if 'main' in x['filename'].lower() else 0)

            for file_info in structure:
                filename = file_info.get('filename')
                desc = file_info.get('description', '')
                deps = file_info.get('dependencies', [])

                # [Safety Net] Auto-complete dependencies for main.py
                if filename == 'main.py' and not deps:
                    logging.info(
                        f"   [!] main.py has no dependencies listed. Auto-injecting all previous modules for context.")
                    deps = [f.get('filename') for f in structure if f.get('filename') != 'main.py']

                # --- Prepare Allowlist from Symbol Table ---
                current_dep_symbols = {}
                for dep in deps:
                    # Try various filename matches (e.g., 'utils' vs 'utils.py')
                    dep_keys = [dep, dep if dep.endswith('.py') else f"{dep}.py"]
                    for key in dep_keys:
                        if key in project_symbol_table:
                            current_dep_symbols[key] = project_symbol_table[key]
                            break
                # -------------------------------------------

                # --- RAG Retrieval ---
                rag_context = ""
                if deps:
                    # [Update] Query instructions emphasize Function names
                    query_text = f"Show me the class definitions, __init__ methods, ALL exported function names, and ALL global constants in: {', '.join(deps)}"
                    logging.info(f" -> Querying RAG for dependencies: {deps}...")

                    # [Update] Filter by run_id to retrieve only content generated in this run
                    results = rag_service.query(query_text, filters={"run_id": run_id}, n_results=3)

                    if results and 'documents' in results and results['documents']:
                        retrieved_docs = results['documents'][0]
                        rag_context = "\n\n".join(retrieved_docs)
                        logging.info(f" -> Retrieved {len(retrieved_docs)} context chunks.")
                # ---------------------

                code_content = generate_module_code(
                    filename, desc, deps, gdd_context, short_assets, rag_context,
                    dependency_symbols=current_dep_symbols,  # Pass Allowlist
                    provider=provider, model=model
                )

                # [Fix] Clean markdown code blocks BEFORE analysis to ensure AST works
                clean_code = extract_code_block(code_content)

                # [New] Analyze generated code and update symbol table
                logging.info(f" -> Analyzing symbols in {filename}...")
                file_symbols = analyze_code_structure(clean_code)  # Use clean_code
                project_symbol_table[filename] = file_symbols
                logging.info(
                    f"      Found: {len(file_symbols['classes'])} classes, {len(file_symbols['functions'])} functions, {len(file_symbols['variables'])} vars")

                # Wrap clean code in markdown for save_code_to_file to prevent "Unable to parse" warnings
                fence = "`" * 3
                markdown_wrapped_code = f"{fence}python\n{clean_code}\n{fence}"

                if output_dir is None:
                    directory = "output"
                    # [Update] Use run_id as folder name
                    output_dir = os.path.join(directory, run_id)
                    logging.info(f"Creating output directory: {output_dir}")

                # --- [Critical Fix] Ensure nested directories exist ---
                # If filename is "entities/tile.py", this creates "output/{run_id}/entities"
                full_save_path = os.path.join(output_dir, filename)
                os.makedirs(os.path.dirname(full_save_path), exist_ok=True)
                # ----------------------------------------------------

                saved_path = save_code_to_file(markdown_wrapped_code, filename=filename, output_dir=output_dir)

                if saved_path:
                    # Update main file path (if current file is main.py)
                    if 'main.py' in filename:
                        main_file_path = saved_path

                # --- RAG Indexing (Insertion) ---
                logging.info(f" -> Indexing {filename} into RAG...")
                # Use clean_code for RAG
                if text_splitter and clean_code:
                    try:
                        docs = text_splitter.create_documents([clean_code], metadatas=[{"filename": filename}])
                        for doc in docs:
                            # [Update] Add run_id to metadata for data isolation
                            doc.metadata["run_id"] = run_id
                            rag_service.insert(doc.page_content, doc.metadata)
                    except Exception as e:
                        logging.exception(f"[!] Error splitting/inserting code: {e}")
                else:
                    # [Update] Add run_id to metadata
                    rag_service.insert(clean_code, {"filename": filename, "run_id": run_id})
                # --------------------------------

            if not main_file_path and output_dir:
                main_file_path = os.path.join(output_dir, "main.py")

    else:
        # Legacy Mode
        logging.info("Start to generate monolithic code...")
        raw_code = generate_code(gdd_context, short_assets, provider, model)
        logging.info("Saving file...")
        main_file_path = save_code_to_file(raw_code)

    # Generate Fuzzer
    if main_file_path:
        fuzzer_logic_code = generate_fuzzer_logic(gdd_context, provider, model)
        output_dir = os.path.dirname(main_file_path)
        save_code_to_file(fuzzer_logic_code, output_dir=output_dir, filename="fuzz_logic.py")

    return main_file_path, structure