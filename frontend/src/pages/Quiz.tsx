import "./PageIndex.css";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { codeAPI, quizAPI, videoAPI, documentAPI } from "../api";
import ReportModal from "../component/ReportModal";

type VideoItem = {
  id: number;
  video_link: string;
  title?: string | null;
  outline?: string | null;
  created_at: string;
};

type DocumentItem = {
  id: number;
  filename: string;
  title: string;
};

type QuizQuestion = {
  question: string;
  correct_answer: string;
  explanation?: string | null;
  reference_concept?: string | null;
  question_type?: string;
  source_time?: string | null;
  source_excerpt?: string | null;
  starter_code?: string | null;
  test_cases?: string[];
};

type QuizData = {
  video_id: number | null;
  document_id?: number | null;
  video_title: string;
  quiz_type?: string;
  questions: QuizQuestion[];
  consumed_points?: number;
};

const Quiz = () => {
  const [searchParams] = useSearchParams();
  const preferredVideoId = Number(searchParams.get("videoId") || 0);
  const preferredDocId = Number(searchParams.get("docId") || 0);
  const userId = Number(localStorage.getItem("userId") || 1);

  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState<string[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const [grading, setGrading] = useState(false);
  const [error, setError] = useState("");
  const [quizCounts, setQuizCounts] = useState<Record<string, number>>({}); 

  const [codeOutput, setCodeOutput] = useState("");
  const [codeError, setCodeError] = useState("");
  const [codeLoading, setCodeLoading] = useState(false);

  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportingContext, setReportingContext] = useState("");

  useEffect(() => {
    void fetchVideos();
    void fetchDocs();
  }, [userId]);

  // 載入草稿邏輯整合
  useEffect(() => {
    if (preferredVideoId > 0) {
      void loadSpecificDraft('video', preferredVideoId);
    } else if (preferredDocId > 0) {
      void loadSpecificDraft('doc', preferredDocId);
    } else if (!quiz) {
      void loadLatestDraft();
    }
  }, [preferredVideoId, preferredDocId, userId]);

  const loadLatestDraft = async () => {
    try {
      const response = await quizAPI.getDrafts(userId);
      const drafts = response.data;
      if (drafts.length > 0) {
        const latest = [...drafts].sort((a: any, b: any) => 
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )[0];
        
        const parsed = JSON.parse(latest.draft_json);
        if (parsed.quiz) {
          setQuiz(parsed.quiz);
          setUserAnswers(parsed.userAnswers || []);
          setCurrentQuestionIndex(parsed.currentQuestionIndex || 0);
          setShowResults(false);
        }
      }
    } catch (e) {
      console.error("Failed to load latest draft", e);
    }
  };

  const loadSpecificDraft = async (type: 'video' | 'doc', id: number) => {
    try {
      const response = await quizAPI.getDrafts(userId);
      const drafts = response.data;
      const targetDraft = drafts.find((d: any) => type === 'video' ? d.video_id === id : d.document_id === id);
      if (targetDraft) {
        const parsed = JSON.parse(targetDraft.draft_json);
        if (parsed.quiz) {
          setQuiz(parsed.quiz);
          setUserAnswers(parsed.userAnswers || []);
          setCurrentQuestionIndex(parsed.currentQuestionIndex || 0);
          setShowResults(false);
        }
      }
    } catch (e) { console.error("Draft restore failed", e); }
  };

  useEffect(() => {
    if (quiz && !showResults) {
      const state = { quiz, userAnswers, currentQuestionIndex, timestamp: new Date().getTime() };
      quizAPI.upsertDraft({
        user_id: userId,
        video_id: quiz.video_id || 0,
        document_id: quiz.document_id || 0,
        draft_json: JSON.stringify(state)
      }).catch(err => console.error("Sync draft failed", err));
    }
  }, [quiz, userAnswers, currentQuestionIndex, showResults, userId]);

  const fetchVideos = async () => {
    try {
      const response = await videoAPI.getVideos(userId);
      setVideos(response.data);
    } catch (err) { console.error(err); }
  };

  const fetchDocs = async () => {
    try {
      const response = await documentAPI.getDocuments(userId);
      setDocs(response.data);
    } catch (err) { console.error(err); }
  };

  const handleGenerateQuiz = async (id: number, type: 'video' | 'doc') => {
    const key = `${type}-${id}`;
    const specificCount = quizCounts[key] || 5;
    setLoading(true); setError("");
    try {
      const response = type === 'video' 
        ? await videoAPI.generateQuiz(id, userId, specificCount)
        : await documentAPI.generateQuiz(id, userId, specificCount);
      const nextQuiz = response.data as QuizData;
      setQuiz(nextQuiz);
      setCurrentQuestionIndex(0);
      setUserAnswers(nextQuiz.questions.map(q => q.starter_code || ""));
      setShowResults(false);
      window.dispatchEvent(new CustomEvent('points-updated', { detail: { userId } }));
    } catch (err: any) {
      setError(err.response?.data?.detail || "無法產生測驗");
    } finally { setLoading(false); }
  };

  const handleAnswerChange = (value: string) => {
    const next = [...userAnswers];
    next[currentQuestionIndex] = value;
    setUserAnswers(next);
  };

  const handlePrevious = () => {
    setCurrentQuestionIndex(prev => Math.max(0, prev - 1));
  };

  const handleNext = async () => {
    if (!quiz) return;
    if (currentQuestionIndex < quiz.questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
      return;
    }

    if (grading) return;
    setGrading(true);
    setLoading(true);
    try {
      const gradeRes = await quizAPI.gradeQuiz(quiz.video_id || 0, { 
        user_id: userId, 
        answers: userAnswers,
        document_id: quiz.document_id 
      });
      const { total_score, details } = gradeRes.data;
      setBackendScore(total_score);
      setGradeDetails(details);
      
      await quizAPI.createResult({
        user_id: userId,
        video_id: quiz.video_id || null as any,
        document_id: quiz.document_id || null as any,
        score: total_score,
        total_questions: quiz.questions.length,
        title: quiz.video_title,
        details_json: JSON.stringify(details),
      });
      await quizAPI.deleteDraft(quiz.video_id || quiz.document_id || 0, userId);
      setShowResults(true);
    } catch (err: any) { setError(`批改失敗: ${err.message}`); }
    finally { 
      setLoading(false); 
      setGrading(false);
    }
  };

  const [gradeDetails, setGradeDetails] = useState<any[]>([]);
  const [backendScore, setBackendScore] = useState(0);

  const executeCode = async () => {
    setCodeLoading(true); setCodeOutput(""); setCodeError("");
    try {
      const userCode = userAnswers[currentQuestionIndex];
      const testBlock = quiz?.questions[currentQuestionIndex]?.test_cases?.join("\n") || "";
      const script = `${userCode}\n\n${testBlock}`;
      const response = await codeAPI.executeCode({ code: script });
      setCodeOutput(response.data.output);
      setCodeError(response.data.error);
    } catch (err: any) { setCodeError("執行失敗"); }
    finally { setCodeLoading(false); }
  };

  const handleManualSave = async () => {
    if (!quiz) return;
    try {
      const state = { quiz, userAnswers, currentQuestionIndex, timestamp: new Date().getTime() };
      await quizAPI.upsertDraft({
        user_id: userId,
        video_id: quiz.video_id || 0,
        document_id: quiz.document_id || 0,
        draft_json: JSON.stringify(state)
      });
      alert("該影片測驗進度已成功儲存至『Unfinished Test』頁面！");
      setQuiz(null);
      setCurrentQuestionIndex(0);
      setUserAnswers([]);
      setShowResults(false);
      setCodeOutput("");
      setCodeError("");
    } catch (err) {
      console.error("Failed to save draft manually", err);
      alert("儲存失敗，請稍後再試。");
    }
  };

  const resetQuiz = async () => {
    if (!quiz) return;
    if (!window.confirm("確定要放棄目前的測驗嗎？進度將會被刪除。")) return;
    
    try {
       await quizAPI.deleteDraft(quiz.video_id || quiz.document_id || 0, userId);
       setQuiz(null);
       setCurrentQuestionIndex(0);
       setUserAnswers([]);
       setShowResults(false);
       setCodeOutput("");
       setCodeError("");
    } catch (e) { console.error(e); }
  };

  const handleReportQuizError = async (description: string) => {
    // 這裡可以串接 report API
    alert(`感謝回報：${description}`);
  };

  if (showResults && quiz) {
    return (
      <div className="page-shell">
        <section className="page-hero">
          <div>
            <div className="page-eyebrow">Quiz Result</div>
            <h1>{quiz.video_title}</h1>
            <p>已根據您上傳的內容完成邏輯批改。</p>
          </div>
          <div className="page-hero-metric">
            <span>Score</span>
            <strong>{backendScore}%</strong>
          </div>
        </section>
        <section className="panel-card">
           <div className="quiz-review-list">
             {quiz.questions.map((q, i) => (
               <article key={i} className="quiz-review-card">
                  <div className={`quiz-review-status ${gradeDetails[i]?.passed ? 'correct' : 'failed'}`}>
                    {gradeDetails[i]?.passed ? 'Logic Correct' : 'Logic Failed'}
                  </div>
                  <h3>{i+1}. {q.question}</h3>
                  <div className="code-comparison">
                     <p>你的解答：</p>
                     <pre className="code-snippet">{userAnswers[i]}</pre>
                     <p>參考答案：</p>
                     <pre className="code-snippet green">{q.correct_answer}</pre>
                  </div>
               </article>
             ))}
           </div>
           <button onClick={() => setQuiz(null)} className="page-primary-button" style={{marginTop:'20px'}}>回到列表</button>
        </section>
      </div>
    );
  }

  const currentQuestion = quiz?.questions[currentQuestionIndex];

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Interactive Learning</div>
          <h1>即時測驗生成</h1>
          <p>支援 YouTube 影片與 PDF 講義，混合四種題型（關鍵字、邏輯、資料處理、函式架構）。</p>
        </div>
      </section>

      {error && <div className="page-error">{error}</div>}
      {loading && <div className="page-loading">正在處理測驗數據...</div>}

      <section className="video-library-grid">
        {videos.map(v => {
          const key = `video-${v.id}`;
          const count = quizCounts[key] || 5;
          return (
            <article key={v.id} className="video-library-card">
              <div className="video-library-top"><div className="video-library-badge">Video</div><h3 className="video-library-title">{v.title}</h3></div>
              <div className="quiz-settings-container">
                <label className="quiz-settings-label">題數</label>
                <div className="quiz-stepper">
                   <button className="quiz-stepper-btn" onClick={() => setQuizCounts(p=>({...p, [key]: Math.max(1, count-1)}))} disabled={loading || !!quiz}>-</button>
                   <div className="quiz-stepper-value">{count}</div>
                   <button className="quiz-stepper-btn" onClick={() => setQuizCounts(p=>({...p, [key]: Math.min(10, count+1)}))} disabled={loading || !!quiz}>+</button>
                </div>
              </div>
              <div className="video-library-actions">
                <button onClick={() => handleGenerateQuiz(v.id, 'video')} className="page-primary-button" disabled={loading || !!quiz}>Generate</button>
              </div>
            </article>
          );
        })}
        {docs.map(d => {
          const key = `doc-${d.id}`;
          const count = quizCounts[key] || 5;
          return (
            <article key={d.id} className="video-library-card">
              <div className="video-library-top"><div className="video-library-badge" style={{backgroundColor:'#a855f722', color:'#a855f7'}}>PDF</div><h3 className="video-library-title">{d.title}</h3></div>
              <div className="quiz-settings-container">
                <label className="quiz-settings-label">題數</label>
                <div className="quiz-stepper">
                   <button className="quiz-stepper-btn" onClick={() => setQuizCounts(p=>({...p, [key]: Math.max(1, count-1)}))} disabled={loading || !!quiz}>-</button>
                   <div className="quiz-stepper-value">{count}</div>
                   <button className="quiz-stepper-btn" onClick={() => setQuizCounts(p=>({...p, [key]: Math.min(10, count+1)}))} disabled={loading || !!quiz}>+</button>
                </div>
              </div>
              <div className="video-library-actions">
                <button onClick={() => handleGenerateQuiz(d.id, 'doc')} className="page-primary-button" disabled={loading || !!quiz}>Generate</button>
              </div>
            </article>
          );
        })}
      </section>

      {quiz && currentQuestion && (
        <section className="panel-card" style={{marginTop:'30px'}}>
           {quiz.consumed_points !== undefined && (
            <div className="quiz-score-band" style={{ marginBottom: '20px', backgroundColor: 'rgba(56, 189, 248, 0.1)', borderColor: 'rgba(56, 189, 248, 0.3)' }}>
              <p style={{ color: '#fb7185' }}>本次生成扣除點數：<strong>{quiz.consumed_points}</strong> 點</p>
            </div>
          )}
           <div className="quiz-question-card">
             <div className="quiz-question-number" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
               <span>Question {currentQuestionIndex+1}/{quiz.questions.length} | {currentQuestion.reference_concept || "Python"}</span>
               <button 
                onClick={() => {
                  setReportingContext(`第 ${currentQuestionIndex + 1} 題生成錯誤`);
                  setIsReportModalOpen(true);
                }}
                className="chat-message-report-btn"
                style={{ margin: 0 }}
              >
                回報題目錯誤
              </button>
             </div>
             <h2>{currentQuestion.question}</h2>
           </div>
           <div style={{marginTop:'20px'}}>
              <p className="page-eyebrow">Python Editor (填入 ___ 處內容)</p>
              <div style={{ height: "400px", border: "1px solid rgba(43, 193, 241, 0.3)", borderRadius: "12px", overflow: "hidden", marginBottom: "12px" }}>
                <Editor height="100%" language="python" value={userAnswers[currentQuestionIndex]} onChange={v => handleAnswerChange(v||"")} theme="vs-dark" options={{ automaticLayout: true, fontSize: 14 }} />
              </div>
              {(codeOutput || codeError) && (
                <div style={{marginTop:'15px', padding:'12px', background:'#08111f', borderRadius:'10px', border:'1px solid rgba(148, 163, 184, 0.2)'}}>
                  <p className="page-eyebrow" style={{ marginBottom: "8px" }}>Test Result:</p>
                  {codeOutput && <pre style={{ margin: 0, color: "#4ade80", fontSize: "13px", whiteSpace: "pre-wrap" }}>{codeOutput}</pre>}
                  {codeError && <pre style={{ margin: codeOutput ? "10px 0 0" : 0, color: "#fb7185", fontSize: "13px", whiteSpace: "pre-wrap" }}>{codeError}</pre>}
                </div>
              )}
           </div>
           <div style={{display:'flex', gap:'12px', marginTop:'20px', justifyContent:'flex-end'}}>
             <button onClick={() => void resetQuiz()} className="page-secondary-button" style={{ marginRight: 'auto' }}>放棄測驗</button>
             <button onClick={() => void handleManualSave()} className="page-secondary-button" style={{ borderColor: "#facc15", color: "#facc15" }}>儲存進度</button>
             <button onClick={handlePrevious} disabled={currentQuestionIndex === 0} className="page-secondary-button">Previous</button>
             <button onClick={() => void handleNext()} disabled={grading || loading} className="page-primary-button">{currentQuestionIndex === quiz.questions.length - 1 ? (grading ? "Grading..." : "Finish") : "Next"}</button>
             <button onClick={() => void executeCode()} disabled={codeLoading} className="page-primary-button">{codeLoading ? "Testing..." : "Test"}</button>
           </div>
        </section>
      )}

      <ReportModal 
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        onSubmit={handleReportQuizError}
        title="回報題目錯誤"
        subtitle={reportingContext || "如果您發現 AI 生成的題目有亂碼、邏輯錯誤時告訴我們。"}
      />
    </div>
  );
};

export default Quiz;
