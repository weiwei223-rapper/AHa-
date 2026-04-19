# 步驟 10 前端功能驗收清單

## 測試前準備

```bash
cd backend
python main.py
```

```bash
cd frontend
npm run dev
```

開啟 `http://localhost:5173`。

---

## 功能驗收項目

- [ ] 註冊頁：欄位驗證（空值、信箱格式、密碼長度、確認密碼）
- [ ] 登入頁：可用註冊帳號登入，錯誤帳密有提示
- [ ] 首頁：卡片/統計區塊正常顯示
- [ ] 教材管理：新增影片、辨識、生成大綱，列表可更新
- [ ] 測驗管理：生成題目、開始作答、提交後分數更新
- [ ] AI 家教：輸入訊息可回覆（需 `VITE_ANTHROPIC_API_KEY`）
- [ ] 學習回顧：圖表與時間軸正常顯示
- [ ] 個人資料：修改名稱後重新整理仍保留
- [ ] 登出：session/token 清除並回到登入畫面

---

## 交付判定

- [ ] 前端 `npm run build` 成功
- [ ] 後端 `pytest -q` 全綠
- [ ] 效能檢核 `python scripts/perf_check.py` 通過
