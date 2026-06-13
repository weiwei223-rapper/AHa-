import "./PageIndex.css";
import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { codeAPI, quizAPI, videoAPI, documentAPI } from "../api";
import ReportModal from "../component/ReportModal";
import { usePoints } from "../context/PointsContext";

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
  const { availablePoints, usePoints: deductPoints } = usePoints();
  const navigate = useNavigate();
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
  const [quizDifficulty, setQuizDifficulty] = useState<Record<string, string>>({});

  const difficultyLevels = [
    { label: "簡單", value: "easy" },
    { label: "中等", value: "medium" },
    { label: "困難", value: "hard" }
  ];

  const [codeOutput, setCodeOutput] = useState("");
  const [codeError, setCodeError] = useState("");
  const [codeLoading, setCodeLoading] = useState(false);

  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportingContext, setReportingContext] = useState("");

  useEffect(() => {
    void fetchVideos();
    void fetchDocs();
  }, [userId]);

  useEffect(() => {
    if (preferredVideoId > 0) void loadSpecificDraft('video', preferredVideoId);
    else if (preferredDocId > 0) void loadSpecificDraft('doc', preferredDocId);
    else if (!quiz) void loadLatestDraft();
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
        video_id: quiz.video_id || undefined,
        document_id: quiz.document_id || undefined,
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
    const specificDifficulty = quizDifficulty[key] || 'medium';

    if (availablePoints < specificCount) {
      setError(`點數不足，生成 ${specificCount} 題需要 ${specificCount} 點。`);
      return;
    }

    setLoading(true); setError("");
    try {
      const response = type === 'video'
        ? await videoAPI.generateQuiz(id, userId, specificCount, specificDifficulty)
        : await documentAPI.generateQuiz(id, userId, specificCount, specificDifficulty);

      const success = deductPoints(specificCount);
      if (!success) {
        setError("點數不足，無法生成。");
        setLoading(false);
        return;
      }

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

  const [gradeDetails, setGradeDetails] = useState<any[]>([]);
  const [backendScore, setBackendScore] = useState(0);

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
        video_id: quiz.video_id || undefined,
        document_id: quiz.document_id || undefined,
        score: total_score,
        total_questions: quiz.questions.length,
        title: quiz.video_title,
        details_json: JSON.stringify(details),
      });
      await quizAPI.deleteDraft(quiz.video_id || quiz.document_id || 0, userId);
      setShowResults(true);
      window.dispatchEvent(new CustomEvent('quiz-completed', { detail: { userId } }));
    } catch (err: any) { setError(`批改失敗: ${err.message}`); }
    finally { setLoading(false); setGrading(false); }
  };

  const executeCode = async () => {
    const userCode = userAnswers[currentQuestionIndex];
    if (!userCode.trim()) {
      setCodeError("沒有可執行的程式碼。");
      return;
    }
    setCodeLoading(true); setCodeOutput(""); setCodeError("");
    try {
      // 嘗試構建測試包裝腳本
      let codeToRun = userCode;
      const tcRaw = quiz?.questions[currentQuestionIndex]?.test_cases?.[0];
      
      if (tcRaw) {
        try {
          const tc = JSON.parse(tcRaw);
          if (tc.input !== undefined) {
            const argsStr = Array.isArray(tc.input) ? tc.input.map((a: any) => JSON.stringify(a)).join(", ") : JSON.stringify(tc.input);
            codeToRun = `${userCode}\n\ntry:\n    print(str(solve(${argsStr})).strip())\nexcept NameError:\n    pass\nexcept Exception as e:\n    print(f"Error: {e}")`;
          }
        } catch (e) {
          // 不是 JSON 格式，直接執行原代碼
        }
      }

      const response = await codeAPI.executeCode({ code: codeToRun });
      setCodeOutput(response.data.output || "");
      setCodeError(response.data.error || "");
      
    } catch (err: any) { setCodeError("網路連線失敗，請稍後再試。"); }
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
      alert("測驗進度已成功儲存至『未完成測驗』頁面！");
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
    if (!window.confirm("確定要放棄目前進度嗎？")) return;
    if (quiz) {
       await quizAPI.deleteDraft(quiz.video_id || quiz.document_id || 0, userId).catch(e => console.error(e));  
    }
    setQuiz(null);
    setCurrentQuestionIndex(0);
    setUserAnswers([]);
    setShowResults(false);
    setCodeOutput("");
    setCodeError("");
  };

  const handleReportQuizError = async (desc: string) => {
    // Reporting logic...
    alert("回報已送出");
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

                  <div className="test-results-details" style={{ margin: '12px 0', padding: '10px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                    {gradeDetails[i]?.test_results?.map((tr: any, j: number) => (
                      <div key={j} style={{ fontSize: '12px', marginBottom: '8px', color: tr.passed ? '#4ade80' : '#fb7185' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span>{tr.passed ? '✓' : '✗'} Test Case {j + 1}</span>
                          {!tr.passed && tr.actual && <span style={{ opacity: 0.8 }}>(Expected: "{tr.expected}", Actual: "{tr.actual}")</span>}
                          {!tr.passed && !tr.actual && <span style={{ opacity: 0.8 }}>(No Output)</span>}
                        </div>
                        {tr.error && (
                          <div style={{ marginTop: '4px', padding: '4px 8px', background: 'rgba(251, 113, 133, 0.1)', borderRadius: '4px', fontFamily: 'monospace', fontSize: '11px', borderLeft: '2px solid #fb7185' }}>
                            Error: {tr.error}
                          </div>
                        )}
                      </div>
                    ))}
                    {(!gradeDetails[i]?.test_results || gradeDetails[i].test_results.length === 0) && (
                      <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>無詳細測試紀錄</div>
                    )}
                  </div>

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
      <style>{`
        .difficulty-slider {
          -webkit-appearance: none;
          width: 100%;
          height: 5px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 5px;
          outline: none;
          margin: 10px 0 !important;
        }
        .difficulty-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 20px;
          height: 20px;
          background: #2bc1f1;
          cursor: pointer;
          border-radius: 50%;
          box-shadow: 0 0 8px rgba(43, 193, 241, 0.5);
          transition: transform 0.1s ease-in-out;
          border: 2px solid #ffffff;
        }
        .difficulty-slider::-webkit-slider-thumb:hover {
          transform: scale(1.1);
        }
        .difficulty-slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          background: #2bc1f1;
          cursor: pointer;
          border-radius: 50%;
          border: 2px solid #ffffff;
          box-shadow: 0 0 8px rgba(43, 193, 241, 0.5);
        }
      `}</style>
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Interactive Learning</div>
          <h1>即時測驗生成</h1>
          <p>支援 YouTube 教材與 PDF 講義，混合四種題型（關鍵字、邏輯、資料處理、函式架構）。</p>
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
              <div className="video-library-top"><div className="video-library-badge">Material</div><h3 className="video-library-title">{v.title}</h3></div>
              <div className="quiz-settings-container">
                <label className="quiz-settings-label">題數</label>
                <div className="quiz-stepper">
                   <button className="quiz-stepper-btn" onClick={() => setQuizCounts(p=>({...p, [key]: Math.max(1, count-1)}))}>-</button>
                   <div className="quiz-stepper-value">{count}</div>
                   <button className="quiz-stepper-btn" onClick={() => setQuizCounts(p=>({...p, [key]: Math.min(10, count+1)}))}>+</button>
                </div>
              </div>
              <div className="quiz-settings-container" style={{ marginTop: '8px', flexDirection: 'column', alignItems: 'stretch', gap: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                   <label className="quiz-settings-label">難度</label>
                   <span style={{ fontSize: '13px', color: '#2bc1f1', fontWeight: '600' }}>
                     {difficultyLevels.find(d => d.value === (quizDifficulty[key] || 'medium'))?.label}
                   </span>
                </div>
                <div style={{ width: '100%', padding: '0', margin: '0' }}>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="1"
                    className="difficulty-slider"
                    value={difficultyLevels.findIndex(d => d.value === (quizDifficulty[key] || 'medium'))}
                    onChange={(e) => setQuizDifficulty(p => ({ ...p, [key]: difficultyLevels[parseInt(e.target.value)].value }))}
                    style={{ width: '100%', cursor: 'pointer', accentColor: '#2bc1f1', margin: '0', padding: '0', display: 'block' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
                    <span>簡單</span>
                    <span>中等</span>
                    <span>困難</span>
                  </div>
                </div>
              </div>
              <div className="video-library-actions">
                <button onClick={() => handleGenerateQuiz(v.id, 'video')} className="page-primary-button">Generate</button>
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
                   <button className="quiz-stepper-btn" onClick={() => setQuizCounts(p=>({...p, [key]: Math.max(1, count-1)}))}>-</button>
                   <div className="quiz-stepper-value">{count}</div>
                   <button className="quiz-stepper-btn" onClick={() => setQuizCounts(p=>({...p, [key]: Math.min(10, count+1)}))}>+</button>
                </div>
              </div>
              <div className="quiz-settings-container" style={{ marginTop: '8px', flexDirection: 'column', alignItems: 'stretch', gap: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                   <label className="quiz-settings-label">難度</label>
                   <span style={{ fontSize: '13px', color: '#2bc1f1', fontWeight: '600' }}>
                     {difficultyLevels.find(d => d.value === (quizDifficulty[key] || 'medium'))?.label}
                   </span>
                </div>
                <div style={{ width: '100%', padding: '0', margin: '0' }}>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="1"
                    className="difficulty-slider"
                    value={difficultyLevels.findIndex(d => d.value === (quizDifficulty[key] || 'medium'))}
                    onChange={(e) => setQuizDifficulty(p => ({ ...p, [key]: difficultyLevels[parseInt(e.target.value)].value }))}
                    style={{ width: '100%', cursor: 'pointer', accentColor: '#2bc1f1', margin: '0', padding: '0', display: 'block' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
                    <span>簡單</span>
                    <span>中等</span>
                    <span>困難</span>
                  </div>
                </div>
              </div>
              <div className="video-library-actions">
                <button onClick={() => handleGenerateQuiz(d.id, 'doc')} className="page-primary-button">Generate</button>
              </div>
            </article>
          );
        })}
      </section>

      {quiz && currentQuestion && (
        <section className="panel-card" style={{marginTop:'30px'}}>
           <div className="quiz-question-card">
             <div className="quiz-question-number" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', flexWrap: 'wrap', gap: '10px' }}>
               <span style={{ whiteSpace: 'nowrap' }}>Question {currentQuestionIndex+1}/{quiz.questions.length} | {currentQuestion.reference_concept}</span>
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
              <div style={{ height: "400px", border: "1px solid rgba(43, 193, 241, 0.3)", borderRadius: "12px", overflow: "hidden", marginBottom: "12px" }}>
                <Editor height="100%" language="python" value={userAnswers[currentQuestionIndex]} onChange={v => handleAnswerChange(v||"")} theme="vs-dark" options={{ automaticLayout: true, fontSize: 14 }} />
              </div>
              {(codeOutput || codeError || codeLoading) && (
                <div style={{marginTop:'15px', padding:'12px', background:'#08111f', borderRadius:'10px', border:'1px solid #ffffff11'}}>
                   <p className="page-eyebrow" style={{ marginBottom: "8px" }}>Test Result:</p>
                   {codeLoading ? (
                     <div style={{color:'#2bc1f1', fontSize:'14px'}}>Running code against test cases...</div>
                   ) : (
                     <pre style={{color:codeError?'#fb7185':'#4ade80', whiteSpace: 'pre-wrap', fontSize:'14px'}}>{codeError || codeOutput || "✓ Execution successful (No output)"}</pre>
                   )}
                </div>
              )}
           </div>
           <div style={{display:'flex', gap:'12px', marginTop:'20px', justifyContent:'flex-end', flexWrap: 'wrap'}}>
             <button onClick={() => void resetQuiz()} className="page-secondary-button" style={{ marginRight: 'auto' }}>放棄測驗</button>
             <button onClick={() => void handleManualSave()} className="page-secondary-button" style={{ borderColor: "#facc15", color: "#facc15" }}>儲存進度</button>
             <button onClick={handlePrevious} disabled={currentQuestionIndex === 0} className="page-secondary-button">Previous</button>
             <button onClick={() => void handleNext()} disabled={grading || loading} className="page-primary-button">{currentQuestionIndex === quiz.questions.length-1 ? (grading ? "Grading..." : "Finish") : "Next"}</button> 
             <button onClick={() => void executeCode()} disabled={codeLoading} className="page-primary-button">{codeLoading ? "Testing..." : "Test"}</button>
           </div>
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

export default Quiz;
