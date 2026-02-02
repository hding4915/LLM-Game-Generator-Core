from typing import Optional, Any, Generator

from src.utils import call_llm
from src.testing.prompts import FIXER_PROMPT, LOGIC_REVIEW_PROMPT, LOGIC_FIXER_PROMPT
from src.generation.file_utils import save_code_to_file
from src.rag_service.rag import RagService, RagConfig
import os
import ast

def static_code_check(file_path: str) -> tuple[bool, str]:
    """
    Use Python ast module, inspecting the syntax errors.
    @:return (syntax validity, error message)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        ast.parse(code)
        return True, "語法檢查通過 ✅"
    except SyntaxError as e:
        return False, f"語法錯誤 ❌: {e}"
    except Exception as e:
        return False, f"其他錯誤 ❌: {e}"


def game_logic_check_with_rag(file_path: str, provider: str = "openai",
                              model: str = "gpt-4o-mini", run_id: str = "") -> tuple[bool, str]:
    """
    使用 RAG 查詢相關程式碼片段進行邏輯檢查
    """
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    # 初始化 RAG
    rag_config = RagConfig(collection_name="game_gen")
    rag_service = RagService(rag_config=rag_config)

    # 使用 RAG 查詢相關程式碼
    query = f"遊戲邏輯檢查: {os.path.basename(file_path)}\n"
    relevant_docs = rag_service.query(question=query, filters={"run_id": run_id}, n_results=3)

    # 組合相關上下文
    context = "\n\n".join([f"參考片段 {i + 1}:\n{doc}" for i, doc in enumerate(relevant_docs)])

    prompt = LOGIC_REVIEW_PROMPT.format(
        code=code,
        context=context
    )

    response = call_llm(
        "You are a game logic reviewer.",
        prompt,
        provider=provider,
        model=model
    )

    print(f"[Member 3]: RAG 邏輯檢查回應 {response[:100]}...")

    if "PASS" in response.upper():
        return True, ""
    return False, response

def run_fix(file_path: str, error_message: str, provider: str = "openai",
            model: str = "gpt-4o-mini", fix_type: str = "syntax", run_id: str="",
            gdd: Optional[str] = "") -> tuple[str | None, str]:
    """
    Auto Fix Loop: Read Codes -> Submit Errors -> Get new codes -> save
    The first return is the path to the fixed file.
    The second return is the result message.
    """
    print(f"[Member 3] 正在嘗試修復代碼... (Error: {error_message[:50]}...)")

    # Read the broken codes
    if not os.path.exists(file_path):
        return None, "找不到原始代碼檔案"

    with open(file_path, "r", encoding="utf-8") as f:
        broken_code = f.read()

    response: str = ""

    if fix_type == "syntax":
        # Insert the codes to the prompt
        fix_syntax_full_prompt: str = FIXER_PROMPT.format(code=broken_code, error=error_message)
        # Call LLM for fixing
        response = call_llm("You are a Code error Fixer.", fix_syntax_full_prompt,
                          provider=provider, model=model)
    elif fix_type == "logic":
        rag_config = RagConfig(collection_name="game_gen")
        rag_service = RagService(rag_config=rag_config)

        query = f"Logic fix: {os.path.basename(file_path)}\n{error_message[:200]}"
        relevant_docs = rag_service.query(question=query, filters={"run_id": run_id}, n_results=3)

        context = "\n\n".join([f"Reference example {i+1}:\n{doc}"
                              for i, doc in enumerate(relevant_docs)])

        fix_logic_full_prompt: str = LOGIC_FIXER_PROMPT.format(
            code=broken_code,
            error=error_message,
            gdd=gdd,
            context=context
        )
        response = call_llm("You are a code logics fixer.", fix_logic_full_prompt,
                          provider=provider, model=model)

    # Save the fixed files (truncate)
    output_dir: str = os.path.dirname(file_path)
    new_path: str | None = save_code_to_file(response, output_dir=output_dir)

    if new_path:
        return new_path, response
    else:
        return None, response


def run_fix_loop(gdd: str, file_path: str, provider: str = "openai",
                 model: str = "gpt-4o-mini") -> Generator[str, None, None]:
    """
    Generator function for SSE (Server-Sent Events).
    Yields strings in the format: "data: <message>\n\n"
    """
    game_is_valid = False
    error_msg = ""

    yield f"data: [Member 3] 收到需求，開始驗證: {os.path.basename(file_path)}\n\n"
    folder_path: str = os.path.dirname(file_path)
    files = os.listdir(folder_path)
    run_id = os.path.basename(folder_path)

    """
    # ------- Syntax check for every files in the folder -------
    """
    for file in files:
        if not file.endswith(".py"):
            continue
        syntax_is_valid, error_msg = static_code_check(os.path.join(folder_path, file))
        if not syntax_is_valid:
            yield f"data: ❌ 語法錯誤: {error_msg} (嘗試修復中...)\n\n"
            print(f"[Member3]: ❌ 語法錯誤: {error_msg}")

            file_path, error_msg = run_fix(
                os.path.join(folder_path, file), error_msg, provider, model, "syntax", run_id)
            if not file_path:
                yield f"data: ❌ 無法修復語法錯誤，停止驗證。\n\n"
                return
            yield f"data: ✅ 已修復語法錯誤，繼續驗證。\n\n"

    """
    # ------- Logic fix loop -------
    """
    for file in files:
        if not file.endswith(".py"):
            continue
        file_path = os.path.join(folder_path, file)
        logic_is_valid, error_msg = game_logic_check_with_rag(file_path, provider, model, run_id)
        if not logic_is_valid:
            yield f"data: ❌ 邏輯錯誤: {error_msg} (嘗試修復中...)\n\n"
            print(f"[Member3]: ❌ 邏輯錯誤: {error_msg}")

            file_path, error_msg = run_fix(file_path, error_msg, provider, model, "logic", run_id, gdd)
            if not file_path:
                yield f"data: ❌ 無法修復邏輯錯誤，停止驗證。\n\n"
                return
            yield f"data: ✅ 已修復邏輯錯誤，繼續驗證。\n\n"

    if game_is_valid:
        yield "data: RESULT_SUCCESS: 程式碼通過所有驗證！\n\n"
    else:
        yield "data: RESULT_FAIL: 已達最大重試次數，驗證失敗。\n\n"