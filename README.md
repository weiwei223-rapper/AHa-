# AHa - AI 驅動智慧學習平台

![AHa Banner](https://img.shields.io/badge/Status-In--Development-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react)

AHa 是一個全方位的 AI 驅動學習平台，旨在透過智慧內容分析、互動式測驗以及安全的代碼執行環境，提升學習者的教育體驗。本專案將 AI 技術深度整合進學習流程，實現「分析、練習、檢驗」的自動化循環。

---

# 核心功能 (Core Features)

### 教材管理 (智慧影音與檔案分析)
* **多模態教材解析**：支援匯入 YouTube 影片連結與 PDF 檔案。後端整合 `youtube-transcript-api` 與 `PyMuPDF` 技術萃取內容，並透過 AI 檢索核心知識點，自動生成結構化的教材大綱。
* **彈性算力扣款**：執行分析時，系統將依據消耗的 Token 總量動態計算並扣除點數。
  * **計算公式**：`點數 = math.ceil((Token總數 / 2000) * 100 / 10) * 10`

### 測驗管理 (AI 出題與即時批改)
* **客製化題庫生成**：AI 會嚴格基於影片大綱與教學字幕，模擬專業題庫（如 LeetCode）的邏輯考核設計，自動生成具備測試案例 (Test Cases) 的專屬練習題。
* **一體化安全執行環境**：提供 Monaco Editor 作為前端代碼編輯器，後端結合 Python AST 靜態分析與 Docker 容器沙盒技術，確保使用者程式碼在完全隔離且受控的環境中安全執行與驗證。
* **自動化仲裁與補償機制**：若使用者發現 AI 生成內容（大綱、題目）有誤，可提出回報。系統啟動「AI 自動仲裁」，若判定屬實，將自動退還 1.5 倍的消耗點數並發送 Email 通知。

### AI 家教 (即時互動輔導)
* **雙引擎混合備援架構 (Hybrid AI Fallback)**：系統底層實作容錯機制，預設優先調度本地端部署的開源客製化模型（如基於 Ollama 的 AHa-Tutor），若無回應則無縫備援至雲端 Google Gemini API，確保服務高可用性。
* **動態上下文注入**：AI 助會即時擷取使用者當下觀看的影片大綱或運行錯誤訊息 (Error Traceback) 作為對話上下文，提供精準的邏輯提示與生活化類比。

### 學習成效分析 (視覺化圖表)
* **資料驅動診斷**：系統會自動提取使用者在各類題型的歷史正確率資料，轉化為視覺化的統計圖表（如雷達圖、折線圖），精準量化學習成效與技能弱點。

### 個人資料與點數管理
* **點數微支付**：採用高度彈性的儲值點數包方案，降低自學者的決策壓力與試錯成本。
* **遊戲化成就系統**：內建每日簽到與階段性任務徽章（如：知識累積者），完成任務可獲取額外積分，提升學習黏著度。

---

## 技術棧

### 前端 (Frontend)
- **核心框架**：React 19 + TypeScript
- **建置工具**：Vite
- **樣式處理**：Tailwind CSS
- **代碼編輯**：Monaco Editor (VS Code 同款核心)
- **資料視覺化**：Chart.js + React-chartjs-2

### 後端 (Backend)
- **核心框架**：FastAPI (Python 3.10+)
- **資料庫 ORM**：SQLAlchemy (PostgreSQL)
- **AI 引擎**：Google Gemini Pro / Flash (`google-generativeai`)
- **多媒體處理**：yt-dlp (影片下載), PyMuPDF (PDF 解析)
- **安全認證**：JWT (PyJWT), Passlib (Bcrypt)

---

## 專案結構

```text
AHa-/
├── backend/            # FastAPI 後端核心
│   ├── routers/        # API 模組化路由 (Auth, Users, AI, Payments...)
│   ├── models.py       # SQLAlchemy 資料模型定義
│   ├── ai_analyzer.py  # AI 核心分析邏輯與 Prompt 管理
│   ├── code_compiler.py# 安全沙箱代碼執行引擎
│   └── main.py         # 應用程式入口與初始化
├── frontend/           # React 前端應用
│   ├── src/            # 原始碼 (Components, Hooks, Store, Pages)
│   ├── public/         # 靜態資源與圖標
│   └── vite.config.ts  # Vite 配置
└── .ecpay-skill/       # 綠界支付整合開發指南與 API 參考
```

---

## 安裝與設置

### 準備工作
- Python 3.10+
- Node.js 18+
- PostgreSQL 資料庫環境

### 1. 後端設置 (Backend)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 前端設置 (Frontend)
```bash
cd frontend
npm install
```

### 3. 啟動開發伺服器
- **啟動後端**：
  ```bash
  cd backend
  python main.py
  ```
- **啟動前端**：
  ```bash
  cd frontend
  npm run dev
  ```

---

## 環境變數 (Environment Variables)

為確保專案正常運行，請在 `backend/` 目錄下建立 `.env` 檔案。以下是必要的配置清單：

### `.env` 範例
```env
# 資料庫配置
DATABASE_URL=postgresql://user:password@localhost:5432/aha_db

# 安全認證
SECRET_KEY=你的JWT加密密鑰
ALGORITHM=HS256

# Google Gemini API
GEMINI_API_KEY=你的Gemini_API密鑰

# 綠界支付 (ECPay) - 測試環境
ECPAY_MERCHANT_ID=2000132
ECPAY_HASH_KEY=5294y06JbCwE5YzTQ85
ECPAY_HASH_IV=v77hoKGq4kWxJvU5

# 郵件服務 (用於驗證碼)
EMAIL_USER=你的Gmail帳號
EMAIL_PASSWORD=你的Gmail應用程式密碼
```

---

## 使用指南 (Usage / Quick Start)

1.  **註冊與登入**：建立個人帳號，首次登入可獲得系統贈送的初始點數。
2.  **上傳教材**：
    - 貼上 **YouTube 連結**：系統將自動抓取字幕或進行語音辨識。
    - 上傳 **PDF 文件**：AI 將解析內容並提取關鍵知識點。
3.  **生成學習筆記**：點擊「AI 分析」，系統會生成結構化的摘要與重點。
4.  **練習與測驗**：點擊「開始測驗」，挑戰 AI 根據內容生成的題目。如果是程式題，可直接在網頁端撰寫代碼並執行驗證。
5.  **查看表現**：在個人檔案頁面查看學習趨勢圖表，並領取成就獎勵。

---

## 授權條款 (License)

本專案採用 **MIT License** 授權。詳見 [LICENSE](LICENSE) 檔案。

---

## 開發進度與計畫

詳細功能說明與改進計畫請參考：
- [成就系統改進方案](ACHIEVEMENT_SYSTEM_IMPROVEMENTS.md)
- [AI 測驗設置指南](AI_QUIZ_SETUP.md)
- [開發指南 (Gemini CLI)](GEMINI.md)

*本專案僅供學習與作品展示使用，部分 AI 功能可能需要有效的 API Key 才能運行。*
