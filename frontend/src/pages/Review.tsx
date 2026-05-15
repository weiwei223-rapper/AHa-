import { useEffect, useState } from "react";
import { quizAPI } from "../api";
import "./PageIndex.css";
import ReportModal from "../component/ReportModal";

type QuizResultItem = {
  id: number;
  video_id: number;
  title?: string | null;
  score: number;
  total_questions: number;
  details_json?: string | null;
  completed_at: string;
};

const Review = () => {
  const userId = Number(localStorage.getItem("userId") || 1);
  const [results, setResults] = useState<QuizResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedResult, setSelectedResult] = useState<QuizResultItem | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  useEffect(() => {
    void fetchResults();
  }, []);

  const handleReportQuizError = async (description: string) => {
    if (!selectedResult) return;
    try {
      await quizAPI.reportQuizError(selectedResult.id, description);
      alert("感謝您的回報！題目錯誤已記錄。");
    } catch (err) {
      console.error("Error reporting quiz error:", err);
      alert("提交回報時發生錯誤，請稍後再試。");
    }
  };

  const fetchResults = async () => {
    try {
      setLoading(true);
      const res = await quizAPI.getResults(userId);
      setResults(res.data);
    } catch (err: any) {
      console.error("Error fetching results:", err);
      setError("無法載入歷史作答紀錄");
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (e: React.MouseEvent, res: QuizResultItem) => {
    e.stopPropagation();
    setEditingId(res.id);
    setNewTitle(res.title || "未命名測驗");
  };

  const handleRename = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await quizAPI.updateResult(id, { title: newTitle });
      setResults(results.map((r) => (r.id === id ? { ...r, title: newTitle } : r)));
      setEditingId(null);
    } catch (err) {
      alert("更改名稱失敗");
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!window.confirm("確定要刪除這筆測驗紀錄嗎？")) return;
    try {
      await quizAPI.deleteResult(id);
      setResults(results.filter((r) => r.id !== id));
    } catch (err) {
      alert("刪除失敗");
    }
  };

  const renderDetails = (detailsJson: string | null | undefined) => {
    if (!detailsJson) return <p>無詳細作答資料</p>;
    try {
      const details = JSON.parse(detailsJson);
      return (
        <div className="quiz-review-list">
          {details.map((detail: any, index: number) => (
            <article key={index} className="quiz-review-card">
              <div className={`quiz-review-status ${detail.passed ? "correct" : "review"}`}>
                {detail.passed ? "Logic Correct" : "Logic Failed"}
              </div>
              {detail.question_text && (
                <h3 style={{ marginTop: "12px", fontSize: "1.1em" }}>{detail.question_text}</h3>
              )}
              <div style={{ marginTop: "12px" }}>
                <p><strong>驗證詳情：</strong></p>
                <ul style={{ listStyle: "none", padding: 0 }}>
                  {detail.test_results?.map((res: any, i: number) => (
                    <li key={i} style={{ color: res.passed ? "#4ade80" : "#fb7185", fontSize: "0.9em", marginBottom: "4px" }}>
                      Test {i+1}: {res.passed ? "✓ Passed" : `✗ Failed (Expected: ${res.expected}, Actual: ${res.actual})`}
                    </li>
                  ))}
                </ul>
              </div>
              <div style={{ marginTop: "12px" }}>
                <p><strong>當時作答：</strong></p>
                <pre className="code-snippet">{detail.user_answer || detail.user_full_code || "N/A"}</pre>
              </div>
            </article>
          ))}
        </div>
      );
    } catch {
      return <p>資料格式錯誤，無法解析詳情。</p>;
    }
  };

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">History Review</div>
          <h1>歷史作答紀錄</h1>
          <p>在這裡你可以回顧過去所有的測驗表現、更改名稱，所有的學習腳印都將被永久保留。</p>
        </div>
      </section>

      {error && <div className="page-error">{error}</div>}
      {loading && <div className="page-loading">正在載入紀錄...</div>}

      {!loading && !selectedResult && (
        <section className="video-library-grid">
          {results.map((res) => (
            <article key={res.id} className="video-library-card" style={{ cursor: "pointer" }} onClick={() => setSelectedResult(res)}>
              <div className="video-library-top">
                <div className="video-library-badge">Score: {res.score}%</div>
                {editingId === res.id ? (
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }} onClick={e => e.stopPropagation()}>
                    <input 
                      className="page-input" 
                      value={newTitle} 
                      onChange={e => setNewTitle(e.target.value)} 
                      autoFocus
                    />
                    <button className="page-primary-button" onClick={(e) => handleRename(e, res.id)}>儲存</button>
                    <button className="page-secondary-button" onClick={() => setEditingId(null)}>取消</button>
                  </div>
                ) : (
                  <h3 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    {res.title || "未命名測驗"}
                    <button style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '0.8em' }} onClick={(e) => startEdit(e, res)}>✎ 修改</button>
                  </h3>
                )}
                <p className="video-library-description">
                  測驗時間: {new Date(res.completed_at).toLocaleString("zh-TW")}
                </p>
                <p className="video-library-description">
                  答對題數: {Math.round((res.score / 100) * res.total_questions)} / {res.total_questions}
                </p>
              </div>
              <div className="video-library-actions" style={{ marginTop: '12px' }}>
                <button className="page-primary-button" style={{ flex: 1 }}>查看詳情</button>
                <button className="page-secondary-button" style={{ color: '#fb7185', borderColor: '#fb7185' }} onClick={(e) => handleDelete(e, res.id)}>刪除紀錄</button>
              </div>
            </article>
          ))}
          {results.length === 0 && (
            <div className="empty-state-card">
              <h3>尚無測驗紀錄</h3>
              <p>完成測驗後，紀錄會自動出現在這裡。</p>
            </div>
          )}
        </section>
      )}

      {selectedResult && (
        <section className="panel-card">
          <div style={{ marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button onClick={() => setSelectedResult(null)} className="page-secondary-button">
              ← 返回列表
            </button>
            <button onClick={() => setIsReportModalOpen(true)} className="chat-message-report-btn">
              回報題目錯誤
            </button>
          </div>
          <h2>{selectedResult.title || "測驗詳細回顧"}</h2>
          <p style={{ color: "#94a3b8", marginBottom: "20px" }}>
            完成時間：{new Date(selectedResult.completed_at).toLocaleString("zh-TW")} | 分數：{selectedResult.score}%
          </p>
          {renderDetails(selectedResult.details_json)}
        </section>
      )}
      <ReportModal 
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        onSubmit={handleReportQuizError}
        title="回報題目錯誤"
        subtitle="如果您發現 AI 生成的題目有亂碼、邏輯錯誤或答案不正確，請告訴我們。"
      />
    </div>
  );
};

export default Review;
