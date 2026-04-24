import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# 載入 .env 文件中的環境變數
load_dotenv()

# 先嘗試從環境變數讀取 Database URL，沒有則使用 PostgreSQL
# 請設置環境變數 DATABASE_URL，例如: postgresql://user:password@localhost:5432/yourdb
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:mars940223@localhost:5432/AHaSQL"
)

# PostgreSQL 和 SQLite 使用不同的連接參數
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL 連接參數
    connect_args = {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依賴注入：確保每個請求都有獨立的 DB 會話，並在結束後關閉
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
