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
      return answer.trim() === correct ? total + 1 : total;
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
      setUserAnswers(new Array(nextQuiz.questions.length).fill(""));
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

  const handleNext = async () => {
    if (!quiz) {
      return;
    }
    if (currentQuestionIndex < quiz.questions.length - 1) {
      setCurrentQuestionIndex((prev) => prev + 1);
      return;
    }
    try {
      await quizAPI.createResult({
        user_id: userId,
        video_id: quiz.video_id,
        score,
        total_questions: quiz.questions.length,
      });
    } catch (err) {
      console.error("Error saving quiz result:", err);
    }
    setShowResults(true);
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
    const percentage = Math.round((score / quiz.questions.length) * 100);
    return (
      <div className="page-shell">
        <section className="page-hero">
          <div>
            <div className="page-eyebrow">Quiz Result</div>
            <h1>{quiz.video_title}</h1>
            <p>這份題目是根據影片內容產生的程式填空題，可以逐題檢查答案與來源。</p>
          </div>
          <div className="page-hero-metric">
            <span>Score</span>
            <strong>{percentage}%</strong>
            <p>
              {score} / {quiz.questions.length}
            </p>
          </div>
        </section>

        <section className="panel-card">
          <div className="quiz-review-list">
            {quiz.questions.map((question, index) => (
              <article key={index} className="quiz-review-card">
                <div className="quiz-review-status">
                  {userAnswers[index].trim() === question.correct_answer.trim() ? "Correct" : "Review"}
                </div>
                <h3>
                  {index + 1}. {question.question}
                </h3>
                {question.starter_code && <pre className="code-snippet">{question.starter_code}</pre>}
                <div style={{ marginTop: "12px" }}>
                  <p>
                    <strong>你的答案：</strong>
                  </p>
                  <pre className="code-snippet">{userAnswers[index] || "未作答"}</pre>
                </div>
                <div style={{ marginTop: "12px" }}>
                  <p>
                    <strong>正確答案：</strong>
                  </p>
                  <pre className="code-snippet">{question.correct_answer}</pre>
                </div>
                {question.explanation && (
                  <p style={{ marginTop: "12px" }}>
                    <strong>解析：</strong>
                    {question.explanation}
                  </p>
                )}
                {(question.source_time || question.source_excerpt) && (
                  <div style={{ marginTop: "12px" }}>
                    <p>
                      <strong>出題依據：</strong>
                      {question.source_time || "unknown"}
                    </p>
                    {question.source_excerpt && <pre className="code-snippet">{question.source_excerpt}</pre>}
                  </div>
                )}
              </article>
            ))}
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
          <p>系統會依照影片逐字稿與摘要，生成 Python 程式填空題與對應測試案例。</p>
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

            {(currentQuestion.source_time || currentQuestion.source_excerpt) && (
              <div style={{ marginTop: "20px" }}>
                <p className="page-eyebrow">出題依據</p>
                <p>{currentQuestion.source_time || "unknown"}</p>
                {currentQuestion.source_excerpt && <pre className="code-snippet">{currentQuestion.source_excerpt}</pre>}
              </div>
            )}
          </div>

          {currentQuestion.starter_code && (
            <div>
              <p className="page-eyebrow">Starter Code</p>
              <pre className="code-snippet">{currentQuestion.starter_code}</pre>
            </div>
          )}

          <div style={{ marginTop: "20px" }}>
            <p className="page-eyebrow">Your Solution</p>
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
            <button
              onClick={() => {
                console.log("Submit clicked");
              }}
              className="page-primary-button"
            >
              Submit
            </button>
          </div>
        </section>
      )}
    </div>
  );
};

export default Quiz;
