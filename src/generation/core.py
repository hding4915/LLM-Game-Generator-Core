from src.utils import call_llm
from src.generation.prompts import PROGRAMMER_PROMPT_TEMPLATE, FUZZER_GENERATION_PROMPT
from src.generation.asset_gen import generate_assets
from src.generation.file_utils import save_code_to_file
from src.rag_service.rag import RagService, RagConfig
from config import config
from src.generation.arcade_tools import ARCADE_TOOLS
import os


rag_config = RagConfig(collection_name=config.ARCADE_COLLECTION_NAME)
rag = RagService(rag_config=rag_config)

COMMON_DEVELOPER_INSTRUCTION = """
CRITICAL INSTRUCTIONS FOR TOOL USAGE:
1. **Source of Truth**: The output from tools is the ABSOLUTE TRUTH. If your training data conflicts, OBEY THE TOOL.
2. **API Strictness (ARCADE 3.0 ONLY)**: 
   - **Drawing**: NEVER use `draw_rectangle_filled`. Use `draw_rect_filled(arcade.XYWH(x,y,w,h), color)`.
   - **Rendering**: NEVER use `arcade.start_render()`. Use `self.clear()` inside `on_draw`.
   - **Cameras**: Use `arcade.Camera2D`. Call `self.camera.use()` before drawing sprites.
3. **Update Logic**: 
   - **Sprite.update**: Any `update` method in a Sprite class MUST accept `delta_time`.
     Example: `def update(self, delta_time: float):` 
     (Even if you don't use it, you must accept it because `SpriteList.update()` passes it.)
4. **Coordinate Systems**: 
   - Arcade's (0,0) is BOTTOM-LEFT.
   - For grids: `x = start_x + col * size`. Do not rely on implicit indexing.
5. **Safety**: Always check for `None` before accessing grid elements.

Please generate the code now based on these findings.
"""


def planner(
        gdd_context: str,
        asset_json: str,
        provider: str = "mistral",
        model: str = "codestral-latest",
        temperature: float = 0.5
) -> str:
    """
    第一階段：規劃。
    [改進] 我們要求 Planner 除了規劃架構外，還要列出「數學與邏輯的關鍵約束 (Constraints)」。
    這樣 2048 的網格邏輯就會由 Planner 自動生成，而不是我們手寫。
    """
    system_prompt = "You are an expert Arcade 3.0 Game Architect."

    full_prompt = f"""
    Create a detailed technical implementation plan for an Arcade 3.0 game.

    GDD:
    {gdd_context}

    ASSETS (JSON):
    {asset_json}

    Please output the plan in two sections:

    SECTION 1: ARCHITECTURE
    - Classes (e.g., GameView, Sprite classes)
    - Key Methods (setup, on_draw, on_update)
    - Logic Flow

    SECTION 2: CRITICAL IMPLEMENTATION CONSTRAINTS
    - List specific mathematical formulas needed (e.g., Grid to Screen coordinate conversion).
    - List specific Arcade 3.0 features to use (e.g., Camera2D for scrolling).
    - List potential pitfalls (e.g., "Ensure tiles don't overlap").

    Return the plan in plain text.
    """

    return call_llm(system_prompt, full_prompt, provider=provider, model=model, temperature=temperature)


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
    print("🔍 準備 Arcade 3.0 知識庫連線...")

    # 3. 構建 Prompt
    programmer_system_prompt = (
        "You are an expert Arcade 3.0 Programmer. "
        "Your goal is to turn the Technical Plan into working Python code. "
        "You have access to tools to look up the latest API documentation."
    )

    user_input = f"""
    Write the full Python code for this game.

    [GDD]
    {gdd_context}

    [ASSETS]
    {asset_json}

    [TECHNICAL PLAN & CONSTRAINTS]
    {plan}

    REMINDER: 
    - Use `get_arcade_3_0_api_conventions` to check drawing functions.
    - Use `search_arcade_kb` to find examples for specific mechanics in the plan.
    """

    print(f"🚀 正在調用 LLM (帶有工具支持)...")

    # 4. 動態組合 Nudge 指令
    # 我們把「通用指令」加上「Planner 產生的計畫」作為最強的提示
    # 這樣針對不同遊戲，Instruction 裡面的內容就會自動變更
    dynamic_instruction = (
        f"{COMMON_DEVELOPER_INSTRUCTION}\n\n"
        f"SPECIFIC PLAN REMINDERS:\n"
        f"Please pay special attention to the 'CRITICAL IMPLEMENTATION CONSTRAINTS' mentioned in the plan above."
    )

    return call_llm(
        programmer_system_prompt,
        user_input,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=8192,
        tools=ARCADE_TOOLS,
        rag_instance=rag,
        tool_additional_instruction=dynamic_instruction  # <--- 自動化的關鍵
    )



def generate_structural_code(
        gdd_context: str,
        asset_json: str,
        provider: str = "mistral",
        model: str = "codestral-latest"
        
):
    """
    Generate structural code according to the given gdd context and the given asset json.
    :param gdd_context: The gdd context to generate code for
    :type gdd_context: str

    :param asset_json: The art asset json file
    :type asset_json: str

    :param provider: The LLM service provider
    :type provider: str

    :param model: The LLM model to use
    :type model: str

    :return: The generated code
    :rtype: str
    """




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
