import openai
import requests
import json
from config import config
from src.generation.arcade_tools import get_arcade_3_0_api_conventions, search_arcade_kb
from typing import List, Dict, Any, Optional

from src.rag_service.rag import RagService


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


def execute_tool(tool_name: str, args: dict, rag_instance: Any = None) -> str:
    """
    根據工具名稱執行對應的本地函數。
    """
    try:
        from src.generation.arcade_tools import get_arcade_3_0_api_conventions, search_arcade_kb
    except ImportError:
        return f"Error: Could not import game_generator tools. Check project structure."

    if tool_name == "get_arcade_3_0_api_conventions":
        return get_arcade_3_0_api_conventions()

    if tool_name == "search_arcade_kb":
        query = args.get("query", "")
        if not rag_instance:
            return "Error: RAG instance is not initialized or passed correctly."
        return search_arcade_kb(query=query, rag=rag_instance)

    return f"Error: Tool '{tool_name}' not found."


def call_llm(
        system_prompt: str,
        user_prompt: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        tools: Optional[List[Dict[str, Any]]] = None,
        rag_instance: Any = None,
        tool_additional_instruction: str = None  # [新增參數] 允許外部注入特定的提醒
) -> str:
    """
    [統一入口] 支援多種 LLM Provider 並整合 Tool Use 迴圈。
    """
    provider = provider.lower()

    if provider in ["google", "gemini"]:
        if model.startswith("gpt"):
            model = "gemini-2.5-flash-preview-09-2025"
        try:
            from src.utils.llm_clients import call_google_gemini
            return call_google_gemini(system_prompt, user_prompt, model, temperature, max_tokens=max_tokens)
        except ImportError:
            return "Error: call_google_gemini not found."

    if provider == "ollama":
        try:
            from src.utils.llm_clients import call_ollama
            return call_ollama(system_prompt, user_prompt, model, temperature, num_ctx=8192)
        except ImportError:
            return "Error: call_ollama not found."

    openai_config = get_client_config(provider)
    if not openai_config:
        return f"Error: 不支援的 Provider '{provider}'"

    api_key = openai_config.get("api_key")
    base_url = openai_config.get("base_url")

    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Tool Loop: 最多允許 5 次往返
        for loop_index in range(5):
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": 600
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = client.chat.completions.create(**kwargs)
            assistant_message = response.choices[0].message

            # 1. 檢查是否有工具呼叫
            if not assistant_message.tool_calls:
                return assistant_message.content if assistant_message.content else ""

            # 2. 處理工具呼叫
            tool_calls_list = []
            for tc in assistant_message.tool_calls:
                tool_calls_list.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })

            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": tool_calls_list
            })

            # 3. 執行所有工具
            for tc in tool_calls_list:
                function_name = tc["function"]["name"]
                try:
                    function_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    function_args = {}

                print(f"🛠️ [Tool Call] 執行工具: {function_name} | 參數: {function_args}")
                observation = execute_tool(function_name, function_args, rag_instance=rag_instance)
                print(f"   -> Result: {observation[:200]}..." if observation else "   -> Result: (Empty)")

                messages.append({
                    "tool_call_id": tc["id"],
                    "role": "tool",
                    "name": function_name,
                    "content": observation
                })

            # [Nudge Logic] 使用傳入的參數，如果沒傳則使用通用提醒
            default_instruction = (
                "Tool outputs provided above. "
                "Please generate the code now based on these findings."
            )

            # 優先使用外部傳入的指令，否則使用預設
            final_instruction = tool_additional_instruction if tool_additional_instruction else default_instruction

            messages.append({
                "role": "user",
                "content": final_instruction
            })

    except Exception as e:
        print(f"[LLM Call Error] Provider: {provider}, Error: {e}")
        return f"LLM Call Error ({provider}): {str(e)}"

    return "Error: Tool loop exceeded limit."