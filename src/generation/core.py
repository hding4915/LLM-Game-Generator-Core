from src.utils import call_llm
from src.generation.prompts import FUZZER_GENERATION_PROMPT, COMMON_DEVELOPER_INSTRUCTION, PLAN_REVIEW_PROMPT
from src.generation.asset_gen import generate_assets
from src.generation.file_utils import save_code_to_file
from src.generation.game_logic_cheat_sheet import *
from src.rag_service.rag import RagService, RagConfig
from config import config
import os


rag_config = RagConfig(collection_name=config.ARCADE_COLLECTION_NAME)
rag = RagService(rag_config=rag_config)



ARCADE_2_LEGACY_INSTRUCTION = """
CRITICAL ARCADE 2.6.17 RULES:
1. **Drawing**: Use `arcade.draw_rectangle_filled(center_x, center_y, width, height, color)`.
   - Note: It uses CENTER x/y, not corner!
2. **Rendering**: Use `arcade.start_render()` inside `on_draw()`.
3. **Class Structure**: Inherit from `arcade.Window`.
4. **Input**: Use `on_key_press(symbol, modifiers)`.
"""


def planner(
        gdd_context: str,
        asset_json: str,
        provider: str = "mistral",
        model: str = "codestral-latest",
        temperature: float = 0.5
) -> str:
    """
    第一階段：規劃 (帶有 Reviewer 修正環節)。
    透過 Reviewer 確保 Arcade 2.x API 的正確性與網格存取的安全性。
    """
    print("[Planner] 正在啟動技術架構規劃與安全審查...")

    system_prompt = "You are an expert Arcade 2.x (Legacy) Game Architect."

    # 初始 Plan 請求
    initial_user_prompt = f"""
    Create a detailed technical implementation plan for an Arcade 2.x (Legacy) game.

    GDD:
    {gdd_context}

    ASSETS (JSON):
    {asset_json}

    Please output the plan in two sections:
    SECTION 1: ARCHITECTURE
    - Classes (e.g., GameWindow, Sprite classes)
    - Key Methods (setup, on_draw, on_update)
    - Logic Flow

    SECTION 2: CRITICAL IMPLEMENTATION CONSTRAINTS
    - List specific mathematical formulas needed.
    - List Arcade 2.x legacy features to use (start_render, draw_rectangle_filled, etc.).
    - List potential pitfalls (e.g., "Must check if cell is None before accessing .value").

    Return the plan in plain text.
    """

    # 第一輪生成
    current_plan = call_llm(system_prompt, initial_user_prompt, provider=provider, model=model, temperature=temperature)

    # 進入 Review 循環 (進行 2 次優化)
    for attempt in range(2):
        print(f"[Planner] 正在進行技術審查 (第 {attempt + 1}/2 輪)...")

        # 呼叫 Reviewer 進行分析
        review_feedback = call_llm(
            "You are a Technical Lead Reviewer.",
            f"Original Plan:\n{current_plan}\n\nReview this plan for Arcade 2.x API accuracy and Grid/NoneType safety.",
            provider=provider, model=model
        )

        # 根據 Feedback 修正 Plan
        refine_prompt = f"""
        Original Plan:
        {current_plan}

        Review Feedback:
        {review_feedback}

        TASK: Rewrite the Technical Implementation Plan by incorporating the feedback. 
        Ensure all API calls are Arcade 2.x and all grid accesses are guarded against NoneType errors.
        """

        current_plan = call_llm(system_prompt, refine_prompt, provider=provider, model=model, temperature=0.3)

    print("[Planner] 技術規劃與安全審查完成。")
    return current_plan

def generate_code(
        gdd_context: str,
        asset_json: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        temperature: float = 0.1
) -> str:
    """
    第二階段：使用 Tool Use 模式生成程式碼。
    """

    # 1. 執行 Planner (現在它會自動幫我們想好數學邏輯)
    print("📝 正在規劃遊戲架構與關鍵約束...")
    plan = planner(gdd_context, asset_json, provider=provider, model=model, temperature=0.5)

    # 2. 初始化 RAG
    print("🔍 準備 Arcade 2.x 知識庫連線...")

    # 3. 構建 Prompt
    programmer_system_prompt = (
        "You are an expert Arcade 2.x Programmer. "
        "Your goal is to turn the Technical Plan into working Python code. "
        "You have access to tools to look up the latest API documentation."
    )

    math_injection = ""
    gdd_lower = gdd_context.lower()

    # 優先權判斷：如果是撞球類，注入物理公式；如果是網格類，注入網格公式
    if any(k in gdd_lower for k in ["pool", "billiard", "physics", "ball", "shooter", "tank"]):
        print("💡 偵測到 Top-Down 物理類遊戲，注入物理數學公式...")
        math_injection = PHYSICS_MATH_CHEAT_SHEET

    elif any(k in gdd_lower for k in ["grid", "2048", "tetris", "snake", "puzzle", "board"]):
        print("💡 偵測到網格類遊戲，注入網格數學公式...")
        math_injection = GRID_MATH_CHEAT_SHEET

    elif any(k in gdd_lower for k in ["jump", "platform", "gravity", "flappy", "mario"]):
        print("💡 偵測到平台跳躍類遊戲，注入重力與跳躍公式...")
        math_injection = PLATFORMER_CHEAT_SHEET

    user_input = f"""
    Write the full Python code for this game.

    [GDD]
    {gdd_context}

    [ASSETS]
    {asset_json}

    [TECHNICAL PLAN & CONSTRAINTS]
    {plan}
    
    [RULES & HELPERS]
    {ARCADE_2_LEGACY_INSTRUCTION}
    
    {math_injection}
    
    INSTRUCTIONS:
    1. Output valid Python code only.
    2. Ensure `import arcade` works for version 2.6.17.
    3. If implementing a grid, STRICTLY follow the math formula provided above.
    4. Ensure the game window is centered and elements are visible.
    5. WRAP the main execution logic in 'if __name__ == "__main__":'.
    """

    # print(f"🚀 正在調用 LLM (帶有工具支持)...")

    # 4. 動態組合 Nudge 指令
    # 我們把「通用指令」加上「Planner 產生的計畫」作為最強的提示
    # 這樣針對不同遊戲，Instruction 裡面的內容就會自動變更
    dynamic_instruction = (
        f"{COMMON_DEVELOPER_INSTRUCTION}\n\n"
        f"SPECIFIC PLAN REMINDERS:\n"
        f"Please pay special attention to the 'CRITICAL IMPLEMENTATION CONSTRAINTS' mentioned in the plan above.\n"
        "Arcade 2.x tool outputs provided above."
        "**Now you can start to generate the codes based on the findings provided below.**\n"
        # !!! This line is very important, do not remove or the llm won't generate codes.!!!
        "Remember to generate codes !!!!!"
    )

    return call_llm(
        programmer_system_prompt,
        user_input,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=8192
    )

def generate_fuzzer_logic(
        gdd_context: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    """
    Generate a fuzzer logic according to the given gdd context.
    :param gdd_context: The gdd context to generate code for
    :type gdd_context: str

    :param provider: The LLM service provider
    :type provider: str

    :param model: The LLM model to use
    :type model: str

    :return: The generated code
    :rtype: str
    """
    print("[Member 2] Start to generate fuzzer logic")
    prompt = FUZZER_GENERATION_PROMPT.replace("{gdd}", gdd_context)
    print("[Member 2] Generating the custom fuzzer test script (Fuzzer)...")
    return call_llm("You are a QA Engineer.", prompt, provider=provider, model=model, temperature=0.2)


def run_core_phase(
        gdd_context: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    """
    Run the game and the logic tester (game tester) codes generation routine.
    :param gdd_context: The gdd context to generate code for
    :type gdd_context: str

    :param provider: The LLM service provider
    :type provider: str

    :param model: The LLM model to use
    :type model: str

    :return: The file path of the generated code
    :rtype: str
    """

    print("[Member 2] Start to generate the assets (JSON)...")
    assets = generate_assets(gdd_context, provider, model)
    print(f"[Member 2] Generation complete: {assets[:50]}...")

    print("[Member 2] Start to generate the code...")
    raw_code = generate_code(gdd_context, assets, provider, model)
    # print("[=============================================================]")
    # print(raw_code)
    # print("[=============================================================]")

    print("[Member 2] Saving file...")
    file_path = save_code_to_file(raw_code)

    if file_path:
        fuzzer_logic_code = generate_fuzzer_logic(gdd_context, provider, model)
        output_dir = os.path.dirname(file_path)

        save_code_to_file(fuzzer_logic_code, output_dir=output_dir, filename="fuzz_logic.py")

    return file_path
