import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, stream_with_context
from flask_session import Session
from config import config

from src.design.chains import run_design_phase
from src.generation.core import run_core_phase
from src.testing.runner import launch_game
from src.testing.fixer import run_fix_loop

app = Flask(__name__)
# --- Flask session config ---
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Supporting providers
PROVIDERS = ["mistral", "openai", "groq", "google", "ollama", "deepseek"]

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        provider = request.form.get("provider", "openai").lower()
        user_input = request.form.get("user_input", "").strip()
        action = request.form.get("action")
        session['provider'] = provider

        if provider not in PROVIDERS:
            flash(f"不支援的 Provider: {provider}", "danger")
            return redirect(url_for("index"))

        api_key = os.getenv(f"{provider.upper()}_API_KEY")
        model_name = os.getenv(f"{provider.upper()}_MODEL_NAME")
        session['model_name'] = model_name

        if not api_key or not model_name:
            flash(f"{provider} API Key 或 Model Name 尚未設定！", "danger")
            return redirect(url_for("index"))
        os.environ[f"{provider.upper()}_API_KEY"] = api_key

        try:
            if action == "generate":
                if not user_input:
                    flash("請輸入遊戲點子！", "warning")
                    return redirect(url_for("index"))

                # --- Phase 1: Design ---
                session['gdd_result_global'] = run_design_phase(user_input, provider, model_name)
                # --- Phase 2: Core ---
                session['game_file_path_global'] = run_core_phase(session.get('gdd_result_global'), provider, model_name)

                print("[Member 2] Generation complete")

                if session.get('game_file_path_global'):
                    session['auto_start_fix'] = True
                    flash("核心代碼生成完畢，準備開始驗證...", "info")
                else:
                    flash("❌ 程式碼生成失敗，未能解析出 Python Block。", "danger")


            elif action == "launch_game":
                path = session.get('game_file_path_global')
                if path:
                    msg = launch_game(path)
                    flash(msg, "info")
                else:
                    flash("尚未生成遊戲程式碼，無法啟動遊戲！", "warning")

        except Exception as e:
            flash(f"發生系統錯誤: {str(e)}", "danger")
            return redirect(url_for("index"))

        return redirect(url_for("index"))
    # --- Get ---
    file_content = None
    path = session.get('game_file_path_global')
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            file_content = f.read()
    auto_start_fix = session.pop('auto_start_fix', None)

    return render_template("index.html",
                           gdd_result=session.get('gdd_result_global'),
                           game_file_path=session.get('game_file_path_global'),
                           file_content=file_content,
                           providers=PROVIDERS,
                           auto_start_fix=auto_start_fix
    )

@app.route('/fix_stream')
def fix_stream():
    """"
    Use generator function to streamline the status output.
    run_fix_loop is a generator function, which contains the message given by "yield".
    When the frontend received the message format sent by run_fix_loop, it will show the message automatically.
    """
    if not session.get('game_file_path_global') or not session.get('gdd_result_global'):
        def error_gen():
            yield "data: 錯誤：尚未生成遊戲，無法開始驗證。\n\n"
        return Response(error_gen(), mimetype='text/event-stream')
    gdd = session.get('gdd_result_global')
    path = session.get('game_file_path_global')
    provider = session.get('provider')
    model_name = session.get('model_name')
    return Response(
        stream_with_context(run_fix_loop(gdd, path, provider, model_name)),
        mimetype='text/event-stream'
    )

def create_app():
    app.secret_key = config.SECRET_KEY
    return app
