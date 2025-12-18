import os
from flask import Flask, render_template, request, redirect, url_for, flash
from config import config

from src.design.chains import run_design_phase
from src.generation.core import run_core_phase
from src.testing.runner import launch_game
from src.testing.fixer import run_fix, static_code_check, run_fix_loop

app = Flask(__name__)

gdd_result_global = None
game_file_path_global = None
last_check_message = None

# Supporting providers
PROVIDERS = ["mistral", "openai", "groq", "google", "ollama", "deepseek"]


@app.route("/", methods=["GET", "POST"])
def index():
    global gdd_result_global, game_file_path_global, last_check_message

    if request.method == "POST":
        provider = request.form.get("provider", "openai").lower()
        user_input = request.form.get("user_input", "").strip()
        action = request.form.get("action")  # 按鈕名稱

        # 檢查 provider 是否在白名單
        if provider not in PROVIDERS:
            flash(f"不支援的 Provider: {provider}", "danger")
            return redirect(url_for("index"))

        # 從 .env 讀 API Key / Model Name
        api_key = os.getenv(f"{provider.upper()}_API_KEY")
        model_name = os.getenv(f"{provider.upper()}_MODEL_NAME")

        if not api_key or not model_name:
            flash(f"{provider} API Key 或 Model Name 尚未設定！", "danger")
            return redirect(url_for("index"))

        # 設定環境變數給模組使用
        os.environ[f"{provider.upper()}_API_KEY"] = api_key

        try:
            if action == "generate":
                if not user_input:
                    flash("請輸入遊戲點子！", "warning")
                    return redirect(url_for("index"))

                # --- Phase 1: Design ---
                gdd_result_global = run_design_phase(user_input, provider, model_name)
                # --- Phase 2: Core ---
                game_file_path_global = run_core_phase(gdd_result_global, provider, model_name)

                print("[Member 2] Generation complete")

                if game_file_path_global:
                    # --- Phase 3: QA ---
                    fix_result = run_fix_loop(gdd_result_global, game_file_path_global, provider, model_name)
                else:
                    flash("❌ 程式碼生成失敗，未能解析出 Python Block。", "danger")


            elif action == "launch_game":
                if game_file_path_global:
                    msg = launch_game(game_file_path_global)
                    flash(msg, "info")
                else:
                    flash("尚未生成遊戲程式碼，無法啟動遊戲！", "warning")

        except Exception as e:
            flash(f"發生系統錯誤: {str(e)}", "danger")
            return redirect(url_for("index"))

        return redirect(url_for("index"))

    file_content = None
    if game_file_path_global and os.path.exists(game_file_path_global):
        with open(game_file_path_global, "r", encoding="utf-8") as f:
            file_content = f.read()

    return render_template("index.html",
                           gdd_result=gdd_result_global,
                           game_file_path=game_file_path_global,
                           file_content=file_content,
                           last_check_message=last_check_message,
                           providers=PROVIDERS)

def create_app():
    app.secret_key = config.SECRET_KEY
    return app
