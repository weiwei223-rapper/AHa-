import "./PageIndex.css";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { codeAPI, quizAPI, videoAPI } from "../api";

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

type QuizData = {
  video_id: number;
  video_title: string;
  quiz_type?: string;
  questions: QuizQuestion[];
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

  const [codeOutput, setCodeOutput] = useState("");
  const [codeError, setCodeError] = useState("");
  const [codeLoading, setCodeLoading] = useState(false);

  useEffect(() => {
    void fetchVideos();
  }, []);

  useEffect(() => {
    if (!quiz) {
      return;
    }
    setCodeOutput("");
    setCodeError("");
  }, [quiz, currentQuestionIndex]);

  useEffect(() => {
    if (!preferredVideoId || videos.length === 0) {
      return;
    }
    const target = videos.find((video) => video.id === preferredVideoId);
    if (target && !target.outline) {
      setOutlineWarning("Outline is not available for this video yet. Please generate an outline first.");
    } else {
      setOutlineWarning("");
    }
  }, [preferredVideoId, videos]);

  const currentQuestion = quiz?.questions[currentQuestionIndex] ?? null;

  const score = useMemo(() => {
    if (!quiz) {
      return 0;
    }
    return userAnswers.reduce((total, answer, index) => {
      const correct = quiz.questions[index].correct_answer.trim();
      // If the answer is the full code, we should check if it contains the correct_answer in place of ___
      // But for simplicity, we'll check if the answer (which was pre-filled with starter_code) now contains the correct_answer
      return answer.trim().includes(correct) ? total + 1 : total;
    }, 0);
  }, [quiz, userAnswers]);

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
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");
    setOutlineWarning("");
    try {
      const response = await videoAPI.generateQuiz(videoId, userId, video.outline);
      const nextQuiz = response.data as QuizData;
      setQuiz(nextQuiz);
      setCurrentQuestionIndex(0);
      setUserAnswers(nextQuiz.questions.map(q => q.starter_code || ""));
      setShowResults(false);
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

  const handleNext = async () => {
    if (!quiz) {
      return;
    }
    if (currentQuestionIndex < quiz.questions.length - 1) {
      setCurrentQuestionIndex((prev) => prev + 1);
      return;
    }

    setGrading(true);
    setLoading(true);
    try {
      // 呼叫後端進行邏輯批改
      const gradeRes = await quizAPI.gradeQuiz(quiz.video_id, {
        user_id: userId,
        answers: userAnswers,
      });

      const { total_score, details } = gradeRes.data;
      setBackendScore(total_score);
      setGradeDetails(details);

      await quizAPI.createResult({
        user_id: userId,
        video_id: quiz.video_id,
        score: total_score,
        total_questions: quiz.questions.length,
      });
      setShowResults(true);
    } catch (err) {
      console.error("Error grading quiz:", err);
      setError("批改過程中發生錯誤，請稍後再試。");
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

  const resetQuiz = () => {
    setQuiz(null);
    setCurrentQuestionIndex(0);
    setUserAnswers([]);
    setShowResults(false);
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
            <p>
              {gradeDetails.filter(d => d.passed).length} / {quiz.questions.length} Passed
            </p>
          </div>
        </section>

        <section className="panel-card">
          <div className="quiz-review-list">
            {quiz.questions.map((question, index) => {
              const detail = gradeDetails[index];
              return (
                <article key={index} className="quiz-review-card">
                  <div className={`quiz-review-status ${detail?.passed ? "correct" : "review"}`}>
                    {detail?.passed ? "Logic Correct" : "Logic Failed"}
                  </div>
                  <h3>
                    {index + 1}. {question.question}
                  </h3>
                  {question.reference_concept && (
                    <p style={{ color: "#38bdf8", fontWeight: "bold", margin: "8px 0" }}>
                      {question.reference_concept}
                    </p>
                  )}

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

                  {question.explanation && (
                    <p style={{ marginTop: "12px" }}>
                      <strong>解析：</strong>
                      {question.explanation}
                    </p>
                  )}
                </article>
              );
            })}
          </div>

          <div className="quiz-nav-row">
            <button onClick={resetQuiz} className="page-primary-button">
              回到影片列表
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Video Quiz</div>
          <h1>影片程式填空題</h1>
          <p>系統會依照影片逐字稿與摘要，並參考 LeetCode 題庫，生成 Python 程式填空題。</p>
        </div>
        <div className="page-hero-metric">
          <span>Sources</span>
          <strong>{videos.length}</strong>
          <p>{quiz?.quiz_type || "waiting"}</p>
        </div>
      </section>

      {error && <div className="page-error">{error}</div>}
      {outlineWarning && <div className="page-error">{outlineWarning}</div>}
      {loading && <div className="page-loading">正在分析影片並產生填空題...</div>}

      <section className="video-library-grid">
        {videos.map((video) => (
          <article key={video.id} className="video-library-card">
            <div className="video-library-top">
              <div style={{ display: "flex", gap: "8px", marginBottom: "8px", flexWrap: "wrap" }}>
                <div className="video-library-badge">Quiz Source</div>
                {video.outline ? (
                  <div style={{ display: "inline-flex", width: "fit-content", borderRadius: "999px", padding: "6px 10px", background: "rgba(34, 197, 94, 0.15)", color: "#86efac", fontSize: "12px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                    ✓ Outline
                  </div>
                ) : (
                  <div style={{ display: "inline-flex", width: "fit-content", borderRadius: "999px", padding: "6px 10px", background: "rgba(248, 113, 113, 0.15)", color: "#fecaca", fontSize: "12px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
                    ✗ No Outline
                  </div>
                )}
              </div>
              <h3>{video.title || "Untitled Video"}</h3>
              <p className="video-library-description">
                Added at {new Date(video.created_at).toLocaleString("zh-TW")}
              </p>
            </div>
            <div className="video-library-actions">
              <button
                onClick={() => void handleGenerateQuiz(video.id)}
                disabled={loading || !video.outline}
                className="page-primary-button"
                title={!video.outline ? "Outline is not available for this video. Please generate an outline first." : ""}
              >
                Generate Quiz
              </button>
            </div>
          </article>
        ))}

        {videos.length === 0 && (
          <div className="empty-state-card">
            <h3>目前沒有影片</h3>
            <p>先到 Learning Material 新增影片，才能產生和影片內容相關的填空題。</p>
          </div>
        )}
      </section>

      {quiz && currentQuestion && (
        <section className="panel-card">
          <div className="quiz-question-card">
            <div className="quiz-question-number">
              Question {currentQuestionIndex + 1} / {quiz.questions.length}
            </div>
            <h2>{currentQuestion.question}</h2>

            {currentQuestion.reference_concept && (
              <p style={{ color: "#38bdf8", fontSize: "1.1em", fontWeight: "bold", marginTop: "10px" }}>
                {currentQuestion.reference_concept}
              </p>
            )}
          </div>

          <div style={{ marginTop: "20px" }}>
            <p className="page-eyebrow">Python Editor (填入 ___ 處內容)</p>
            <style>{`
              /* NUCLEAR FIX for Monaco Suggestion Widget */
              .monaco-editor .suggest-widget,
              .monaco-editor .suggest-widget *,
              .monaco-editor .suggest-widget .monaco-list-row,
              .monaco-editor .suggest-widget .monaco-list-row * {
                color: #ffffff !important;
                background-color: #1e1e1e !important;
              }
              .monaco-editor .suggest-widget .monaco-list-row.focused,
              .monaco-editor .suggest-widget .monaco-list-row.focused * {
                background-color: #2b415e !important;
                color: #ffffff !important;
              }
            `}</style>
            <div style={{ height: "400px", border: "1px solid rgba(43, 193, 241, 0.3)", borderRadius: "12px", overflow: "hidden", marginBottom: "12px" }}>
              <Editor
                height="100%"
                language="python"
                value={userAnswers[currentQuestionIndex]}
                onChange={(value) => handleAnswerChange(value || "")}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: "on",
                  roundedSelection: false,
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
              />
            </div>
          </div>

          {(currentQuestion.test_cases && currentQuestion.test_cases.length > 0) && (
            <div>
              <p className="page-eyebrow">Test Cases</p>
              <article className="quiz-review-card">
                <pre className="code-snippet">
                  {currentQuestion.test_cases.join("\n")}
                </pre>
              </article>
            </div>
          )}

          {(codeOutput || codeError) && (
            <div>
              {codeOutput && (
                <div>
                  <p className="page-eyebrow">Output</p>
                  <article className="quiz-review-card">
                    <pre className="code-snippet">{codeOutput}</pre>
                  </article>
                </div>
              )}
              {codeError && (
                <div>
                  <p className="page-eyebrow">Error</p>
                  <article className="quiz-review-card">
                    <pre className="code-snippet">{codeError}</pre>
                  </article>
                </div>
              )}
            </div>
          )}

          <div style={{ display: "flex", gap: "12px", marginTop: "20px", justifyContent: "flex-end" }} className="unified-control-bar">
            <button
              onClick={handlePrevious}
              disabled={currentQuestionIndex === 0}
              className="page-secondary-button"
            >
              Previous
            </button>
            <button
              onClick={() => void handleNext()}
              className="page-primary-button"
            >
              {currentQuestionIndex === quiz.questions.length - 1 ? "Finish" : "Next"}
            </button>
            <button
              onClick={() => void executeCode()}
              disabled={codeLoading}
              className="page-primary-button"
            >
              {codeLoading ? "Testing..." : "Test"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
};

export default Quiz;
