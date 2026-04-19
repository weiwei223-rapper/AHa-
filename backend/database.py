import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 先嘗試從環境變數讀取 Database URL，沒有則使用本機 Postgres
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Wayne48763@localhost/postgres"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依賴注入：確保每個請求都有獨立的 DB 會話，並在結束後關閉
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
