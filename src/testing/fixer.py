from typing import Optional

from src.utils import call_llm
from src.testing.prompts import FIXER_PROMPT, LOGIC_REVIEW_PROMPT, LOGIC_FIXER_PROMPT
from src.generation.file_utils import save_code_to_file
from src.testing.fuzzer import run_fuzz_test
from config import config
from flask import flash
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

def game_logic_check(gdd:str ,file_path: str, provider: str = "openai", model: str = "gpt-4o-mini") -> tuple[bool, str]:
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
    prompt = LOGIC_REVIEW_PROMPT.format(code=code, gdd=gdd)
    response = call_llm("You are a code logic reviewer.",
             prompt,
             provider=provider,
             model=model
    )
    print(f"[Member 3]: response of game_logic_check {response}")
    if "PASS" in response.upper() : return True, ""
    return False, response

def run_fix(file_path: str, error_message: str, provider: str = "openai"
                 , model: str  = "gpt-4o-mini", fix_type: str="syntax", gdd: Optional[str]="") -> tuple[str | None, str]:
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

    response: str  = ""

    if fix_type == "syntax":
        # Insert the codes to the prompt
        fix_syntax_full_prompt: str = FIXER_PROMPT.format(code=broken_code, error=error_message)
        # Call LLM for fixing
        response = call_llm("You are a Code error Fixer.", fix_syntax_full_prompt, provider=provider, model=model)
    elif fix_type == "logic":
        fix_logic_full_prompt: str = LOGIC_FIXER_PROMPT.format(code=broken_code, error=error_message, gdd=gdd)
        response = call_llm("You are a code logics fixer.", fix_logic_full_prompt, provider=provider, model=model)

    # Save the fixed files (truncate)
    output_dir: str = os.path.dirname(file_path)
    new_path: str | None = save_code_to_file(response, output_dir=output_dir)

    if new_path:
        return new_path, "修復完成，已更新代碼。"
    else:
        return None, "AI 無法生成有效的 Python 代碼區塊。"

def run_fix_loop(gdd: str, file_path: str, provider: str = "openai",
                 model: str = "gpt-4o-mini") -> bool:
    """
    :param gdd:
    :param file_path:
    :param provider:
    :param model:
    :return: (fixed_file_path, result)
    """
    print(f"[Member 3] 收到需求: {file_path}")

    max_retries: int = 3
    game_is_valid = False
    error_msg = ""
    while (not game_is_valid) and (max_retries > 0):
        syntax_is_valid, error_msg = static_code_check(file_path)
        if syntax_is_valid:
            error_msg = "No error detected"
            print(f"[Member 3]: ✅ 程式碼生成完成且語法檢查通過！")
            flash("✅ 程式碼生成完成且語法檢查通過！", "success")
        else:
            print(f"[Member 3]: ❌ 靜態檢查失敗: {error_msg}, 正在修理語法")
            flash(f"❌ 靜態檢查失敗: {error_msg}, 正在修理語法", "danger")
            new_path, error_msg = run_fix(file_path, error_msg, provider, model, "syntax")

        logic_is_valid, error_msg = game_logic_check(gdd, file_path, provider, model)
        if logic_is_valid:
            error_msg = "No error detected"
            print(f"[Member 3]: ✅ 程式碼生成完成且邏輯檢查通過！")
            flash("✅ 程式碼生成完成且邏輯檢查通過！", "success")
        else:
            print(f"[Member 3]: ❌ 邏輯檢查失敗: {error_msg}, 正在修理邏輯")
            flash(f"❌ 邏輯檢查失敗: {error_msg}, 正在修理邏輯", "danger")
            new_path, error_msg = run_fix(file_path, error_msg, provider, model, "logic")

        fuzz_passed, error_msg = run_fuzz_test(file_path, config.FUZZER_RUNNING_TIME)
        if fuzz_passed:
            game_is_valid = True
            error_msg = "No error detected"
            print(f"[Member 3]: ✅ 程式碼生成完成且 fuzzer 檢查通過！")
            flash("✅ 程式碼生成完成且 fuzzer 檢查通過！", "success")
        else:
            print(f"[Member 3]: ❌ fuzzer 檢查失敗: {error_msg}, 正在修理邏輯")
            flash(f"❌ fuzzer 檢查失敗: {error_msg}, 正在修理邏輯", "danger")
            new_path, error_msg = run_fix(file_path, error_msg, provider, model, "logic")

        max_retries -= 1

    if game_is_valid: return True
    return False