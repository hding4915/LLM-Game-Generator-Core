import re
import ast
import logging


def extract_code_block(text: str) -> str:
    """
    從 LLM 回應中提取程式碼區塊。
    支援 Markdown 代碼塊或純文字自動清洗。
    """
    if not text:
        return ""

    # 使用變數定義 pattern，避免與編輯器渲染衝突
    fence = "`" * 3

    # 1. 嘗試匹配標準 Markdown 代碼塊: ``` ... ``` 或 ```python ... ```
    # re.DOTALL 讓 . 可以匹配換行符
    pattern = fence + r"(?:python)?\s*(.*?)" + fence
    match = re.search(pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    # 2. 如果沒有成對的 Markdown 區塊，嘗試寬鬆清洗
    # 有時候 LLM 會漏掉結尾的 ```，或者只給代碼但包含開頭的 ```
    clean = text.strip()

    # 移除開頭的 ```python 或 ```
    start_pattern = r"^" + fence + r"(?:python)?\s*"
    clean = re.sub(start_pattern, '', clean)

    # 移除結尾的 ```
    end_pattern = r"\s*" + fence + r"$"
    clean = re.sub(end_pattern, '', clean)

    return clean.strip()


def extract_code_signatures(code: str) -> str:
    """
    使用 AST 提取程式碼的 '簽名' (Signatures/Headers)。
    只保留 Class 定義、Function 參數、全域變數與 Import。
    """
    signature_lines = []
    try:
        clean_code = extract_code_block(code)
        tree = ast.parse(clean_code)

        for node in tree.body:
            # 提取 Import
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                signature_lines.append(ast.unparse(node))

            # 提取常數定義 (Assign)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        val_str = "..."
                        if isinstance(node.value, (ast.Constant, ast.Num, ast.Str)):
                            if hasattr(node.value, 'value'):
                                val_str = repr(node.value.value)
                            else:
                                val_str = ast.unparse(node.value)
                        signature_lines.append(f"{target.id} = {val_str}")

            # 提取 Class 定義
            elif isinstance(node, ast.ClassDef):
                signature_lines.append(f"class {node.name}:")
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        args = ast.unparse(item.args)
                        methods.append(f"    def {item.name}({args}): ...")
                if methods:
                    signature_lines.extend(methods)
                else:
                    signature_lines.append("    pass")

            # 提取 Function 定義
            elif isinstance(node, ast.FunctionDef):
                args = ast.unparse(node.args)
                signature_lines.append(f"def {node.name}({args}): ...")

    except Exception as e:
        # 解析失敗不應中斷流程，回傳空字串即可
        return ""

    return "\n".join(signature_lines)