import os
from pathlib import Path
from tqdm import tqdm
from langchain_text_splitters import MarkdownTextSplitter
from src.rag_service.rag import RagService, RagConfig
from config import config

# --- 設定 ---
SOURCE_DIR = config.ARCADE_SOURCE_DIR
COLLECTION_NAME = config.ARCADE_COLLECTION_NAME


def main():
    # 1. 初始化你的 RagService
    # 它會自動讀取你的 config.py 並連接到你的 Ollama
    print("🤖 正在初始化 RagService (Ollama)...")
    config = RagConfig(collection_name=COLLECTION_NAME)
    rag = RagService(rag_config=config)

    # 2. 準備 Markdown 切分器
    # 這裡很關鍵：切分程式碼時盡量保持完整性
    text_splitter = MarkdownTextSplitter(chunk_size=1200, chunk_overlap=150)

    # 3. 讀取所有檔案並切分
    all_contents = []
    all_metadatas = []

    path_list = list(Path(SOURCE_DIR).glob("*.md"))
    if not path_list:
        print(f"❌ 找不到目錄 {SOURCE_DIR} 或目錄內沒有 .md 檔案。")
        return

    print(f"📄 正在處理 {len(path_list)} 個 Markdown 檔案...")

    for file_path in tqdm(path_list):
        with open(file_path, "r", encoding="utf-8") as f:
            full_text = f.read()

            # 從內容中提取來源標記 (你在上一個腳本加的 Source: ...)
            source_line = "unknown"
            if "Source: " in full_text:
                source_line = full_text.split("\n")[0].replace("Source: ", "")

            # 進行切分
            chunks = text_splitter.split_text(full_text)

            for chunk in chunks:
                # 簡單過濾掉過短或只有空白的 chunk，避免重複的無意義 ID
                if len(chunk.strip()) < 10:
                    continue

                all_contents.append(chunk)
                all_metadatas.append({
                    "file_name": file_path.name,
                    "source": source_line
                })

    # 4. [修復] 確保 IDs 唯一性
    # 因為 RagService 使用 hash_content(content) 作為 ID，
    # 如果內容完全一樣，ID 就會重複導致 ChromaDB 報錯。
    print("🧹 正在檢查並移除重複內容...")
    unique_contents = []
    unique_metadatas = []
    seen_ids = set()

    for content, metadata in zip(all_contents, all_metadatas):
        content_id = rag.hash_content(content)
        if content_id not in seen_ids:
            seen_ids.add(content_id)
            unique_contents.append(content)
            unique_metadatas.append(metadata)

    print(f"📊 過濾後總計 {len(unique_contents)} 個獨特區塊。")

    # 5. 批次寫入 ChromaDB
    print(f"📦 正在發送向量化請求至 Ollama (模型: {config.model_type})...")
    rag.batch_insert(unique_contents, metadatas=unique_metadatas)

    print("\n✨ Arcade 3.0 知識庫導入完成！")
    print(f"現在你可以使用 rag.query(\"如何移動 Sprite\") 來查詢了。")


if __name__ == "__main__":
    main()
    # print(SOURCE_DIR)
    # config = RagConfig(collection_name=COLLECTION_NAME)
    # rag = RagService(rag_config=config)
    #
    # result = rag.query("how to move Sprite")
    #
    # print(result)
    # print(result['documents'])
    # print(result['metadatas'][0])
    # print(result['metadatas'][0][0]['file_name'])