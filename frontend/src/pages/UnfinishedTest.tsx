import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { quizAPI } from '../api';
import "./PageIndex.css";

interface DraftItem {
  id: number;
  video_id: number;
  video_title: string;
  draft_json: string;
  updated_at: string;
}

const UnfinishedTest = () => {
  const navigate = useNavigate();
  const userId = Number(localStorage.getItem("userId") || 1);
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDrafts();
  }, [userId]);

  const fetchDrafts = async () => {
    try {
      setLoading(true);
      const response = await quizAPI.getDrafts(userId);
      setDrafts(response.data);
    } catch (e) {
      console.error("Failed to load drafts", e);
    } finally {
      setLoading(false);
    }
  };

  const handleResume = (videoId: number) => {
    navigate(`/Quiz?videoId=${videoId}`);
  };

  const handleClearDraft = async (videoId: number) => {
    if (!window.confirm("確定要刪除這個未完成的草稿嗎？")) return;
    try {
      await quizAPI.deleteDraft(videoId, userId);
      setDrafts(prev => prev.filter(d => d.video_id !== videoId));
    } catch (e) {
      alert("清空失敗");
    }
  };

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Active Drafts</div>
          <h1>未完成的測驗</h1>
          <p>這裡儲存了您所有尚未完成的練習進度。每個教材都可以擁有獨立的練習進度。</p>
        </div>
      </section>

      {loading ? (
        <div className="page-loading">正在檢查雲端草稿...</div>
      ) : drafts.length > 0 ? (
        <section className="video-library-grid">
          {drafts.map((draft) => {
            const parsedData = JSON.parse(draft.draft_json);
            return (
              <article key={draft.id} className="video-library-card">
                <div className="video-library-top">
                  <div className="video-library-badge" style={{ background: 'rgba(234, 179, 8, 0.15)', color: '#facc15' }}>
                    Pending Draft
                  </div>
                  <h3 style={{ marginTop: '15px' }}>{draft.video_title}</h3>
                  <div style={{ marginTop: '15px', padding: '12px', background: 'rgba(0,0,0,0.2)', borderRadius: '10px' }}>
                    <p style={{ color: '#e2e8f0', fontSize: '0.95rem' }}>
                      <strong>進度：</strong> 第 {parsedData.currentQuestionIndex + 1} 題 / 共 {parsedData.quiz.questions.length} 題
                    </p>
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '5px' }}>
                      <strong>最後更新：</strong> {new Date(draft.updated_at).toLocaleString("zh-TW")}
                    </p>
                  </div>
                </div>
                
                <div className="video-library-actions" style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
                  <button 
                    onClick={() => handleResume(draft.video_id)}
                    className="page-primary-button"
                    style={{ flex: 2, justifyContent: 'center' }}
                  >
                    Continue
                  </button>
                  <button 
                    onClick={() => handleClearDraft(draft.video_id)}
                    className="page-secondary-button"
                    style={{ flex: 1, borderColor: '#fb7185', color: '#fb7185' }}
                  >
                    Delete
                  </button>
                </div>
              </article>
            );
          })}
        </section>
      ) : (
        <div className="empty-state-card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ fontSize: '3.5rem', marginBottom: '20px' }}>📋</div>
          <h3>目前沒有存檔</h3>
          <p style={{ color: '#64748b', marginTop: '10px', maxWidth: '400px', margin: '10px auto' }}>
            當您在 Quiz 頁面按下「儲存進度」後，該教材的進度就會出現在這裡，不會被其他教材覆蓋。
          </p>
          <button 
            onClick={() => navigate('/Quiz')}
            className="page-primary-button" 
            style={{ marginTop: '20px' }}
          >
            去發掘新題目
          </button>
        </div>
      )}
    </div>
  );
};

export default UnfinishedTest;
