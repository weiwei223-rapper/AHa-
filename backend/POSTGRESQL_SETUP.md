# PostgreSQL 設置與操作指南

## 1. 安裝 PostgreSQL

### Windows
- 下載官方安裝程序：[PostgreSQL 官網](https://www.postgresql.org/download/windows/)
- 安裝時記住 PostgreSQL 用戶 (預設: postgres) 和密碼
- 預設端口：5432

### macOS (使用 Homebrew)
```bash
brew install postgresql
brew services start postgresql
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

---

## 2. 創建資料庫和使用者

### 使用 psql 命令行工具

#### 連接到 PostgreSQL
```bash
# 連接到預設資料庫 (postgres)
psql -U postgres
# 系統會提示輸入密碼
```

#### 創建新用戶
```sql
CREATE USER aha_user WITH PASSWORD 'aha_password';
```

#### 創建資料庫
```sql
CREATE DATABASE aha OWNER aha_user;
```

#### 授予權限
```sql
GRANT ALL PRIVILEGES ON DATABASE aha TO aha_user;
```

#### 查看所有資料庫
```sql
\l
```

#### 查看所有用戶
```sql
\du
```

#### 退出 psql
```
\q
```

---

## 3. 環境變數配置

### 創建 .env 文件
在 `backend/` 目錄下創建 `.env` 文件：

```env
DATABASE_URL=postgresql+psycopg://aha_user:aha_password@localhost:5432/aha
JWT_SECRET=your-secret-key-change-this-in-production
API_HOST=127.0.0.1
API_PORT=8000
LOG_LEVEL=INFO
```

### 說明
- `aha_user`: PostgreSQL 用戶名
- `aha_password`: 對應的密碼
- `localhost`: 資料庫伺服器地址 (本地開發)
- `5432`: PostgreSQL 預設端口
- `aha`: 資料庫名稱

---

## 4. Python 依賴安裝

```bash
cd backend
pip install -r requirements.txt
```

關鍵包括：
- `psycopg[binary]`: PostgreSQL 的 Python 驅動程式
- `sqlalchemy>=2.0`: ORM 框架
- `fastapi`: Web 框架

---

## 5. 啟動應用程式

### 開發模式（自動重載）
```bash
cd backend
python main.py
```

### 生產模式（使用 Gunicorn）
```bash
cd backend
gunicorn -c gunicorn_conf.py main:app
```

應用程式將在 `http://127.0.0.1:8000` 啟動

---

## 6. 驗證資料庫連接

### 查看創建的表
使用 psql 連接到資料庫：

```bash
psql -U aha_user -d aha -h localhost
```

查看所有表：
```sql
\dt
```

查看特定表結構：
```sql
\d users
\d videos
\d quizzes
```

### 查看表內容
```sql
SELECT * FROM users;
SELECT * FROM videos;
SELECT * FROM quizzes;
```

---

## 7. 數據持久化

### SQLite vs PostgreSQL 的區別

| 特性 | SQLite | PostgreSQL |
|------|--------|-----------|
| 存儲位置 | 本地檔案 | 資料庫伺服器 |
| 多進程訪問 | 有限制 | 完全支持 |
| 擴展性 | 小型數據 | 大規模數據 |
| 數據持久化 | 檔案持久 | 伺服器持久 |
| 適用場景 | 開發、測試 | 生產環境 |

### 重要提示
- PostgreSQL 中的數據存儲在資料庫伺服器中，即使 Python 應用程式重啟，數據也會保留
- 確保 PostgreSQL 伺服器持續運行

---

## 8. 常見操作

### 備份資料庫
```bash
pg_dump -U aha_user -d aha > backup.sql
```

### 還原資料庫
```bash
psql -U aha_user -d aha < backup.sql
```

### 連接到遠端 PostgreSQL
修改 `.env` 中的 `DATABASE_URL`：
```env
DATABASE_URL=postgresql+psycopg://aha_user:aha_password@your_host:5432/aha
```

### 刪除資料庫（謹慎操作）
```bash
psql -U postgres
DROP DATABASE aha;
```

---

## 9. 使用 Docker 運行 PostgreSQL

如果不想在本機安裝 PostgreSQL，可以使用 Docker：

```yaml
# docker-compose.yml (添加到現有的 docker-compose.yml)
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: aha_user
      POSTGRES_PASSWORD: aha_password
      POSTGRES_DB: aha
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

啟動：
```bash
docker-compose up -d postgres
```

---

## 10. 測試數據庫連接

運行測試確認配置正確：
```bash
cd backend
pytest tests/test_api.py
```

如果測試通過，表示 PostgreSQL 配置成功！

---

## 故障排查

### 連接被拒絕 (Connection refused)
- 確認 PostgreSQL 伺服器已啟動
- 檢查 `DATABASE_URL` 中的主機、端口和憑證是否正確

### 認證失敗 (FATAL: Ident authentication failed)
- 確認用戶名和密碼正確
- 重新創建用戶：`DROP USER aha_user; CREATE USER aha_user ...`

### 資料庫不存在 (database "aha" does not exist)
- 重新創建資料庫：`CREATE DATABASE aha OWNER aha_user;`

### 應用程式無法連接
- 檢查 `.env` 文件是否存在並有正確的 `DATABASE_URL`
- 重新安裝依賴：`pip install -r requirements.txt`
