from src.utils import call_llm
from src.design.prompts import CEO_PROMPT, CPO_PROMPT
from config import config
import logging


logger = logging.getLogger("Member1-Designer")
logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.DEBUG))


TEMPERATURE = 0.8


def run_design_phase(user_input, provider="openai", model="gpt-4o-mini"):
    """
    流程：User -> CEO (分析) -> CPO (規則化) -> GDD
    """
    logging.info(f"收到需求: {user_input}")

    # 1. CEO 分析
    ceo_response = call_llm(CEO_PROMPT, user_input, provider=provider, model=model, temperature=TEMPERATURE)
    logging.info(f"CEO 分析完成: {ceo_response[:50]}...")

    # 2. CPO 產出文件
    cpo_input = f"用戶想法: {user_input}\nCEO 分析: {ceo_response}"
    gdd_context = call_llm(CPO_PROMPT, cpo_input, provider=provider, model=model, temperature=TEMPERATURE)

    return gdd_context