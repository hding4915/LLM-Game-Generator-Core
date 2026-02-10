from src.utils import call_llm, generate_with_reviewer
from src.design.prompts import CEO_PROMPT, CPO_PROMPT, GDD_REVIEWER_PROMPT
from config import config
import logging


logger = logging.getLogger("Member1-Designer")
logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.DEBUG))


TEMPERATURE = 0.8


def run_design_phase(user_input, provider="openai", model="gpt-4o-mini"):
    """
    流程：User -> CEO -> CPO -> [Review Loop] -> GDD
    """
    logging.info(f"收到需求: {user_input}")

    ceo_response = call_llm(CEO_PROMPT, user_input, provider=provider, model=model, temperature=0.7)

    cpo_input = f"用戶想法: {user_input}\nCEO 分析: {ceo_response}"

    logging.info("進入 GDD 審查迴圈...")
    final_gdd = generate_with_reviewer(
        generator_func=call_llm,
        generator_args={
            "system_prompt": CPO_PROMPT,
            "user_prompt": cpo_input,
            "provider": provider,
            "model": model,
            "temperature": 0.7
        },
        reviewer_prompt=GDD_REVIEWER_PROMPT,
        context_text=None,  # There's no previous context for the first generation
        provider=provider,
        model=model
    )

    return final_gdd