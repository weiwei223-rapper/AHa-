# AHa 交付部署說明

本文件對應 `IMPLEMENTATION_ROADMAP.md` 的步驟 10 / 12 / 14，提供可交付的測試、效能與部署流程。

## 1) 交付前驗證（必跑）

### 後端自動化測試

```bash
cd backend
python -m pip install -r requirements.txt
pytest -q
```

### 後端效能檢核

```bash
cd backend
python scripts/perf_check.py
```

說明：
- `perf_check.py` 會檢查 `/videos` 與 `/quizzes` 的平均、p95、max 延遲。
- 目前門檻為 `p95 < 500ms`，超過會直接以非 0 狀態碼失敗。

### 前端建置驗證

```bash
cd frontend
npm install
npm run build
```

---

## 2) 本機 Docker 部署

專案根目錄執行：

```bash
docker compose up --build
```

服務位址：
- 前端：`http://localhost:5173`
- 後端：`http://localhost:8000`

停止服務：

```bash
docker compose down
```

---

## 3) 環境變數設定

### `backend/.env`

必填：
- `DATABASE_URL`（預設 `sqlite:///./aha.db`）
- `API_HOST`
- `API_PORT`
- `LOG_LEVEL`
- `JWT_SECRET`（正式環境請更換）

### `frontend/.env.local`

必填：
- `VITE_API_BASE_URL`（例如 `http://localhost:8000`）
- `VITE_ANTHROPIC_API_KEY`（若要啟用 AI 功能）

---

## 4) 生產啟動建議

後端容器預設使用 Gunicorn + Uvicorn Worker：
- 設定檔：`backend/gunicorn_conf.py`
- 啟動指令：`gunicorn -c gunicorn_conf.py main:app`

優點：
- 比單純 `uvicorn --reload` 更適合生產環境。
- 可透過 worker 數量提升並行吞吐。

---

## 5) 日誌與監控建議

目前已在 API 層提供：
- 統一日誌格式（含時間、等級、路徑、狀態碼、耗時）
- 回應 header `X-Process-Time`

建議正式環境再補：
- 反向代理（Nginx/Caddy）存取日誌
- 錯誤告警（Sentry 或雲端監控）
- 依環境分級的 LOG_LEVEL 策略（dev/info, prod/warn）
