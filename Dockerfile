FROM python:3.10-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt requirements_web.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_web.txt

# 複製專案檔案
COPY . .

# 暴露 port
EXPOSE 5000

# 啟動應用
CMD ["python3", "app.py"]
