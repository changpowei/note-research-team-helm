FROM python:3.10-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt requirements_web.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_web.txt

# 複製專案檔案
COPY . .

# 建立非 root 使用者並設定擁有權
RUN adduser --disabled-password --gecos "" --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露 port
EXPOSE 5000

# 使用 gunicorn 啟動（production-grade WSGI server）
# --workers 1：保持單一 process，避免全域狀態問題
# --threads 4：允許同時處理 SSE 串流與普通請求
# --timeout 620：大於 MAX_STREAM_SECONDS (600)，避免 SSE 連線被強制中斷
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "620", "app:app"]
