import chromadb
import hashlib
import requests
from chromadb import QueryResult, EmbeddingFunction, Documents, Embeddings
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from config import Config
from dataclasses import dataclass


class RemoteOllamaAuthEF(EmbeddingFunction):
    def __init__(self, base_url: str, api_key: str, model_name: str = "nomic-embed-text", timeout: int = 30):
        self.api_url = f"{base_url}/api/embeddings"
        self.model_name = model_name
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.timeout = timeout

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            payload = {
                "model": self.model_name,
                "prompt": text
            }
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
            except Exception as e:
                print(f"Error embedding text: {e}")
                raise e

        return embeddings


@dataclass
class RagConfig:
    tenant: str = getattr(Config, 'CHROMA_TENANT', 'default_tenant')
    database: str = getattr(Config, 'CHROMA_DATABASE', 'default_database')
    collection_name: str = getattr(Config, 'CHROMA_COLLECTION_NAME', 'my_collection')

    provider: str = getattr(Config, 'LLM_EMBEDDING_PROVIDER', 'ollama')
    base_url: str = getattr(Config, 'LLM_EMBEDDING_SERVER_ADDRESS', 'http://localhost')
    base_port: str = getattr(Config, 'LLM_EMBEDDING_SERVER_PORT', '11434')
    model_type: str = getattr(Config, 'LLM_EMBEDDING_MODEL_TYPE', 'llama3')
    embedding_token: str = getattr(Config, 'LLM_EMBEDDING_CLIENT_TOKEN', None)

    # --- Cloud mode ---
    chroma_token: str = getattr(Config, 'CHROMA_TOKEN', None)

    # client_type: 'cloud' or 'http'
    client_type: str = getattr(Config, 'CHROMA_CLIENT_TYPE', 'http')

    # --- Http mode ---
    host: str = getattr(Config, 'CHROMA_HOST', 'localhost')
    port: int = getattr(Config, 'CHROMA_PORT', 8000)
    ssl: bool = getattr(Config, 'CHROMA_SSL', False)

    # [新增] SSL 驗證設定
    # 如果是自簽憑證且不想報錯，設為 False
    # 如果有特定的 CA 檔案，設為檔案路徑字串
    ssl_verify: bool | str = getattr(Config, 'CHROMA_SSL_VERIFY', True)

    # [補充] 如果 Server 有設密碼 (X-Chroma-Token 或 Authorization)
    chroma_server_auth_credentials: str = getattr(Config, 'CHROMA_SERVER_AUTH_CREDENTIALS', None)
    chroma_server_auth_provider: str = getattr(Config, 'CHROMA_SERVER_AUTH_PROVIDER', None)

    # [新增] Cloudflare Access 設定
    cf_client_id: str = getattr(Config, 'CF_ACCESS_CLIENT_ID', None)
    cf_client_secret: str = getattr(Config, 'CF_ACCESS_CLIENT_SECRET', None)


class RagService:
    def __init__(self, rag_config: RagConfig = None):
        if rag_config is None:
            rag_config = RagConfig()

        self.client = self._get_client(rag_config)

        self.embedding_function = self._get_embedding_function(
            rag_config.provider,
            rag_config.base_url,
            rag_config.base_port,
            rag_config.model_type,
            rag_config.embedding_token
        )

        self.actual_collection_name = f"{rag_config.collection_name}_{rag_config.model_type}"

        print(f"Now use model: {rag_config.model_type}")
        print(f"Data collection name: {self.actual_collection_name}")

        self.collection = self.client.get_or_create_collection(
            name=self.actual_collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

    def reset(self):
        """
        刪除目前的 Collection 並重新建立一個空的。
        用於每次生成新專案時清除舊記憶。
        """
        try:
            print(f"[RAG] Resetting collection: {self.actual_collection_name}...")
            self.client.delete_collection(self.actual_collection_name)

            # 重新建立空的 Collection
            self.collection = self.client.create_collection(
                name=self.actual_collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            print("[RAG] Collection reset successfully.")
        except Exception as e:
            print(f"[RAG] Warning during reset (might be empty already): {e}")
            # 如果刪除失敗（例如不存在），確保還是要 get_or_create
            self.collection = self.client.get_or_create_collection(
                name=self.actual_collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )

    def delete_by_metadata(self, filter_dict: dict):
        """
        根據 metadata 刪除資料。
        自動處理多條件的 AND 邏輯。
        """
        print(f"Deleting documents with metadata: {filter_dict}")

        # 1. 檢查 filter_dict 是否為空
        if not filter_dict:
            print("Filter is empty, skipping delete.")
            return

        # 2. 轉換邏輯：如果超過一個鍵值對，轉換為 ChromaDB 的 $and 語法
        if len(filter_dict) > 1:
            where_clause = {
                "$and": [
                    {k: v} for k, v in filter_dict.items()
                ]
            }
        else:
            # 只有一個條件時，直接使用
            where_clause = filter_dict

        try:
            # 傳入轉換後的 where_clause
            self.collection.delete(where=where_clause)
            print("Delete executed.")
        except Exception as e:
            print(f"Delete failed: {e}")

    def _get_client(self, config: RagConfig):
        mode = config.client_type.lower()

        if mode == 'cloud':
            print("Connecting to Chroma Cloud...")
            return chromadb.CloudClient(
                api_key=config.chroma_token,
                tenant=config.tenant,
                database=config.database
            )

        elif mode == 'http':
            chroma_settings = Settings()

            request_headers = {
                "Content-Type": "application/json"
            }

            if config.cf_client_id and config.cf_client_secret:
                print("偵測到 Cloudflare Service Token，已加入 Headers")
                request_headers["CF-Access-Client-Id"] = config.cf_client_id
                request_headers["CF-Access-Client-Secret"] = config.cf_client_secret

            if config.ssl:
                chroma_settings.chroma_server_ssl_verify = config.ssl_verify

            # [選用] 如果你需要 Token/Basic Auth 認證
            if config.chroma_server_auth_credentials:
                chroma_settings.chroma_client_auth_provider = config.chroma_server_auth_provider or "chromadb.auth.token_auth.TokenAuthClientProvider"
                chroma_settings.chroma_client_auth_credentials = config.chroma_server_auth_credentials

            return chromadb.HttpClient(
                host=config.host,
                port=config.port,
                ssl=config.ssl,
                headers=request_headers,
                settings=chroma_settings,
                tenant=config.tenant
            )

        else:
            raise ValueError(f"Unsupported Chroma client_type: {mode}。Please use 'cloud' or 'http'")

    def _get_embedding_function(self, provider: str, base_url: str, base_port: str, model_type: str, token: str):
        model_type = model_type.lower()

        if provider == "ollama":
            return RemoteOllamaAuthEF(
                base_url=f"{base_url}:{base_port}",
                api_key=token,
                model_name=model_type,
                timeout=120
            )

        elif provider == "default":
            return embedding_functions.DefaultEmbeddingFunction()

        else:
            raise ValueError(f"不支援的 provider: {provider}")

    def hash_content(self, content):
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def insert(self, content: str, metadata: dict = None) -> str:
        new_id = self.hash_content(content)
        if metadata is None:
            self.collection.upsert(
                documents=[content],
                ids=[new_id],
            )
        else:
            self.collection.upsert(
                documents=[content],
                metadatas=[metadata],
                ids=[new_id],
            )
        return new_id

    def query(self, question: str, filters: dict = None, n_results: int = 3):
        return self.collection.query(
            query_texts=[question],
            n_results=n_results,
            where=filters
        )



if __name__ == "__main__":
    rag_config = RagConfig(collection_name="menu1")
    rag = RagService(rag_config=rag_config)

    rag.insert("1231", metadata={"source": "main.py", "run_id": "asd12gfhjrthgsdfzxzc"})
    rag.insert("1234", metadata={"source": "main.py", "run_id": "asdaqwr12ewqda"})
    result = rag.query("1234")
    print(result)

    rag.delete_by_metadata({"source": "main.py", "run_id": "asd12gfhjrthgsdfzxzc"})
    result = rag.query("1234")
    print(result)

    rag.delete_by_metadata({"source": "main.py", "run_id": "asdaqwr12ewqda"})
    result = rag.query("1234")
    print(result)
