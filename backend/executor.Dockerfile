# 使用輕量級的 Python 基礎映像檔
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 建立一個非 root 的使用者以增加安全性
RUN useradd -m sandbox
USER sandbox

# 預設執行指令
CMD ["python"]
