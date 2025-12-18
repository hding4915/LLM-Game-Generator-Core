from src.utils import call_llm
from src.generation.prompts import PROGRAMMER_PROMPT_TEMPLATE, FUZZER_GENERATION_PROMPT
from src.generation.asset_gen import generate_assets
from src.generation.file_utils import save_code_to_file
import os


def generate_code(
        gdd_context: str,
        asset_json: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    """
    Generate code according to the given gdd context and the given asset json.
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

    full_prompt = f"""
    GDD:
    {gdd_context}

    ASSETS (JSON):
    {asset_json}

    Write the full code now following the Template.
    """
    return call_llm(PROGRAMMER_PROMPT_TEMPLATE, full_prompt, provider=provider, model=model, temperature=0.2)


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

    print("[Member 2] Saving file...")
    file_path = save_code_to_file(raw_code)

    if file_path:
        fuzzer_logic_code = generate_fuzzer_logic(gdd_context, provider, model)
        output_dir = os.path.dirname(file_path)

        save_code_to_file(fuzzer_logic_code, output_dir=output_dir, filename="fuzz_logic.py")

    return file_path
