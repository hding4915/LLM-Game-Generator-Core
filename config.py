import os

from dotenv import load_dotenv

load_dotenv()


# --- Helper Functions ---
def get_env_bool(var_name, default=False):
    """將環境變數轉換為 Boolean (支援 'true', '1', 'yes')"""
    val = os.getenv(var_name, str(default)).lower()
    return val in ('true', '1', 't', 'yes', 'on')


def get_env_int(var_name, default=0):
    """將環境變數轉換為 Integer"""
    try:
        return int(os.getenv(var_name, default))
    except (ValueError, TypeError):
        return default


def get_env_ssl_verify(var_name, default=True):
    """
    處理特殊的 SSL_VERIFY:
    - 它可以是 Bool (True/False)
    - 也可以是 Str (路徑 "/path/to/cert.pem")
    """
    val = os.getenv(var_name)

    if val is None:
        return default

    # 嘗試判斷是否為布林字串
    lower_val = val.lower()
    if lower_val in ('true', '1', 't', 'yes', 'on'):
        return True
    if lower_val in ('false', '0', 'f', 'no', 'off'):
        return False

    # 如果不是布林關鍵字，就當作路徑字串回傳
    return val



class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    # LLM API keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    # LLM model names
    GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama3-8b-8192")
    GOOGLE_MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-2.5-flash")
    OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    MISTRAL_MODEL_NAME = os.getenv("MISTRAL_MODEL_NAME", "codestral-lastest")
    DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")

    # OLLAMA
    OLLAMA_BASE_URL =  os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
    OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3:8b")

    # Fuzzer
    FUZZER_RUNNING_TIME = 30

    # Embedding model
    LLM_EMBEDDING_PROVIDER = os.getenv("LLM_EMBEDDING_PROVIDER")
    LLM_EMBEDDING_SERVER_ADDRESS = os.getenv("LLM_EMBEDDING_SERVER_ADDRESS")
    LLM_EMBEDDING_SERVER_PORT = os.getenv("LLM_EMBEDDING_SERVER_PORT", "")
    LLM_EMBEDDING_MODEL_TYPE = os.getenv("LLM_EMBEDDING_MODEL_TYPE")
    LLM_EMBEDDING_CLIENT_TOKEN = os.getenv("LLM_EMBEDDING_CLIENT_TOKEN")

    # Chroma
    CHROMA_TENANT = os.getenv("CHROMA_TENANT", "default_tenant")
    CHROMA_DATABASE = os.getenv("CHROMA_DATABASE")
    CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME")

    # Chroma client type(http, cloud)
    CHROMA_CLIENT_TYPE = os.getenv("CHROMA_CLIENT_TYPE")

    # Chroma cloud
    CHROMA_TOKEN = os.getenv("CHROMA_TOKEN")

    # Chroma http
    CHROMA_HOST = os.getenv("CHROMA_HOST")
    CHROMA_PORT = get_env_int("CHROMA_PORT", 443)
    CHROMA_SSL = get_env_bool("CHROMA_SSL", False)
    CHROMA_SSL_VERIFY = get_env_ssl_verify("CHROMA_SSL_VERIFY", False)
    CHROMA_SERVER_AUTH_CREDENTIALS = os.getenv("CHROMA_SERVER_AUTH_CREDENTIALS", None)
    CHROMA_SERVER_AUTH_PROVIDER = os.getenv("CHROMA_SERVER_AUTH_PROVIDER", None)
    CF_ACCESS_CLIENT_ID = os.getenv("CF_ACCESS_CLIENT_ID", None)
    CF_ACCESS_CLIENT_SECRET = os.getenv("CF_ACCESS_CLIENT_SECRET", None)

config = Config()