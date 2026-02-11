from src.utils import call_llm
from src.design.prompts import CEO_PROMPT, CPO_PROMPT, CPO_REVIEW_PROMPT


def run_design_phase(user_input, provider="openai", model="gpt-4o-mini"):
    """
    流程：User -> CEO (分析) -> CPO (規則化) -> GDD
    """
    print(f"[Member 1] 收到需求: {user_input}")

    # 1. CEO 分析
    ceo_response = call_llm(CEO_PROMPT, user_input, provider=provider, model=model)
    print(f"[Member 1] CEO 分析完成: {ceo_response[:50]}...")

    gdd_context = ""
    cpo_review_response = ""
    # 2. CPO 產出文件
    for attempt in range(3):
        print(f"[Member 1] CPO 產出文件中... (嘗試 {attempt + 1}/3)")
        cpo_input = f"用戶想法: {user_input}\nCEO 分析: {ceo_response}"
        if cpo_review_response:
            cpo_input += f"\nCPO Review: {cpo_review_response}"
        gdd_context = call_llm(CPO_PROMPT, cpo_input, provider=provider, model=model)
        cpo_review_response = call_llm(CPO_REVIEW_PROMPT, gdd_context, provider=provider, model=model)
        print(cpo_review_response)
        if "PASS" in cpo_review_response:
            print("[Member 1] CPO 文件審查通過 ✅")
            break

    return gdd_context