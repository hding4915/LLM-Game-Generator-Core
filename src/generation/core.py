from src.utils import call_llm
from src.generation.prompts import PROGRAMMER_PROMPT_TEMPLATE
from src.generation.asset_gen import generate_assets
from src.generation.file_utils import save_code_to_file


def generate_code(
        gdd_context: str,
        asset_json: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    full_prompt = f"""
    GDD:
    {gdd_context}

    ASSETS (JSON):
    {asset_json}

    Write the full code now following the Template.
    """
    return call_llm(PROGRAMMER_PROMPT_TEMPLATE, full_prompt, provider=provider, model=model)


def run_core_phase(
        gdd_context: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    print("[Member 2] Start to generate assets (JSON)...")
    assets = generate_assets(gdd_context, provider, model)
    print(f"[Member 2] Generation complete: {assets[:50]}...")

    print("[Member 2] Start to generate code...")
    raw_code = generate_code(gdd_context, assets, provider, model)

    print("[Member 2] Saving code to file...")
    file_path = save_code_to_file(raw_code)

    return file_path