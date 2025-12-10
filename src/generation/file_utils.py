import re
import os


def save_code_to_file(
        raw_text: str,
        output_dir: str = "output"
) -> str | None:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pattern = r"```python(.*?)```"
    match = re.search(pattern, raw_text, re.DOTALL)

    if match:
        clean_code = match.group(1).strip()
        file_path = os.path.join(output_dir, "main.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(clean_code)
        return file_path
    else:
        if "import pygame" in raw_text:
            file_path = os.path.join(output_dir, "main.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
            return file_path
        return None