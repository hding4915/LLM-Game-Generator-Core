import re
from src.utils import call_llm
from src.generation.prompts import ART_PROMPT


def generate_assets(
        gdd_context: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
) -> str:
    response = call_llm(ART_PROMPT, f"GDD Content:\n{gdd_context}", provider=provider, model=model)

    try:
        # Find {...} structure
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return response
    except:
        return "{}"