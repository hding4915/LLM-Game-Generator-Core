import os
import re
import subprocess
import sys
import textwrap


def get_dynamic_fuzz_logic(game_file_path: str) -> str:
    """
    尋找動態 Fuzz 邏輯。Arcade 2.x 版本應呼叫 window 的方法。
    """
    dir_path = os.path.dirname(game_file_path)
    logic_path = os.path.join(dir_path, "fuzz_logic.py")

    default_logic = """
# Random Mouse Press (Arcade 2.x Style)
if _monkey_random.random() < 0.05:
    _mx = _monkey_random.randint(0, self.width)
    _my = _monkey_random.randint(0, self.height)
    self.on_mouse_press(_mx, _my, arcade.MOUSE_BUTTON_LEFT, 0)
    self.on_mouse_release(_mx, _my, arcade.MOUSE_BUTTON_LEFT, 0)

# Random Key Press
if _monkey_random.random() < 0.05:
    _keys = [arcade.key.SPACE, arcade.key.LEFT, arcade.key.RIGHT, arcade.key.UP, arcade.key.DOWN]
    _k = _monkey_random.choice(_keys)
    self.on_key_press(_k, 0)
    """

    if os.path.exists(logic_path):
        try:
            with open(logic_path, "r", encoding="utf-8") as f:
                content = f.read()
                return content
        except Exception:
            return default_logic

    return default_logic


def inject_monkey_bot(code_content: str, bot_logic: str) -> str:
    """
    將 Monkey Bot 注入 Arcade 2.x 的 on_update 方法中。
    """
    # 1. 前處理
    lines = bot_logic.splitlines()
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        # 過濾 AI 可能生成的 import
        if any(stripped.startswith(s) for s in ["import arcade", "import random", "import pygame"]):
            continue
        filtered_lines.append(line)

    bot_logic = "\n".join(filtered_lines)
    bot_logic = textwrap.dedent(bot_logic).strip()

    bot_logic = bot_logic.replace("random.", "_monkey_random.")

    monkey_bot_template = """
        # --- [INJECTED ARCADE 2.x MONKEY BOT START] ---
        try:
            import random as _monkey_random
            # The logic should use 'self' to access window methods
{indented_logic}
        except Exception as _e:
            pass 
        # --- [INJECTED ARCADE 2.x MONKEY BOT END] ---
    """

    # 3. 尋找注入點：Arcade 2.x 的 on_update(self, delta_time)
    # 我們尋找 Window 類別中的 on_update 定義
    pattern = r"def\s+on_update\s*\(\s*self\s*,\s*delta_time[^)]*\)\s*:"
    match = re.search(pattern, code_content)

    if match:
        insertion_point = match.end()

        # 抓取縮排（假設類別方法縮排為 4 或 8 個空格）
        indented_logic = textwrap.indent(bot_logic, "            ")
        full_inject_code = monkey_bot_template.replace("{indented_logic}", indented_logic)

        # 這裡不使用 dedent 以保持相對縮排
        new_code = (
                code_content[:insertion_point] +
                "\n" +
                full_inject_code +
                code_content[insertion_point:]
        )
        return new_code

    # 如果沒找到 on_update，退而求其次尋找 update(self)
    return code_content


def run_fuzz_test(file_path: str, duration: int = 5) -> tuple[bool, str]:
    """
    執行 Fuzz Test。針對 Arcade，我們需要模擬渲染環境。
    """
    try:
        if not os.path.exists(file_path):
            return False, "File not found"

        with open(file_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        bot_logic = get_dynamic_fuzz_logic(file_path)
        fuzzed_code = inject_monkey_bot(original_code, bot_logic)

        temp_file = file_path.replace(".py", "_fuzz_temp.py")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(fuzzed_code)

        print(f"[Fuzzer] 正在對 Arcade 遊戲進行 {duration} 秒壓力測試...")

        env = os.environ.copy()
        env["SDL_AUDIODRIVER"] = "dummy"

        cmd = [sys.executable, temp_file]
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env
        )

        try:
            stdout, stderr = process.communicate(timeout=duration)
        except subprocess.TimeoutExpired:
            process.kill()
            return True, "Fuzz Test Passed (Game survived random inputs)."

        if os.path.exists(temp_file):
            os.remove(temp_file)

        if process.returncode != 0:
            error_msg = stderr
            if "Traceback" in stderr:
                error_msg = "Traceback" + stderr.split("Traceback")[-1]
            return False, f"Arcade Logic Crash: {error_msg}"

        return True, "Fuzz Test Passed."

    except Exception as e:
        return False, f"Fuzz Test Failed: {str(e)}"