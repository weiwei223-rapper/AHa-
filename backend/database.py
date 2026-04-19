from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 資料庫連線字串格式: postgresql://用戶名:密碼@主機:埠號/資料庫名
# 格式：postgresql://帳號:密碼@主機位置/資料庫名稱
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Wayne48763@localhost/postgres"

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