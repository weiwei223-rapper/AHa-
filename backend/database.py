import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# 載入 .env 文件中的環境變數
load_dotenv()

# 先嘗試從環境變數讀取 Database URL，沒有則使用 SQLite
# 請設置環境變數 DATABASE_URL，例如: sqlite:///./test.db 或 postgresql://user:password@localhost:5432/yourdb
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

# PostgreSQL 和 SQLite 使用不同的連接參數
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL 連接參數
    connect_args = {}

def _create_engine_with_fallback():
    try:
        primary_engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args=connect_args
        )
    except ModuleNotFoundError:
        # PostgreSQL driver（如 psycopg2）不存在時，且未明確指定 DATABASE_URL，改用 SQLite。
        if not os.getenv("DATABASE_URL"):
            return create_engine("sqlite:///./aha_app.db", connect_args={"check_same_thread": False})
        raise

    # 若未手動設定 DATABASE_URL，且預設 PostgreSQL 無法連線時，自動降級到本地 SQLite。
    if not os.getenv("DATABASE_URL"):
        try:
            with primary_engine.connect():
                pass
        except OperationalError:
            return create_engine("sqlite:///./aha_app.db", connect_args={"check_same_thread": False})

    return primary_engine

engine = _create_engine_with_fallback()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依賴注入：確保每個請求都有獨立的 DB 會話，並在結束後關閉
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
