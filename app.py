"""
Flask Web 應用 - CrewAI Research Team UI

提供互動式界面讓用戶輸入研究主題並實時查看 agent 執行過程
"""

import os
import json
import threading
import queue
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 導入 CrewAI
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from note_research_team.crew import NoteResearchTeamCrew

app = Flask(__name__, template_folder='.')
CORS(app)

# 全域變數儲存執行狀態
execution_queue = queue.Queue()
current_execution = None


class OutputCapture:
    """捕獲 CrewAI 輸出並推送到佇列"""
    
    def __init__(self, output_queue):
        self.queue = output_queue
        self.original_stdout = sys.stdout
        
    def write(self, text):
        if text.strip():
            self.queue.put({
                'type': 'output',
                'data': text
            })
        self.original_stdout.write(text)
    
    def flush(self):
        self.original_stdout.flush()


def run_crew_task(topic, output_queue):
    """
    在背景執行 CrewAI 任務
    
    Args:
        topic: 研究主題
        output_queue: 輸出佇列
    """
    try:
        # 推送開始訊息
        output_queue.put({
            'type': 'status',
            'data': 'starting',
            'message': f'開始研究主題：{topic}'
        })
        
        # 捕獲輸出
        sys.stdout = OutputCapture(output_queue)
        
        # 執行 Crew
        inputs = {'topic': topic}
        result = NoteResearchTeamCrew().crew().kickoff(inputs=inputs)
        
        # 恢復標準輸出
        sys.stdout = sys.stdout.original_stdout
        
        # 從結果中提取 Notion URL
        # result 可能是 CrewOutput 對象或字串
        if hasattr(result, 'raw'):
            # CrewOutput 對象
            result_text = str(result.raw)
            print(f"\n[DEBUG] result 類型: CrewOutput")
            print(f"[DEBUG] result.raw: {result.raw}")
        else:
            result_text = str(result)
            print(f"\n[DEBUG] result 類型: {type(result)}")
        
        notion_url = None
        
        print(f"[DEBUG] 開始提取 Notion URL")
        print(f"[DEBUG] result_text 內容長度: {len(result_text)} 字元")
        print(f"[DEBUG] result_text 前200字元: {result_text[:200]}")
        
        # 方法 1：從「✅ 成功發佈...」訊息中提取
        # 格式：頁面連結：https://www.notion.so/...
        if '頁面連結：' in result_text:
            print(f"[DEBUG] 找到「頁面連結：」關鍵字")
            lines = result_text.split('\n')
            for line in lines:
                if '頁面連結：' in line:
                    # 提取 URL
                    url_start = line.find('https://www.notion.so/')
                    if url_start != -1:
                        # 找到 URL 的結尾（空白或換行）
                        url_end = len(line)
                        for char in [' ', '\n', '\r']:
                            pos = line.find(char, url_start)
                            if pos != -1 and pos < url_end:
                                url_end = pos
                        notion_url = line[url_start:url_end].strip()
                        print(f"[DEBUG] 方法1 提取成功: {notion_url}")
                        break
        
        # 方法 2：使用正則表達式作為備用方案
        if not notion_url and 'https://www.notion.so/' in result_text:
            print(f"[DEBUG] 嘗試方法2（正則）")
            import re
            url_match = re.search(r'https://www\.notion\.so/[^\s\)\]]+', result_text)
            if url_match:
                notion_url = url_match.group(0)
                print(f"[DEBUG] 方法2 提取成功: {notion_url}")
        
        if not notion_url:
            print(f"[DEBUG] ⚠️ 未能提取 Notion URL")
            print(f"[DEBUG] result_text 完整內容: {result_text}")
        
        # 推送完成訊息
        output_queue.put({
            'type': 'status',
            'data': 'completed',
            'message': '任務完成！',
            'result': result_text,
            'notion_url': notion_url
        })
        print(f"[DEBUG] 推送完成訊息，notion_url={notion_url}\n")
        
    except Exception as e:
        # 恢復標準輸出
        if hasattr(sys.stdout, 'original_stdout'):
            sys.stdout = sys.stdout.original_stdout
        
        # 推送錯誤訊息
        output_queue.put({
            'type': 'status',
            'data': 'error',
            'message': f'執行錯誤：{str(e)}'
        })


@app.route('/')
def index():
    """首頁"""
    notion_page_url = os.getenv('NOTION_PARENT_PAGE_URL', 'https://www.notion.so/CrewAI-2fbbb5a7920980dd89c0c8b82915f45c')
    return render_template('index.html', notion_page_url=notion_page_url)


@app.route('/api/run', methods=['POST'])
def run_research():
    """
    啟動研究任務
    
    預期 JSON body: {"topic": "研究主題"}
    """
    global current_execution
    
    data = request.get_json()
    topic = data.get('topic', '').strip()
    
    if not topic:
        return jsonify({'error': '請輸入研究主題'}), 400
    
    # 創建新的輸出佇列（清空舊的執行狀態）
    output_queue = queue.Queue()
    current_execution = {
        'topic': topic,
        'queue': output_queue,
        'thread': None,
        'notion_url': None  # 初始化為 None
    }
    
    # 在背景執行
    thread = threading.Thread(target=run_crew_task, args=(topic, output_queue))
    thread.daemon = True
    thread.start()
    current_execution['thread'] = thread
    
    return jsonify({
        'status': 'started',
        'topic': topic
    })


@app.route('/api/stream')
def stream_output():
    """
    Server-Sent Events 串流輸出
    
    返回格式：
    data: {"type": "output", "data": "agent 輸出文字"}
    data: {"type": "status", "data": "starting|completed|error", "message": "..."}
    """
    def generate():
        if current_execution is None:
            yield f"data: {json.dumps({'type': 'error', 'message': '沒有正在執行的任務'})}\n\n"
            return
        
        queue_ref = current_execution['queue']
        
        while True:
            try:
                # 從佇列取得訊息（超時 1 秒）
                message = queue_ref.get(timeout=1.0)
                yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                
                # 如果是完成或錯誤，結束串流
                if message.get('type') == 'status' and message.get('data') in ['completed', 'error']:
                    break
                    
            except queue.Empty:
                # 發送心跳訊息保持連線
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                
                # 檢查執行緒是否還活著
                if current_execution['thread'] and not current_execution['thread'].is_alive():
                    break
    
    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    print("🚀 CrewAI Research UI 啟動中...")
    print("📍 訪問: http://localhost:5000")
    app.run(host='0.0.0.0', debug=True, threaded=True, port=5000)
