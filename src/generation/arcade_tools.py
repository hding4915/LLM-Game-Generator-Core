from src.rag_service.rag import RagService
from config import config
import os


def get_arcade_3_0_api_conventions() -> str:
    """
    回傳 Arcade 3.0 的強制性 API 規範。
    當 LLM 需要確認繪圖函數或核心系統變更時呼叫。
    """
    return """
    ARCADE 3.0 MANDATORY CONVENTIONS:
    1. Drawing: All 'draw_rectangle_...' functions are renamed to 'draw_rect_...'.
    2. Signatures: 'draw_rect_filled' and 'draw_rect_outline' MUST take a rect object.
       Example: arcade.draw_rect_filled(arcade.XYWH(x, y, w, h), color)
    3. Cameras: Use 'arcade.Camera2D' for scrolling and UI. Call 'camera.use()' before drawing.
    4. Sprites: Use 'SpriteList' for efficiency. Update logic via 'on_update' or PhysicsEngine.
    """


def search_arcade_kb(query: str, rag: RagService) -> str:
    """
    搜尋 Arcade 3.0 的官方文件與程式碼範例。
    """
    results = rag.query(query, n_results=1)

    if results and "metadatas" in results:
        filename = results["metadatas"][0][0]["file_name"]
        full_path = os.path.join(config.ARCADE_SOURCE_DIR, filename)
        with open(full_path, "r", encoding="utf-8") as f:
            rag_context = f.read()
        return rag_context

    return "No relevant documentation found."


ARCADE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_arcade_3_0_api_conventions",
            "description": "Get mandatory API mapping rules and argument signatures for Arcade 3.0 (e.g. draw_rect_filled).",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_arcade_kb",
            "description": "Search the Arcade 3.0 knowledge base for specific implementation details or examples.",
            "parameters": {
                "type": "object",
                "properties": {
                    # 注意：rag 參數由系統內部注入，不放入 JSON Schema 供 LLM 填寫
                    "query": {"type": "string", "description": "The search query, e.g., 'sprite movement physics'"}
                },
                "required": ["query"]
            }
        }
    }
]