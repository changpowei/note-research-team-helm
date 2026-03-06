"""
Flask Web 應用 - CrewAI Research Team UI

提供互動式界面讓用戶輸入研究主題並實時查看 agent 執行過程
"""
from __future__ import annotations

# Standard library
import json
import logging
import os
import queue
import re
import sys
import threading
import time

# sys.path setup（必須在 local import 之前）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Third-party
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Local
from note_research_team.crew import NoteResearchTeamCrew

# 載入環境變數
load_dotenv()

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder=".")

# CORS：限制允許來源（預設為 research.local，本地開發可加 http://localhost:5000）
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://research.local").split(",")
CORS(app, origins=_allowed_origins)

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri="memory://",
)

# 執行狀態（thread-safe）
_execution_lock = threading.Lock()
current_execution: dict | None = None

# 設定值
MAX_TOPIC_LENGTH = int(os.getenv("MAX_TOPIC_LENGTH", "200"))
MAX_STREAM_SECONDS = int(os.getenv("MAX_STREAM_SECONDS", "600"))
NOTION_PARENT_PAGE_URL = os.getenv("NOTION_PARENT_PAGE_URL", "")


class OutputCapture:
    """捕獲 CrewAI stdout 輸出並推送到佇列"""

    def __init__(self, output_queue: queue.Queue) -> None:
        self.queue = output_queue

    def write(self, text: str) -> None:
        if text.strip():
            self.queue.put({"type": "output", "data": text})

    def flush(self) -> None:
        pass


def run_crew_task(topic: str, output_queue: queue.Queue) -> None:
    """在背景執行 CrewAI 任務"""
    original_stdout = sys.stdout
    result = None
    try:
        output_queue.put({
            "type": "status",
            "data": "starting",
            "message": f"開始研究主題：{topic}",
        })
        sys.stdout = OutputCapture(output_queue)
        inputs = {"topic": topic}
        result = NoteResearchTeamCrew().crew().kickoff(inputs=inputs)
    except Exception:
        logger.exception("Crew task failed for topic: %s", topic)
        output_queue.put({
            "type": "status",
            "data": "error",
            "message": "執行失敗，請聯繫管理員",
        })
        return
    finally:
        sys.stdout = original_stdout

    # 提取結果文字
    result_text = str(result.raw) if hasattr(result, "raw") else str(result)

    # 從結果中提取 Notion URL
    notion_url: str | None = None

    # 方法 1：從「頁面連結：https://...」訊息中提取
    if "頁面連結：" in result_text:
        for line in result_text.split("\n"):
            if "頁面連結：" in line:
                url_start = line.find("https://www.notion.so/")
                if url_start != -1:
                    url_end = len(line)
                    for char in (" ", "\n", "\r"):
                        pos = line.find(char, url_start)
                        if pos != -1 and pos < url_end:
                            url_end = pos
                    notion_url = line[url_start:url_end].strip()
                    break

    # 方法 2：正則表達式備用
    if not notion_url and "https://www.notion.so/" in result_text:
        url_match = re.search(r"https://www\.notion\.so/[^\s\)\]]+", result_text)
        if url_match:
            notion_url = url_match.group(0)

    if not notion_url:
        logger.warning("Could not extract Notion URL from crew result")

    output_queue.put({
        "type": "status",
        "data": "completed",
        "message": "任務完成！",
        "result": result_text,
        "notion_url": notion_url,
    })


@app.after_request
def set_security_headers(response: Response) -> Response:
    """加入基本安全 Headers"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.tailwindcss.com 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "font-src *;"
    )
    return response


@app.route("/")
def index() -> str:
    """首頁"""
    return render_template("index.html", notion_page_url=NOTION_PARENT_PAGE_URL)


@app.route("/api/run", methods=["POST"])
@limiter.limit("3 per minute")
@limiter.limit("10 per hour")
def run_research() -> tuple[Response, int]:
    """
    啟動研究任務

    預期 JSON body: {"topic": "研究主題"}
    """
    global current_execution

    # 驗證請求格式
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "請求格式錯誤，需要 JSON body"}), 400

    topic = data.get("topic", "")
    if not isinstance(topic, str):
        return jsonify({"error": "topic 必須為字串"}), 400

    topic = topic.strip()
    if not topic:
        return jsonify({"error": "請輸入研究主題"}), 400

    if len(topic) > MAX_TOPIC_LENGTH:
        return jsonify({"error": f"研究主題不能超過 {MAX_TOPIC_LENGTH} 字元"}), 400

    with _execution_lock:
        # 拒絕並發任務
        if (
            current_execution is not None
            and current_execution.get("thread")
            and current_execution["thread"].is_alive()
        ):
            return jsonify({"error": "目前有任務正在執行，請稍後再試"}), 429

        output_queue: queue.Queue = queue.Queue()
        current_execution = {
            "topic": topic,
            "queue": output_queue,
            "thread": None,
        }

        thread = threading.Thread(
            target=run_crew_task, args=(topic, output_queue), daemon=True
        )
        thread.start()
        current_execution["thread"] = thread

    return jsonify({"status": "started", "topic": topic}), 200


@app.route("/api/stream")
def stream_output() -> Response:
    """
    Server-Sent Events 串流輸出

    返回格式：
    data: {"type": "output", "data": "agent 輸出文字"}
    data: {"type": "status", "data": "starting|completed|error", "message": "..."}
    data: {"type": "heartbeat"}
    """
    def generate():
        with _execution_lock:
            execution = current_execution

        if execution is None:
            yield f"data: {json.dumps({'type': 'error', 'message': '沒有正在執行的任務'})}\n\n"
            return

        queue_ref = execution["queue"]
        start_time = time.monotonic()

        while True:
            # 防止 SSE 連線無限掛起
            if time.monotonic() - start_time > MAX_STREAM_SECONDS:
                yield f"data: {json.dumps({'type': 'error', 'message': '串流超時'}, ensure_ascii=False)}\n\n"
                break

            try:
                message = queue_ref.get(timeout=1.0)
                yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"

                if message.get("type") == "status" and message.get("data") in (
                    "completed",
                    "error",
                ):
                    break

            except queue.Empty:
                # 心跳訊息保持連線
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

                if execution["thread"] and not execution["thread"].is_alive():
                    break

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    # 本地開發模式：設定 FLASK_DEBUG=true 開啟 debug
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    logger.info("CrewAI Research UI 啟動中... 訪問: http://localhost:5000")
    app.run(host="0.0.0.0", debug=debug_mode, threaded=True, port=5000)
