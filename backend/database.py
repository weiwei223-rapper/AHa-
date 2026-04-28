import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# 載入 .env 文件中的環境變數
load_dotenv()

# 從環境變數讀取 PostgreSQL Database URL
# 請設置環境變數 DATABASE_URL，例如: postgresql://user:password@localhost:5432/yourdb
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Please set it to a PostgreSQL connection string.")

if not SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
    raise ValueError("Only PostgreSQL is supported. DATABASE_URL must start with 'postgresql://'.")

# PostgreSQL 連接參數
connect_args = {}

def _create_engine():
    try:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args=connect_args
        )
        # Test the connection
        with engine.connect():
            pass
        return engine
    except Exception as e:
        raise RuntimeError(f"Failed to connect to PostgreSQL database: {e}")

engine = _create_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依賴注入：確保每個請求都有獨立的 DB 會話，並在結束後關閉
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
