import os
import re
import logging
from typing import Optional, Generator

from src.utils import call_llm
from src.testing.prompts import FIXER_PROMPT, LOGIC_REVIEW_PROMPT, LOGIC_FIXER_PROMPT, FUZZER_PROMPT
from src.generation.file_utils import save_code_to_file
from src.rag_service.rag import RagService, RagConfig
from src.testing.fuzzer import run_fuzz_test
from src.testing.static_code_analyzer import get_project_symbols, check_cross_file_calls, static_code_check
from config import config

logger = logging.getLogger("【Member3-Fixer】")
logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.DEBUG))
logger.propagate = False

if not logger.handlers:
    formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fh = logging.FileHandler(config.LOG_FILE_PATH, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def extract_rag_context(rag_service: RagService, query: str, run_id: str) -> str:
    """
    Get relevant code snippets from RAG service based on the query and run_id.
    :param rag_service: the instance of RagService
    :param query: the query string
    :param run_id: the run_id to filter documents
    :return: the concatenated relevant code snippets
    """
    results = rag_service.query(question=query, filters={"run_id": run_id}, n_results=7)

    if results and 'documents' in results and results['documents']:
        actual_docs = results['documents'][0]
        return "\n\n".join([f"References {i + 1}:\n{doc}" for i, doc in enumerate(actual_docs)])
    return "無相關參考程式碼片段。"


def game_logic_check_with_rag(file_path: str, provider: str = "openai",
                              model: str = "gpt-4o-mini", run_id: str = "") -> tuple[bool, str]:
    """使用 RAG 查詢相關程式碼片段進行邏輯檢查"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        import_lines = [line for line in code.splitlines() if "import" in line]
        import_context_query = "\n".join(import_lines)

        rag_service = RagService(rag_config=RagConfig(collection_name="game_gen"))

        query = f"Provide definitions for symbols used in: {os.path.basename(file_path)}\n{import_context_query}"
        context = extract_rag_context(rag_service, query, run_id)

        prompt = LOGIC_REVIEW_PROMPT.format(code=code, context=context)
        response = call_llm("You are a game logic reviewer.", prompt, provider=provider, model=model)

        logger.info(f"檔案 {os.path.basename(file_path)} 邏輯審查完畢。")
        logger.debug(f"LLM 回應摘要: {response[:200]}...")

        if "PASS" in response.upper():
            logger.info(f"檔案 {os.path.basename(file_path)} 邏輯檢查通過 ✅")
            return True, ""

        return False, response
    except Exception as e:
        logger.exception(f"邏輯檢查過程中發生錯誤: {file_path}")
        return False, str(e)


def run_fix(file_path: str, error_message: str, provider: str = "openai",
            model: str = "gpt-4o-mini", fix_type: str = "syntax", run_id: str = "",
            gdd: Optional[str] = "") -> tuple[str | None, str]:
    """
    The main function to fix code based on error type (syntax or logic).
    :param file_path: str: The path to the broken code file
    :param error_message: str: The error message to guide the fix
    :param provider: str: LLM provider
    :param model: str: LLM model name
    :param fix_type: str: "syntax" or "logic"
    :param run_id: str: The run_id for RAG context filtering
    :param gdd: str: Game Design Document for logic fixes
    """
    logger.info(f"🛠️ 開始修復 {os.path.basename(file_path)} | 類型: {fix_type}")

    if not os.path.exists(file_path):
        logger.error(f"檔案不存在: {file_path}")
        return None, "找不到原始代碼檔案"

    with open(file_path, "r", encoding="utf-8") as f:
        broken_code = f.read()

    rag_service = RagService(rag_config=RagConfig(collection_name="game_gen"))
    query = f"{fix_type.capitalize()} fix reference: {os.path.basename(file_path)}\n{error_message[:100]}"
    context = extract_rag_context(rag_service, query, run_id)

    if fix_type == "syntax":
        full_prompt = FIXER_PROMPT.format(code=broken_code, error=error_message)
        full_prompt += f"\n\nContext:\n{context}"
        response = call_llm("You are a Code error Fixer.", full_prompt, provider=provider, model=model)
    else:
        full_prompt = LOGIC_FIXER_PROMPT.format(code=broken_code, error=error_message, gdd=gdd, context=context)
        response = call_llm("You are a code logics fixer.", full_prompt, provider=provider, model=model)

    output_dir = os.path.dirname(file_path)
    new_path = save_code_to_file(response, output_dir=output_dir, filename=os.path.basename(file_path))
    file_name = os.path.basename(file_path)

    if new_path:
        logger.info(f"✅ {os.path.basename(file_path)} 修復成功。")
        rag_service.delete_by_metadata({"filename": file_name, "run_id": run_id})
        rag_service.insert_with_chunk(response, metadata={"filename": file_name, "run_id": run_id})
        return new_path, response

    logger.error(f"❌ {os.path.basename(file_path)} 存檔失敗。")
    return None, response

def run_fix_loop(gdd: str, file_path: str, provider: str = "openai",
                 model: str = "gpt-4o-mini") -> Generator[str, None, None]:
    """
    Validate and fix the entire project iteratively using static code analysis,
    gdd: str: Game Design Document for logic fixes
    file_path: str: The main game file path to test
    provider: str: LLM provider
    model: str: LLM model name
    """
    yield f"data: [Member 3] 啟動專案級驗證流程...\n\n"

    # Get all Python files in the project folder
    folder_path = os.path.dirname(file_path)
    files = [f for f in os.listdir(folder_path) if f.endswith(".py")]
    full_path_files = [os.path.join(folder_path, f) for f in files]
    # The folder name is run_id
    run_id = os.path.basename(folder_path)

    symbols_table = get_project_symbols(folder_path)

    logger.info(f"--- 專案驗證開始 | RunID: {run_id} | 檔案清單: {files} ---")

    # Static syntax check for all files
    for file in full_path_files:
        valid, err = static_code_check(file)
        if not valid:
            yield f"data: ❌ {file} 語法錯誤，正在修復...\n\n"
            res_path, _ = run_fix(file, err, provider, model, "syntax", run_id)
            if not res_path:
                yield f"data: ❌ 檔案 {file} 無法修復語法，終止。\n\n"
                return
            yield f"data: ✅ {file} 語法已修復。\n\n"

    # Cross-file static analysis (semantic check)
    for file in full_path_files:
        errors = check_cross_file_calls(file, symbols_table)
        if errors:
            for err in errors:
                yield f"data: ❌ {file} 發現跨檔案呼叫錯誤，正在修復...\n\n"
                res_path, _ = run_fix(file, err, provider, model, "syntax", run_id)
                if not res_path:
                    yield f"data: ❌ 檔案 {file} 無法修復跨檔案錯誤，終止。\n\n"
                    return
            yield f"data: ✅ {file} 跨檔案呼叫錯誤已修復。\n\n"

    success, err = run_fuzz_test(file_path, 10)
    file_regex = r'File ".*[/\\]([^/\\]+\.py)"'
    while not success:
        all_files = re.findall(file_regex, err)
        unique_error_files = set([f for f in all_files if f != "main_fuzz_temp.py"])
        if not unique_error_files:
            unique_error_files = {os.path.basename(file_path)}

        logger.debug(f"偵測到錯誤檔案清單: {unique_error_files}")
        yield f"data: ❌ Fuzzer 測試發現錯誤，正在修正...\n\n"

        for file in unique_error_files:
            logger.info(f"🛠️ 準備修復檔案: {file}")
            full_path = os.path.join(folder_path, file)

            res_path, _ = run_fix(full_path, err, provider, model, "logic", run_id, gdd)

            if not res_path:
                yield f"data: ❌ 檔案 {file} 無法解決 Fuzzer 錯誤，終止。\n\n"
                return

        yield f"data: ✅ 相關檔案已修復，重新進行壓力測試...\n\n"
        success, err = run_fuzz_test(file_path, 10)

    # Logic check with RAG
    for file in full_path_files:
        valid, err = game_logic_check_with_rag(file_path, provider, model, run_id)
        if not valid:
            yield f"data: ❌ {file} 發現邏輯瑕疵，正在修正...\n\n"
            res_path, _ = run_fix(file, err, provider, model, "logic", run_id, gdd)
            if not res_path:
                yield f"data: ❌ 檔案 {file} 無法解決邏輯錯誤，終止。\n\n"
                return
            yield f"data: ✅ {file} 邏輯優化完成。\n\n"

    logger.info(f"專案 {run_id} 驗證全數通過。")
    yield "data: RESULT_SUCCESS: 專案通過 Member 3 所有驗證！\n\n"