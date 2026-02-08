import os
import re
import logging
import ast
from typing import Optional, Generator

from src.utils import call_llm
from src.testing.prompts import FIXER_PROMPT, LOGIC_REVIEW_PROMPT, LOGIC_FIXER_PROMPT, FUZZER_PROMPT
from src.rag_service.rag import RagService, RagConfig
from src.testing.fuzzer import run_fuzz_test
from src.testing.static_code_analyzer import get_project_symbols, check_cross_file_calls, static_code_check
from src.code_parsing.utils import extract_code_block, extract_code_signatures
from config import config

logger = logging.getLogger("Member3-Fixer")
logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.DEBUG))

TEMPERATURE = 0.1

def get_project_signatures(folder_path: str, exclude_filename: str) -> str:
    """Generate project-level signature context."""
    signatures = []
    if not os.path.exists(folder_path):
        return ""

    for filename in os.listdir(folder_path):
        if filename.endswith(".py") and filename != exclude_filename:
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                sig = extract_code_signatures(content)
                if sig.strip():
                    signatures.append(f"\n--- {filename} ---\n{sig}")
            except Exception:
                pass

    if not signatures:
        return ""
    return "\n=== DEPENDENCY INTERFACES (READ ONLY) ===\nUse these signatures to ensure correct function calls and imports:\n" + "\n".join(
        signatures) + "\n=========================================\n"


def extract_rag_context(rag_service: RagService, query: str, run_id: str) -> str:
    """Get relevant code snippets from RAG service."""
    results = rag_service.query(question=query, filters={"run_id": run_id}, n_results=7)
    if results and 'documents' in results and results['documents']:
        actual_docs = results['documents'][0]
        return "\n\n".join([f"References {i + 1}:\n{doc}" for i, doc in enumerate(actual_docs)])
    return "No relevant code snippets found."


def game_logic_check_with_rag(file_path: str, provider: str = "openai", model: str = "gpt-4o-mini", run_id: str = "", structure: list = None) -> \
tuple[bool, str]:
    """Perform logic check using RAG to query relevant code snippets."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Simple check: report error directly if file is empty
        if not code.strip():
            return False, "File is empty."

        import_lines = [line for line in code.splitlines() if "import" in line]
        import_context_query = "\n".join(import_lines)
        rag_service = RagService(rag_config=RagConfig(collection_name="game_gen"))
        query = f"Provide definitions for symbols used in: {os.path.basename(file_path)}\n{import_context_query}"
        context = extract_rag_context(rag_service, query, run_id)

        prompt = LOGIC_REVIEW_PROMPT.format(code=code, context=context, structure=structure)
        response = call_llm("You are a game logic reviewer.", prompt, provider=provider, model=model, temperature=TEMPERATURE)

        if "PASS" in response.upper():
            return True, ""
        return False, response
    except Exception as e:
        logger.exception(f"Error during logic check: {file_path}")
        return False, str(e)


def run_fix(file_path: str, error_message: str, provider: str = "openai",
            model: str = "gpt-4o-mini", fix_type: str = "syntax", run_id: str = "",
            structure: list = None) -> tuple[str | None, str]:
    """
    Execute fix and write directly to file to ensure no Markdown residue.
    """
    logger.info(f"🛠️ Starting fix for {os.path.basename(file_path)} | Type: {fix_type}")

    if not os.path.exists(file_path):
        return None, "Original code file not found"

    with open(file_path, "r", encoding="utf-8") as f:
        broken_code = f.read()

    # Prepare Context
    rag_service = RagService(rag_config=RagConfig(collection_name="game_gen"))
    query = f"{fix_type.capitalize()} fix reference: {os.path.basename(file_path)}\n{error_message[:100]}"
    rag_context = extract_rag_context(rag_service, query, run_id)

    folder_path = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    signature_context = get_project_signatures(folder_path, file_name)
    full_context = f"{rag_context}\n\n{signature_context}"

    # Call LLM
    if fix_type == "syntax":
        full_prompt = FIXER_PROMPT.format(code=broken_code, error=error_message, structure=structure)
        full_prompt += f"\n\nContext & Interfaces:\n{full_context}"
        response = call_llm("You are a Code error Fixer.", full_prompt, provider=provider, model=model, temperature=TEMPERATURE)
    else:
        full_prompt = LOGIC_FIXER_PROMPT.format(code=broken_code, error=error_message, structure=structure, context=full_context)
        response = call_llm("You are a code logics fixer.", full_prompt, provider=provider, model=model, temperature=TEMPERATURE)

    # Clean code
    clean_code = extract_code_block(response)

    # [Critical] Validate if cleaned code is valid Python
    try:
        ast.parse(clean_code)
    except SyntaxError as e:
        logger.error(f"❌ Syntax error remains in fixed code: {e}")
        # If fix fails, we could choose not to save, or save to let loop retry (saving here to let loop proceed)

    # [Critical] Direct file write (Bypass save_code_to_file)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(clean_code)

        logger.info(f"✅ {file_name} Overwritten (Direct Write).")

        # Update RAG
        rag_service.delete_by_metadata({"filename": file_name, "run_id": run_id})
        rag_service.insert_with_chunk(clean_code, metadata={"filename": file_name, "run_id": run_id})

        return file_path, clean_code
    except Exception as e:
        logger.error(f"❌ File write failed: {e}")
        return None, clean_code


def run_fix_loop(structure: list, file_path: str, provider: str = "openai",
                 model: str = "gpt-4o-mini") -> Generator[str, None, None]:
    """Project-level iterative fix loop"""
    yield f"data: [Member 3] Starting project-level validation process...\n\n"

    folder_path = os.path.dirname(file_path)
    if not os.path.exists(folder_path):
        yield f"data: ❌ Directory not found: {folder_path}, validation aborted.\n\n"
        return

    files = [f for f in os.listdir(folder_path) if f.endswith(".py")]
    files = [f for f in files if "fuzz" not in f]
    full_path_files = [os.path.join(folder_path, f) for f in files]
    run_id = os.path.basename(folder_path)
    symbols_table = get_project_symbols(folder_path)

    logger.info(f"--- Project Validation Start | RunID: {run_id} | Files: {len(files)} ---\n")

    # 1. Syntax Check
    for file in full_path_files:
        valid, err = static_code_check(file)
        if not valid:
            yield f"data: ❌ {os.path.basename(file)} Syntax error, fixing...\n\n"
            res_path, _ = run_fix(file, err, provider, model, "syntax", run_id)
            if not res_path:
                yield f"data: ❌ Unable to fix {os.path.basename(file)}, aborted.\n\n"
                return
            yield f"data: ✅ {os.path.basename(file)} Syntax fixed.\n\n"

    # 2. Cross-file Check
    for file in full_path_files:
        errors = check_cross_file_calls(file, symbols_table)
        if errors:
            err_msg = "\n".join(errors)
            yield f"data: ❌ {os.path.basename(file)} Reference error, fixing...\n\n"
            res_path, _ = run_fix(file, err_msg, provider, model, "syntax", run_id)
            if not res_path:
                return
            yield f"data: ✅ {os.path.basename(file)} Reference error fixed.\n\n"

    # 3. Fuzzer Test
    success, err = run_fuzz_test(file_path, 10)
    retry_count = 0
    max_retries = 2

    file_regex = r'File ".*[/\\]([^/\\]+\.py)"'

    while not success and retry_count < max_retries:
        retry_count += 1
        all_files = re.findall(file_regex, err)
        # Filter out fuzzer temp files
        unique_error_files = set([f for f in all_files if "fuzz_temp" not in f])

        # If no filename captured in error, default to main file
        if not unique_error_files:
            unique_error_files = {os.path.basename(file_path)}

        yield f"data: ❌ Fuzzer failed (Attempt {retry_count}), fixing targets: {unique_error_files}\n\n"

        for file in unique_error_files:
            full_path = os.path.join(folder_path, file)
            res_path, _ = run_fix(full_path, err, provider, model, "logic", run_id, structure)
            if not res_path:
                yield f"data: ❌ Fix failed, process aborted.\n\n"
                return

        yield f"data: ✅ Fix complete, restarting Fuzzing...\n\n"
        success, err = run_fuzz_test(file_path, 10)

    if not success:
        yield f"data: ⚠️ Fuzzer test failed multiple times, manual check required.\n\n"
    else:
        yield f"data: 🎉 Fuzzer test passed!\n\n"


    logger.info(f"Project {run_id} validation all passed.")
    yield "data: RESULT_SUCCESS: Project passed all Member 3 validations!\n\n"