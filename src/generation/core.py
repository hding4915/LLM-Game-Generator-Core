from src.utils import call_llm
from src.generation.prompts import PROGRAMMER_PROMPT_TEMPLATE, FUZZER_GENERATION_PROMPT, MODULAR_PROMPT_TEMPLATE, STRUCTURAL_PROMPT_TEMPLATE
from src.generation.asset_gen import generate_assets
from src.generation.file_utils import save_code_to_file
from src.rag_service.rag import RagService, RagConfig
import os
import json
import re
import ast  # 用於靜態分析程式碼結構
import uuid  # [New] 用於生成唯一的 run_id

# 嘗試導入 Langchain 文字切分器，用於 RAG 預處理
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    print("[Warning] Langchain not found. RAG code splitting will be limited.")


def generate_code(
        gdd_context: str,
        asset_json: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    """
    Generate monolithic code (Legacy/Fallback).
    """
    full_prompt = f"""
    GDD:
    {gdd_context}

    ASSETS (JSON):
    {asset_json}

    Write the full code now following the Template.
    """
    return call_llm(PROGRAMMER_PROMPT_TEMPLATE, full_prompt, provider=provider, model=model, temperature=0.2)


def generate_structural_code(
        gdd_context: str,
        asset_json: str,
        provider: str = "mistral",
        model: str = "codestral-latest"
) -> list:
    """
    Generate a JSON list describing the file structure of the project.
    """
    print(f"[Member 2] Designing modular architecture using {model}...")

    prompt = STRUCTURAL_PROMPT_TEMPLATE.replace("{gdd_context}", gdd_context)
    prompt = prompt.replace("{asset_json}", asset_json)

    response = call_llm("You are a System Architect. Output only JSON.", prompt, provider=provider, model=model,
                        temperature=0.1)

    # Clean up response to ensure valid JSON
    json_str = re.sub(r'```json\s*|\s*```', '', response).strip()

    try:
        structure = json.loads(json_str)
        if isinstance(structure, list):
            print(f"[Member 2] Generated structure with {len(structure)} files.")
            return structure
        else:
            print("[Member 2] Warning: LLM returned valid JSON but not a list.")
            return []
    except json.JSONDecodeError as e:
        print(f"[Member 2] JSON Parsing Error: {e}\nResponse: {response[:100]}...")
        return []


def analyze_code_structure(code: str) -> dict:
    """
    使用 AST 分析程式碼，提取實際存在的 Classes, Functions 和 Global Variables。
    這能確保我們只讓 LLM import 真正存在的符號。
    """
    symbols = {"classes": [], "functions": [], "variables": []}
    try:
        # 確保解析前沒有 Markdown 標記 (防禦性檢查)
        clean_code = re.sub(r'```python\s*|```\s*', '', code).strip()
        tree = ast.parse(clean_code)

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                symbols["classes"].append(node.name)
            elif isinstance(node, ast.FunctionDef):
                symbols["functions"].append(node.name)
            elif isinstance(node, ast.Assign):
                # 提取全域變數 (例如 config.py 中的常數)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols["variables"].append(target.id)
    except Exception as e:
        print(f"[AST Analysis Warning] Could not parse code: {e}")
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
    print(f"[Member 2] Generating module: {filename}...")

    # 將依賴列表轉換為字串
    deps_str = ", ".join(dependencies) if dependencies else "None"

    # 建構 "允許 Import 的符號列表" 提示
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

    # 針對 config.py 的特殊強化指令
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

    prompt = f"""
    Write the Python code for the file: '{filename}'.

    PROJECT CONTEXT:
    GDD Summary: {gdd_context[:300]}...

    CURRENT FILE SPEC:
    - Filename: {filename}
    - Responsibility: {description}
    - Dependencies to Import: {deps_str}
    - Assets Available: {asset_json}

    RAG CONTEXT (Definitions from existing files):
    {rag_context}

    {allowlist_str}

    INSTRUCTIONS:
    1. **IMPORT EXTERNAL LIBS**: If you use `pygame`, `random`, `math`, `sys` etc., you MUST import them explicitly.
    2. **IMPORT INTERNAL DEPS**: You MUST import the classes/functions listed in 'Dependencies' from their respective filenames (without .py).
    3. **CHECK ALLOWLIST**: Refer to the 'STRICT IMPORT ALLOWLIST' above. Do not import symbols not listed there.
    4. **NO RE-IMPLEMENTATION**: Do NOT define classes that are already shown in RAG CONTEXT. Use the imports.
    5. **CHECK SIGNATURES**: Look at RAG CONTEXT for `__init__` methods. Pass ONLY the arguments defined there.
    6. **IMPLEMENTATION**: Implement only the logic described in 'Responsibility'.
    7. **Output**: Return ONLY the raw Python code.

    {special_instruction}
    """

    return call_llm(MODULAR_PROMPT_TEMPLATE, prompt, provider=provider, model=model, temperature=0.2)


def generate_fuzzer_logic(
        gdd_context: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    """
    Generate a fuzzer logic according to the given gdd context.
    """
    print("[Member 2] Start to generate fuzzer logic")
    prompt = FUZZER_GENERATION_PROMPT.replace("{gdd}", gdd_context)
    print("[Member 2] Generating the custom fuzzer test script (Fuzzer)...")
    return call_llm("You are a QA Engineer.", prompt, provider=provider, model=model, temperature=0.2)


def run_core_phase(
        gdd_context: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        use_modular: bool = True
) -> str:
    """
    Run the game generation pipeline.

    :param use_modular: If True, uses the new structural generation + RAG-ready flow.
    """

    print("[Member 2] Start to generate the assets (JSON)...")
    assets = generate_assets(gdd_context, provider, model)
    short_assets = str(assets)[:1000] + "..." if len(str(assets)) > 1000 else str(assets)

    main_file_path = None
    output_dir = None

    # [New] 生成唯一的 Run ID，用於資料夾命名和 RAG 隔離
    run_id = str(uuid.uuid4())
    print(f"[Member 2] Current Run ID: {run_id}")

    # [New] 專案符號表，用於存儲每個檔案生成的實際符號 (AST analysis results)
    project_symbol_table = {}

    if use_modular:
        print("[Member 2] Start to generate code structure (Modular Mode)...")
        structure = generate_structural_code(gdd_context, short_assets, provider=provider, model=model)

        if not structure:
            print("[Member 2] Structure generation failed. Falling back to monolithic generation.")
            raw_code = generate_code(gdd_context, short_assets, provider, model)
            main_file_path = save_code_to_file(raw_code)
        else:
            # --- RAG Initialization ---
            print("[Member 2] Initializing RAG Service for Code Memory...")
            rag_config = RagConfig(collection_name="game_gen")
            rag_service = RagService(rag_config=rag_config)

            # --- CLEAR RAG MEMORY ---
            # 保留 reset 機制以防萬一，但依賴 run_id 做主要隔離
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

            # 優化排序邏輯
            structure.sort(key=lambda x: len(x.get('dependencies', [])))
            structure.sort(key=lambda x: 1 if 'main' in x['filename'].lower() else 0)

            for file_info in structure:
                filename = file_info.get('filename')
                desc = file_info.get('description', '')
                deps = file_info.get('dependencies', [])

                # [Safety Net] 自動補全 main.py 的依賴
                if filename == 'main.py' and not deps:
                    print(
                        f"   [!] main.py has no dependencies listed. Auto-injecting all previous modules for context.")
                    deps = [f.get('filename') for f in structure if f.get('filename') != 'main.py']

                # --- Prepare Allowlist from Symbol Table ---
                current_dep_symbols = {}
                for dep in deps:
                    # 嘗試各種可能的檔名匹配 (e.g., 'utils' vs 'utils.py')
                    dep_keys = [dep, dep if dep.endswith('.py') else f"{dep}.py"]
                    for key in dep_keys:
                        if key in project_symbol_table:
                            current_dep_symbols[key] = project_symbol_table[key]
                            break
                # -------------------------------------------

                # --- RAG Retrieval ---
                rag_context = ""
                if deps:
                    # [Update] 查詢指令更加強調 Functions 名稱
                    query_text = f"Show me the class definitions, __init__ methods, ALL exported function names, and ALL global constants in: {', '.join(deps)}"
                    print(f"   -> Querying RAG for dependencies: {deps}...")

                    # [Update] 使用 run_id 過濾，只檢索本次生成的內容
                    results = rag_service.query(query_text, filters={"run_id": run_id}, n_results=3)

                    if results and 'documents' in results and results['documents']:
                        retrieved_docs = results['documents'][0]
                        rag_context = "\n\n".join(retrieved_docs)
                        print(f"   -> Retrieved {len(retrieved_docs)} context chunks.")
                # ---------------------

                code_content = generate_module_code(
                    filename, desc, deps, gdd_context, short_assets, rag_context,
                    dependency_symbols=current_dep_symbols,  # 傳入白名單
                    provider=provider, model=model
                )

                # [Fix] Clean markdown code blocks BEFORE analysis to ensure AST works
                # Some LLMs output markdown despite "raw code" instruction
                clean_code = re.sub(r'```python\s*|```\s*', '', code_content).strip()

                # [New] 分析生成的程式碼並更新符號表
                print(f"   -> Analyzing symbols in {filename}...")
                file_symbols = analyze_code_structure(clean_code)  # Use clean_code
                project_symbol_table[filename] = file_symbols
                print(
                    f"      Found: {len(file_symbols['classes'])} classes, {len(file_symbols['functions'])} functions, {len(file_symbols['variables'])} vars")

                # Wrap clean code in markdown for save_code_to_file to prevent "Unable to parse" warnings
                # assuming save_code_to_file expects markdown blocks
                markdown_wrapped_code = f"```python\n{clean_code}\n```"

                if output_dir is None:
                    directory = "output"
                    # [Update] 使用 run_id 作為資料夾名稱
                    output_dir = os.path.join(directory, run_id)
                    print(f"[Member 2] Creating output directory: {output_dir}")

                    saved_path = save_code_to_file(markdown_wrapped_code, filename=filename,
                                                   output_dir=output_dir)  # Use wrapped
                    if saved_path:
                        output_dir = os.path.dirname(saved_path)
                    if 'main.py' in filename:
                        main_file_path = saved_path
                else:
                    saved_path = save_code_to_file(markdown_wrapped_code, output_dir=output_dir,
                                                   filename=filename)  # Use wrapped
                    if 'main.py' in filename:
                        main_file_path = saved_path

                # --- RAG Indexing (Insertion) ---
                print(f"   -> Indexing {filename} into RAG...")
                # Use clean_code for RAG
                if text_splitter and clean_code:
                    try:
                        docs = text_splitter.create_documents([clean_code], metadatas=[{"filename": filename, "run_id": run_id}])
                        for doc in docs:
                            # [Update] 加入 run_id 到 metadata，確保資料隔離
                            doc.metadata["run_id"] = run_id
                            rag_service.insert(doc.page_content, doc.metadata)
                    except Exception as e:
                        print(f"   [!] Error splitting/inserting code: {e}")
                else:
                    # [Update] 加入 run_id 到 metadata
                    rag_service.insert(clean_code, {"filename": filename, "run_id": run_id})
                # --------------------------------

            if not main_file_path and output_dir:
                main_file_path = os.path.join(output_dir, "main.py")

    else:
        # Legacy Mode
        print("[Member 2] Start to generate monolithic code...")
        raw_code = generate_code(gdd_context, short_assets, provider, model)
        print("[Member 2] Saving file...")
        main_file_path = save_code_to_file(raw_code)

    # Generate Fuzzer
    if main_file_path:
        fuzzer_logic_code = generate_fuzzer_logic(gdd_context, provider, model)
        output_dir = os.path.dirname(main_file_path)
        save_code_to_file(fuzzer_logic_code, output_dir=output_dir, filename="fuzz_logic.py")

    return main_file_path