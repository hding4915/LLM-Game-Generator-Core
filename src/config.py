import os
from dotenv import load_dotenv

# 模組被匯入時自動載入 .env
load_dotenv()

# 支援的模型提供者列表
PROVIDERS = ["openai", "groq", "google", "ollama", "mistral"]

# Provider 與 環境變數名稱的對照表
ENV_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "google": "GOOGLE_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "ollama": "OLLAMA_API_KEY"  # 新增: 支援 Ollama API Key
}


def get_env_key_name(provider):
    """取得特定 Provider 對應的環境變數名稱"""
    return ENV_KEY_MAP.get(provider, f"{provider.upper()}_API_KEY")


def get_default_api_key(provider):
    """從環境變數取得預設的 API Key"""
    key_name = get_env_key_name(provider)
    return os.getenv(key_name, "")


def get_default_ollama_url():
    """取得 Ollama 的預設 URL"""
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")


def update_llm_env(provider, api_key=None, ollama_url=None):
    """
    根據使用者的輸入更新當前的系統環境變數
    這樣後續呼叫 utils.py 時就能讀到最新的設定
    """
    # 1. 更新 API Key (所有 Provider 都適用，包括 Ollama)
    key_name = get_env_key_name(provider)
    if api_key:
        os.environ[key_name] = api_key

    # 2. 如果是 Ollama，額外更新 Base URL 並進行防呆修正
    if provider == "ollama" and ollama_url:
        clean_url = ollama_url.strip().rstrip("/")

        # 防呆: 如果使用者不小心貼了完整的 endpoint (包含 /chat/completions)，把它去掉
        if clean_url.endswith("/chat/completions"):
            clean_url = clean_url.replace("/chat/completions", "")
            clean_url = clean_url.rstrip("/")

        # 防呆: OpenAI Client 規範 Base URL 必須指向 /v1
        # 如果使用者只輸入了 host (如 http://localhost:11434)，自動補上 /v1
        if not clean_url.endswith("/v1"):
            clean_url += "/v1"

        os.environ["OLLAMA_BASE_URL"] = clean_url