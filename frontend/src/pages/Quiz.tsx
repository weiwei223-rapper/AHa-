import "./PageIndex.css";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { codeAPI, quizAPI, videoAPI, userAPI } from "../api";
import ReportModal from "../component/ReportModal";

type VideoItem = {
  id: number;
  video_link: string;
  title?: string | null;
  outline?: string | null;
  created_at: string;
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

type TokenUsage = {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
};

type QuizData = {
  video_id: number;
  video_title: string;
  quiz_type?: string;
  questions: QuizQuestion[];
  token_usage?: TokenUsage;
  consumed_points?: number;
};

const Quiz = () => {
  const [searchParams] = useSearchParams();
  const preferredVideoId = Number(searchParams.get("videoId") || 0);
  const userId = Number(localStorage.getItem("userId") || 1);

  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState<string[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [outlineWarning, setOutlineWarning] = useState("");
  const [quizCounts, setQuizCounts] = useState<Record<number, number>>({}); // 每部影片獨立數量

  const [codeOutput, setCodeOutput] = useState("");
  const [codeError, setCodeError] = useState("");
  const [codeLoading, setCodeLoading] = useState(false);

  // 1. 初始化載入影片清單
  useEffect(() => {
    void fetchVideos();
  }, [userId]);

  // 2. 當有指定影片時，自動載入該影片的草稿 (若有)
  useEffect(() => {
    if (preferredVideoId > 0) {
      void loadSpecificDraft(preferredVideoId);
    }
  }, [preferredVideoId]);

  const loadSpecificDraft = async (videoId: number) => {
    try {
      const response = await quizAPI.getDrafts(userId);
      const drafts = response.data;
      const targetDraft = drafts.find((d: any) => d.video_id === videoId);
      
      if (targetDraft) {
        const parsed = JSON.parse(targetDraft.draft_json);
        if (parsed.quiz) {
          setQuiz(parsed.quiz);
          setUserAnswers(parsed.userAnswers || []);
          setCurrentQuestionIndex(parsed.currentQuestionIndex || 0);
          setShowResults(false);
          console.log(`Draft restored for video ${videoId}`);
        }
      }
    } catch (e) {
      console.error("Failed to restore draft from backend", e);
    }
  };

  // 3. 自動儲存進度到該影片專屬的草稿欄位
  useEffect(() => {
    if (quiz && !showResults) {
      const state = {
        quiz,
        userAnswers,
        currentQuestionIndex,
        timestamp: new Date().getTime()
      };
      // 自動背景儲存
      quizAPI.upsertDraft({
        user_id: userId,
        video_id: quiz.video_id,
        draft_json: JSON.stringify(state)
      }).catch(err => console.error("Failed to sync draft", err));
    }
  }, [quiz, userAnswers, currentQuestionIndex, showResults, userId]);

  useEffect(() => {
    if (!quiz) return;
    setCodeOutput("");
    setCodeError("");
  }, [quiz, currentQuestionIndex]);

  useEffect(() => {
    if (!preferredVideoId || videos.length === 0) return;
    const target = videos.find((video) => video.id === preferredVideoId);
    if (target && !target.outline) {
      setOutlineWarning("Outline is not available for this video yet. Please generate an outline first.");
    } else {
      setOutlineWarning("");
    }
  }, [preferredVideoId, videos]);

  const currentQuestion = quiz?.questions[currentQuestionIndex] ?? null;

  const fetchVideos = async () => {
    try {
      const response = await videoAPI.getVideos(userId);
      setVideos(response.data);
    } catch (err: any) {
      console.error("Error fetching videos:", err);
      setError(err.response?.data?.detail || "無法載入影片列表");
    }
  };

  const handleGenerateQuiz = async (videoId: number) => {
    const video = videos.find((v) => v.id === videoId);
    if (!video || !video.outline) {
      setOutlineWarning("Outline is not available for this video yet. Please generate an outline first.");
      return;
    }

    const specificCount = quizCounts[videoId] || 5;
    setLoading(true);
    setError("");
    setOutlineWarning("");
    try {
      const response = await videoAPI.generateQuiz(videoId, userId, specificCount);
      const nextQuiz = response.data as QuizData;
      setQuiz(nextQuiz);
      setCurrentQuestionIndex(0);
      setUserAnswers(nextQuiz.questions.map(q => q.starter_code || ""));
      setShowResults(false);
      setLastResultId(null);
      window.dispatchEvent(new CustomEvent('points-updated', { detail: { userId } }));
    } catch (err: any) {
      console.error("Error generating quiz:", err);
      setError(err.response?.data?.detail || "無法產生影片填空題");
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (value: string) => {
    const next = [...userAnswers];
    next[currentQuestionIndex] = value;
    setUserAnswers(next);
  };

  const handlePrevious = () => {
    setCurrentQuestionIndex((prev) => Math.max(prev - 1, 0));
  };

  const [grading, setGrading] = useState(false);
  const [gradeDetails, setGradeDetails] = useState<any[]>([]);
  const [backendScore, setBackendScore] = useState(0);
  const [lastResultId, setLastResultId] = useState<number | null>(null);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportingContext, setReportingContext] = useState<string>("");

  const handleReportQuizError = async (description: string) => {
    try {
      const fullDescription = reportingContext ? `[${reportingContext}] ${description}` : description;
      if (lastResultId) {
        await quizAPI.reportQuizError(lastResultId, fullDescription);
      } else if (quiz) {
        // 如果還沒產生結果，先建立一個初始紀錄
        const resultRes = await quizAPI.createResult({
          user_id: userId,
          video_id: quiz.video_id,
          score: 0,
          total_questions: quiz.questions.length,
          title: `[回報中] ${quiz.video_title}`,
          error_report: fullDescription
        });
        if (resultRes.data && resultRes.data.id) {
          setLastResultId(resultRes.data.id);
        }
      } else {
        return;
      }
      alert("感謝您的回報！錯誤內容已記錄。");
      setReportingContext("");
    } catch (err) {
      console.error("Error reporting quiz error:", err);
      alert("提交回報時發生錯誤，請稍後再試。");
    }
  };

  const handleNext = async () => {
    if (!quiz) return;
    if (currentQuestionIndex < quiz.questions.length - 1) {
      setCurrentQuestionIndex((prev) => prev + 1);
      return;
    }

    if (grading) return;
    setGrading(true);
    setLoading(true);
    try {
      const gradeRes = await quizAPI.gradeQuiz(quiz.video_id, {
        user_id: userId,
        answers: userAnswers,
      });

      const { total_score, details } = gradeRes.data;
      setBackendScore(total_score);
      setGradeDetails(details);

      if (lastResultId) {
        // 如果已經因為回報而建立了紀錄，則更新它
        await quizAPI.updateResult(lastResultId, {
          score: total_score,
          details_json: JSON.stringify(details),
          title: quiz.video_title // 移除 [回報中] 標籤
        });
      } else {
        const resultRes = await quizAPI.createResult({
          user_id: userId,
          video_id: quiz.video_id,
          score: total_score,
          total_questions: quiz.questions.length,
          details_json: JSON.stringify(details),
        });
        
        if (resultRes.data && resultRes.data.id) {
          setLastResultId(resultRes.data.id);
        }
      }
      
      // 測驗完成，清空該影片草稿
      await quizAPI.deleteDraft(quiz.video_id, userId);
      
      setShowResults(true);
    } catch (err: any) {
      console.error("Error grading quiz:", err);
      setError(`批改失敗: ${err.message}`);
    } finally {
      setGrading(false);
      setLoading(false);
    }
  };

  const executeCode = async () => {
    setCodeLoading(true);
    setCodeOutput("");
    setCodeError("");
    try {
      const userCode = userAnswers[currentQuestionIndex];
      const testBlock = currentQuestion?.test_cases?.join("\n") || "";
      const script = testBlock ? `${userCode}\n\n${testBlock}\nprint("All tests passed")` : userCode;
      const response = await codeAPI.executeCode({ code: script });
      setCodeOutput(response.data.output);
      setCodeError(response.data.error);
    } catch (err: any) {
      console.error("Error executing code:", err);
      setCodeError(err.response?.data?.detail || "執行程式失敗");
    } finally {
      setCodeLoading(false);
    }
  };

  const handleManualSave = async () => {
    if (!quiz) return;
    try {
      const state = {
        quiz,
        userAnswers,
        currentQuestionIndex,
        timestamp: new Date().getTime()
      };
      await quizAPI.upsertDraft({
        user_id: userId,
        video_id: quiz.video_id,
        draft_json: JSON.stringify(state)
      });
      alert("該影片測驗進度已成功儲存至『Unfinished Test』頁面！");
    } catch (err) {
      console.error("Failed to save draft manually", err);
      alert("儲存失敗，請稍後再試。");
    }
  };

  const resetQuiz = async () => {
    if (quiz) {
       await quizAPI.deleteDraft(quiz.video_id, userId).catch(e => console.error(e));
    }
    setQuiz(null);
    setCurrentQuestionIndex(0);
    setUserAnswers([]);
    setShowResults(false);
    setLastResultId(null);
    setCodeOutput("");
    setCodeError("");
  };

  if (showResults && quiz) {
    return (
      <div className="page-shell">
        <section className="page-hero">
          <div>
            <div className="page-eyebrow">Quiz Result</div>
            <h1>{quiz.video_title}</h1>
            <p>這份題目是根據影片內容產生的程式填空題，系統已透過 3 個測試案例進行邏輯驗證。</p>
          </div>
          <div className="page-hero-metric">
            <span>Score</span>
            <strong>{backendScore}%</strong>
            <p>{gradeDetails.filter(d => d.passed).length} / {quiz.questions.length} Passed</p>
          </div>
        </section>

        <section className="panel-card">
          <div className="quiz-review-list">
            {quiz.questions.map((question, index) => {
              const detail = gradeDetails[index];
              return (
                <article key={index} className="quiz-review-card">
                  <div className="quiz-review-status" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', background: detail?.passed ? 'rgba(74, 222, 128, 0.15)' : 'rgba(251, 113, 133, 0.15)', color: detail?.passed ? '#4ade80' : '#fb7185' }}>
                    <span>{detail?.passed ? "Logic Correct" : "Logic Failed"}</span>
                    <button 
                      onClick={() => {
                        setReportingContext(`第 ${index + 1} 題批改問題`);
                        setIsReportModalOpen(true);
                      }}
                      className="chat-message-report-btn"
                      style={{ margin: 0 }}
                    >
                      回報批改問題
                    </button>
                  </div>
                  <h3>{index + 1}. {question.question}</h3>
                  <div style={{ marginTop: "12px" }}>
                    <p><strong>驗證詳情：</strong></p>
                    <ul style={{ listStyle: "none", padding: 0 }}>
                      {detail?.test_results?.map((res: any, i: number) => (
                        <li key={i} style={{ color: res.passed ? "#4ade80" : "#fb7185", fontSize: "0.9em", marginBottom: "4px" }}>
                          Test {i+1}: {res.passed ? "✓ Passed" : `✗ Failed (Expected: ${res.expected}, Actual: ${res.actual})`}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div style={{ marginTop: "12px" }}>
                    <p><strong>你的作答：</strong></p>
                    <pre className="code-snippet">{userAnswers[index] || "未作答"}</pre>
                  </div>
                  <div style={{ marginTop: "12px" }}>
                    <p><strong style={{ color: "#4ade80" }}>參考答案 (填空處)：</strong></p>
                    <code style={{ background: "rgba(0,0,0,0.3)", padding: "4px 8px", borderRadius: "4px", color: "#4ade80", border: "1px solid rgba(74, 222, 128, 0.3)" }}>
                      {question.correct_answer}
                    </code>
                  </div>
                  <div style={{ marginTop: "12px" }}>
                    <p><strong>完整正確程式碼：</strong></p>
                    <pre className="code-snippet" style={{ borderColor: "rgba(74, 222, 128, 0.4)" }}>
                      {(question.starter_code || "").replace("___", question.correct_answer)}
                    </pre>
                  </div>
                  {detail?.diagnostic && (
                    <div style={{ marginTop: "12px", padding: "10px", background: detail.passed ? "rgba(74, 222, 128, 0.1)" : "rgba(251, 113, 133, 0.1)", borderRadius: "8px", borderLeft: `4px solid ${detail.passed ? "#4ade80" : "#fb7185"}` }}>
                      <strong>{detail.passed ? "通過解析：" : "錯誤診斷："}</strong>
                      <p style={{ margin: "5px 0 0", color: detail.passed ? "#86efac" : "#fca5a5" }}>{detail.diagnostic}</p>
                    </div>
                  )}
                  {question.explanation && detail?.passed && (
                    <p style={{ marginTop: "12px" }}><strong>原理補充：</strong>{question.explanation}</p>
                  )}
                </article>
              );
            })}
          </div>
          <div className="quiz-nav-row">
            <button onClick={() => void resetQuiz()} className="page-primary-button">回到影片列表</button>
          </div>
        </section>
        <ReportModal 
          isOpen={isReportModalOpen}
          onClose={() => setIsReportModalOpen(false)}
          onSubmit={handleReportQuizError}
          title="回報批改問題"
          subtitle="如果您發現系統批改有誤、診斷訊息不正確，請告訴我們。"
        />
      </div>
    );
  }

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Video Quiz</div>
          <h1>影片程式填空題</h1>
          <p>系統會依照影片逐字稿與摘要，生成 Python 程式填空題。</p>
        </div>
        <div className="page-hero-metric">
          <span>Sources</span>
          <strong>{videos.length}</strong>
          <p>{quiz?.quiz_type || "waiting"}</p>
        </div>
      </section>

      {error && <div className="page-error">{error}</div>}
      {outlineWarning && <div className="page-error">{outlineWarning}</div>}
      {loading && <div className="page-loading">正在處理測驗數據...</div>}

      <section className="video-library-grid">
        {videos.map((video) => {
          const currentCount = quizCounts[video.id] || 5;
          const updateCount = (val: number) => setQuizCounts(prev => ({ ...prev, [video.id]: val }));
          return (
            <article key={video.id} className="video-library-card">
              <div className="video-library-top">
                <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}>
                  <div className="video-library-badge">Quiz Source</div>
                </div>
                <h3 className="video-library-title">{video.title || "Untitled Video"}</h3>
              </div>
              <div className="quiz-settings-container">
                <label className="quiz-settings-label">題目數量<br/>(上限 10 題)</label>
                <div className="quiz-stepper">
                  <button className="quiz-stepper-btn" onClick={() => updateCount(Math.max(1, currentCount - 1))}>-</button>
                  <div className="quiz-stepper-value">{currentCount}</div>
                  <button className="quiz-stepper-btn" onClick={() => updateCount(Math.min(10, currentCount + 1))}>+</button>
                </div>
              </div>
              <div className="video-library-actions">
                <button onClick={() => void handleGenerateQuiz(video.id)} disabled={loading || !video.outline} className="page-primary-button">
                  {quiz && quiz.video_id === video.id ? "Regenerate" : "Generate"}
                </button>
              </div>
            </article>
          );
        })}
      </section>

      {quiz && currentQuestion && (
        <section className="panel-card">
          {quiz.consumed_points !== undefined && (
            <div className="quiz-score-band" style={{ marginBottom: '20px', backgroundColor: 'rgba(56, 189, 248, 0.1)', borderColor: 'rgba(56, 189, 248, 0.3)' }}>
              <p style={{ color: '#fb7185' }}>本次生成扣除點數：<strong>{quiz.consumed_points}</strong> 點</p>
            </div>
          )}
          <div className="quiz-question-card">
            <div className="quiz-question-number" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <span>Question {currentQuestionIndex + 1} / {quiz.questions.length}</span>
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
          <div style={{ marginTop: "20px" }}>
            <p className="page-eyebrow">Python Editor (填入 ___ 處內容)</p>
            <div style={{ height: "400px", border: "1px solid rgba(43, 193, 241, 0.3)", borderRadius: "12px", overflow: "hidden", marginBottom: "12px" }}>
              <Editor height="100%" language="python" value={userAnswers[currentQuestionIndex]} onChange={(value) => handleAnswerChange(value || "")} theme="vs-dark" options={{ automaticLayout: true, fontSize: 14 }} />
            </div>
            {(codeOutput || codeError) && (
              <div style={{ marginTop: "15px", padding: "12px", background: "#08111f", borderRadius: "10px", border: "1px solid rgba(148, 163, 184, 0.2)" }}>
                <p className="page-eyebrow" style={{ marginBottom: "8px" }}>Test Result:</p>
                {codeOutput && <pre style={{ margin: 0, color: "#4ade80", fontSize: "13px", whiteSpace: "pre-wrap" }}>{codeOutput}</pre>}
                {codeError && <pre style={{ margin: codeOutput ? "10px 0 0" : 0, color: "#fb7185", fontSize: "13px", whiteSpace: "pre-wrap" }}>{codeError}</pre>}
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: "12px", marginTop: "20px", justifyContent: "flex-end" }}>
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
        subtitle="如果您發現 AI 生成的題目有亂碼、邏輯錯誤或答案不正確，請告訴我們。"
      />
    </div>
  );
};

export default Quiz;
