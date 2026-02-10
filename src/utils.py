import openai
import requests
from config import config
import os

def generate_with_reviewer(
        generator_func,  # the function that generates the content (e.g., GDD or Code)
        generator_args: dict,  # generator_func params
        reviewer_prompt: str,  # Prompt Template
        context_text: str,  # the generated content
        provider: str,
        model: str,
        max_retries: int = 3
) -> str:
    """
    通用審查迴圈：生成 -> 審查 -> (如果不通過) 附帶意見重生成
    """
    current_content = context_text

    # If context_text is empty, generate first
    if not current_content:
        current_content = generator_func(**generator_args)

    print(f"--- [Review Loop] 開始審查 (Max Retries: {max_retries}) ---")

    for i in range(max_retries):
        # 1. Call reviewer to check the current content
        review_input = f"CONTENT_TO_REVIEW:\n{current_content}\n\n請檢查上述內容是否符合要求。如果不符合，請列出具體修改建議。如果完美，請只回答 'PASS'。"
        review_feedback = call_llm(
            system_prompt=reviewer_prompt,
            user_prompt=review_input,
            provider=provider,
            model=model,
            temperature=0.1
        )

        # 2. Determine if it passes review
        if "PASS" in review_feedback.upper() and len(review_feedback) < 20:
            print(f"--- [Review Loop] 第 {i + 1} 次審查通過 ✅ ---")
            return current_content

        # 3. If not passed, print feedback and prepare for next iteration
        print(f"--- [Review Loop] 第 {i + 1} 次審查未通過，正在修正... ❌ ---")
        print(f"意見: {review_feedback[:100]}...")

        # 4. Prepare new prompt for revision (can include original prompt + feedback)
        original_prompt = generator_args.get('user_prompt', '')
        revise_prompt = f"{original_prompt}\n\n[Previous Attempt]:\n{current_content}\n\n[Reviewer Feedback]:\n{review_feedback}\n\n請根據 Feedback 修正並重新輸出完整的內容。"

        # Regenerate with the new prompt
        new_args = generator_args.copy()
        new_args['user_prompt'] = revise_prompt
        current_content = generator_func(**new_args)

    print(f"--- [Review Loop] 達到最大重試次數，回傳最後結果 ---")
    return current_content

def get_client_config(provider: str) -> dict | None:
    """
    根據 Provider 回傳對應的 Client 設定 (api_key, base_url)
    支援 OpenAI 相容介面的服務 (Groq, Mistral, DeepSeek)
    注意：Ollama 已獨立處理，不在此函式中
    """
    provider = provider.lower()

    if provider == "openai":
        return {
            "api_key": config.OPENAI_API_KEY,
            "base_url": None
        }
    elif provider == "groq":
        return {
            "api_key": config.GROQ_API_KEY,
            "base_url": "https://api.groq.com/openai/v1"
        }
    elif provider == "mistral":
        return {
            "api_key": config.MISTRAL_API_KEY,
            "base_url": "https://api.mistral.ai/v1"
        }
    elif provider == "deepseek":
        return {
            "api_key": config.DEEPSEEK_API_KEY,
            "base_url": "https://api.deepseek.com/v1"
        }
    elif provider == "inception":
        return {
            "api_key": config.INCEPTION_API_KEY,
            "base_url": "https://api.inceptionlabs.ai/v1"
        }
    return None


def call_google_gemini(
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int = 8192
) -> str:
    """
    處理 Google Gemini 的特殊邏輯 (需安裝 google-generativeai)
    """
    try:
        import google.generativeai as genai
    except ImportError:
        return "Error: 請安裝 google-generativeai 套件 (pip install google-generativeai)"

    api_key: str = config.GOOGLE_API_KEY
    if not api_key:
        return "Error: 未設定 GOOGLE_API_KEY"

    try:
        genai.configure(api_key=api_key)

        generation_config: dict = {
            "temperature": temperature,
            "top_p": 0.95,
            "max_output_tokens": max_tokens,
            "response_mime_type": "text/plain",
        }

        # System instructions
        gemini_model = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
            system_instruction=system_prompt
        )

        response = gemini_model.generate_content(user_prompt)
        return response.text
    except Exception as e:
        return f"Gemini API Error: {str(e)}"


def call_ollama(
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        num_ctx: int = 4096
) -> str:

    print(f"Run ollama (Native API): {model}")

    base_url = config.OLLAMA_BASE_URL
    if not base_url:
        base_url = "http://localhost:11434"

    # 清理 URL，確保指向 /api/chat
    api_url = base_url.rstrip("/")
    # 如果原本設定包含 /v1 (為了相容 OpenAI)，要把它拿掉改成原生路徑
    if api_url.endswith("/v1"):
        api_url = api_url[:-3]
    api_url = f"{api_url}/api/chat"

    # 設定 Request Body
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "num_ctx": num_ctx,
            "temperature": temperature
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    if config.OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {config.OLLAMA_API_KEY}"

    response = ""


    try:
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,  # 帶上 headers
            timeout=300
        )

        # 檢查是否有 401 (Unauthorized) 或 403 (Forbidden) 等錯誤
        if response.status_code == 401:
            return "Ollama Error: 401 Unauthorized. 請檢查 API Key 是否正確。"

        response.raise_for_status()

        result = response.json()
        return result["message"]["content"]

    except requests.exceptions.RequestException as e:
        print(f"[Ollama Error] Connection failed: {e}")
        return f"Ollama Error: {str(e)}"
    except KeyError:
        return f"Ollama Error: Unexpected response format. {response.text}"


def call_llm(
        system_prompt: str,
        user_prompt: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 256000
) -> str:
    """
    [統一入口] 支援多種 LLM Provider
    Provider: 'openai', 'groq', 'google', 'ollama', 'mistral', 'deepseek'
    """
    provider = provider.lower()

    # --- Case 1: Google Gemini ---
    if provider in ["google", "gemini"]:
        if model.startswith("gpt"):
            model = "gemini-2.5-flash"
        return call_google_gemini(system_prompt, user_prompt, model, temperature, max_tokens=max_tokens)

    # --- Case 2: Ollama (Local) ---
    if provider == "ollama":
        return call_ollama(system_prompt, user_prompt, model, temperature, num_ctx=8192)

    # --- Case 3: OpenAI Compatible APIs (OpenAI, Groq, Mistral, DeepSeek) ---
    openai_config = get_client_config(provider)
    if not openai_config:
        return f"Error: 不支援的 Provider '{provider}'"

    api_key = openai_config.get("api_key")
    base_url = openai_config.get("base_url")

    if not api_key:
        return f"Error: 請在 .env 設定 {provider.upper()}_API_KEY"

    try:
        # 初始化 OpenAI Client
        client = openai.OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            timeout=600,  # 強制設定 600秒 超時
            max_tokens=max_tokens  # 強制設定最大 Token 數
        )
        return response.choices[0].message.content

    except KeyError as e:
        print(f"[LLM Config Error] Missing key: {e}")
        return f"Configuration Error: Missing key {str(e)}"
    except Exception as e:
        print(f"[LLM Call Error] Provider: {provider}, Error: {e}")
        return f"LLM Call Error ({provider}): {str(e)}"


