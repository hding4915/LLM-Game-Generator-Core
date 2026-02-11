from src.rag_service.rag import RagService
from config import config
import os


def get_arcade_2_x_api_conventions() -> str:
    """
    回傳 Arcade 2.x (Legacy) 的強制性 API 規範。
    當 LLM 需要確認舊版繪圖函數或核心系統時呼叫。
    """
    return """
    ARCADE 2.x (LEGACY) MANDATORY CONVENTIONS:
    1. Drawing: Use 'draw_rectangle_filled' and 'draw_circle_filled'. 
       (Direct parameters: x, y, width, height, color). Do NOT use XYWH objects.
    2. Rendering: 'arcade.start_render()' MUST be called at the beginning of 'on_draw'.
    3. Cameras: Use 'arcade.Camera(width, height)' for scrolling. 'arcade.Camera2D' does NOT exist.
    4. Textures: 'arcade.Texture(name, image)' requires a unique name string for caching.
    5. Updates: 'Sprite.update()' does NOT take 'delta_time' by default.
    """


def search_arcade_kb(query: str, rag: RagService) -> str:
    """
    搜尋 Arcade 2.x 的官方文件與程式碼範例。
    """
    results = rag.query(query, n_results=1)

    if results and "metadatas" in results:
        filename = results["metadatas"][0][0]["file_name"]

        full_path = os.path.join(config.ARCADE_SOURCE_DIR, filename)
        with open(full_path, "r", encoding="utf-8") as f:
            rag_context = f.read()
        return rag_context

    return "No relevant Arcade 2.x documentation found."


ARCADE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_arcade_2_x_api_conventions",
            "description": "Get mandatory API mapping rules and legacy argument signatures for Arcade 2.x (e.g. draw_rectangle_filled).",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_arcade_kb",
            "description": "Search the Arcade 2.x knowledge base for legacy implementation details or examples.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query, e.g., 'sprite movement physics engine'"}
                },
                "required": ["query"]
            }
        }
    }
]