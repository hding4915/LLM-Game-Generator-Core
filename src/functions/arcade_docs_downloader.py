import requests
import zipfile
import io
import os
import re
from pathlib import Path

# Arcade 2.6.17 的官方 Tag 下載連結
GITHUB_ZIP_URL = "https://codeload.github.com/pythonarcade/arcade/zip/refs/tags/2.6.17"
OUTPUT_DIR = "../../arcade_rag_knowledge_base"

# 2.6.x 的結構中，doc 是文檔，arcade/examples 是範例
# 注意：有些版本的 doc 會放在分支出去的地方，但在 2.6.17 zip 中主要路徑如下：
DIRS_TO_KEEP = ["doc", "arcade/examples"]


def download_arcade_source():
    print(f"📥 正在從 GitHub 下載 Arcade 2.6.17 原始碼... ({GITHUB_ZIP_URL})")

    # 建立標頭偽裝成一般瀏覽器存取
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(GITHUB_ZIP_URL, headers=headers)

    # 檢查是否下載成功 (200 OK)
    response.raise_for_status()

    # 除錯檢查：如果內容太小或包含 <html>，代表下載到錯誤頁面
    if len(response.content) < 1000 or b"<html" in response.content[:100].lower():
        print("❌ 錯誤：下載內容並非有效的 ZIP 檔案。")
        print(f"內容預覽: {response.content[:100]}")
        raise ValueError("The server returned HTML instead of a ZIP file. Check the URL or your network.")

    print("✅ 下載完成，開始解壓縮與處理...")
    return zipfile.ZipFile(io.BytesIO(response.content))


def clean_rst_to_markdown(rst_content):
    """
    將 2.6.x 的 .rst 文檔清洗為 Markdown。
    2.6 的文檔中含有大量關於舊版 API 的說明（例如 draw_rectangle_filled）。
    """
    lines = rst_content.split('\n')
    md_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 1. 處理標題 (RST 使用 === 或 --- 當底線)
        if stripped and all(c in '=' for c in stripped) and len(stripped) > 3:
            if i > 0:
                header_text = lines[i - 1].strip()
                if md_lines: md_lines.pop()
                md_lines.append(f"# {header_text}")
            continue
        if stripped and all(c in '-' for c in stripped) and len(stripped) > 3:
            if i > 0:
                header_text = lines[i - 1].strip()
                if md_lines: md_lines.pop()
                md_lines.append(f"## {header_text}")
            continue

        # 2. 處理程式碼區塊
        if ".. code-block::" in line:
            lang = line.split("::")[-1].strip()
            if not lang: lang = "python"
            md_lines.append(f"\n```{lang}")
            continue

        # 3. 移除 Sphinx 特有指令
        if stripped.startswith(".. ") and "code-block" not in stripped:
            continue

            # 4. 清理格式標記
        line = re.sub(r':ref:`([^`]+)`', r'\1', line)
        line = re.sub(r':class:`([^`]+)`', r'`\1`', line)
        line = re.sub(r':func:`([^`]+)`', r'`\1`', line)

        md_lines.append(line)

    return "\n".join(md_lines)


def process_files(zip_ref):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    file_list = zip_ref.namelist()
    # 2.6.17 zip 解壓後根目錄通常是 arcade-2.6.17
    root_folder = file_list[0].split('/')[0]

    count_docs = 0
    count_examples = 0

    print(f"📂 正在從根目錄 {root_folder} 提取內容...")

    for file_path in file_list:
        # 取得相對路徑
        relative_path = file_path[len(root_folder) + 1:]

        if not any(relative_path.startswith(d) for d in DIRS_TO_KEEP):
            continue

        if file_path.endswith('/'):
            continue

        try:
            with zip_ref.open(file_path) as f:
                content = f.read().decode('utf-8', errors='ignore')
        except Exception as e:
            continue

        # --- 處理文檔 ---
        if relative_path.startswith("doc/") and relative_path.endswith(".rst"):
            md_content = clean_rst_to_markdown(content)
            save_name = relative_path.replace('/', '_').replace('.rst', '.md')
            save_path = os.path.join(OUTPUT_DIR, save_name)

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"Source: Arcade 2.6.17 {relative_path}\n\n")
                f.write(md_content)
            count_docs += 1

        # --- 處理 2.6.x 範例程式碼 ---
        elif relative_path.startswith("arcade/examples/") and relative_path.endswith(".py"):
            save_name = relative_path.replace('/', '_').replace('.py', '.md')
            save_path = os.path.join(OUTPUT_DIR, save_name)

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"# Arcade 2.6.17 Example: {os.path.basename(file_path)}\n")
                f.write(f"Source: {relative_path}\n\n")
                f.write("```python\n")
                f.write(content)
                f.write("\n```")
            count_examples += 1

    print(f"\n🎉 Arcade 2.6.17 知識庫準備完成！")
    print(f"📄 文檔轉換: {count_docs} 個檔案")
    print(f"💻 2.6 版範例代碼: {count_examples} 個檔案")
    print(f"📂 資料夾路徑: ./{OUTPUT_DIR}")


if __name__ == "__main__":
    try:
        z = download_arcade_source()
        process_files(z)
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")