import React from 'react';
import "./PageIndex.css";

const Tutorial = () => {
  const tutorialSteps = [
    {
      title: "1. 探索影片",
      content: "在『Video』頁面貼上 YouTube 連結。我們支援 Python 相關的教學影片，系統會自動為您生成大綱與逐字稿。",
      icon: "📺"
    },
    {
      title: "2. 生成測驗",
      content: "前往『Quiz』頁面選擇已解析的影片，調整您想要練習的題目數量（1-10 題），點擊 Generate 即可開始。",
      icon: "🎯"
    },
    {
      title: "3. 程式實戰",
      content: "在瀏覽器編輯器中補全程式碼。您可以使用『Test』按鈕即時執行程式並查看輸出結果。",
      icon: "💻"
    },
    {
      title: "4. AI 助教",
      content: "測驗完成後，系統會給予邏輯診斷。遇到困難時，右下角的 Workspace Chat 隨時待命為您解答影片中的難點。",
      icon: "🤖"
    }
  ];

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Learning Guide</div>
          <h1>使用教學</h1>
          <p>歡迎來到 AHa AI 學習平台！跟隨以下步驟，開啟您的 Python 學習之旅。</p>
        </div>
      </section>

      <section className="video-library-grid">
        {tutorialSteps.map((step, index) => (
          <article key={index} className="video-library-card" style={{ minHeight: 'auto' }}>
            <div style={{ fontSize: '2rem', marginBottom: '15px' }}>{step.icon}</div>
            <h3 style={{ margin: '0 0 10px 0', color: '#2bc1f1' }}>{step.title}</h3>
            <p style={{ color: '#94a3b8', lineHeight: '1.6', fontSize: '0.95rem' }}>
              {step.content}
            </p>
          </article>
        ))}
      </section>

      <section className="panel-card" style={{ marginTop: '20px' }}>
        <h2>常見問題</h2>
        <div style={{ marginTop: '20px', display: 'grid', gap: '20px' }}>
          <div>
            <h4 style={{ color: 'white', marginBottom: '8px' }}>Q: 為什麼有些影片無法上傳？</h4>
            <p style={{ color: '#94a3b8' }}>為了保持平台專業性，我們僅允許與 Python 程式設計相關的內容。系統會自動偵測標題與內容進行過濾。</p>
          </div>
          <div>
            <h4 style={{ color: 'white', marginBottom: '8px' }}>Q: 測驗進度會消失嗎？</h4>
            <p style={{ color: '#94a3b8' }}>不會。您的測驗進度會即時同步到雲端資料庫。您可以在『Unfinished Test』中查看並隨時繼續練習。</p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Tutorial;
