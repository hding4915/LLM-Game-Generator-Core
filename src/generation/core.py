from src.utils import call_llm
from src.generation.prompts import PROGRAMMER_PROMPT_TEMPLATE
from src.generation.asset_gen import generate_assets
from src.generation.file_utils import save_code_to_file


def generate_code(gdd_context, asset_json, provider="openai", model="gpt-4o-mini"):
    """產出 Python 代碼"""
    full_prompt = f"""
    GDD:
    {gdd_context}

    ASSETS (JSON):
    {asset_json}

    Write the full code now following the Template.
    """
    return call_llm(PROGRAMMER_PROMPT_TEMPLATE, full_prompt, provider=provider, model=model)


def run_core_phase(gdd_context, provider="openai", model="gpt-4o-mini"):
    print("[Member 2] 開始生成美術素材 (JSON)...")
    assets = generate_assets(gdd_context, provider, model)
    print(f"[Member 2] 素材完成: {assets[:50]}...")

    print("[Member 2] 開始生成程式碼...")
    raw_code = generate_code(gdd_context, assets, provider, model)

    print("[Member 2] 存檔中...")
    file_path = save_code_to_file(raw_code)

    return file_path