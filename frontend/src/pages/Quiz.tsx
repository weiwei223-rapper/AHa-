import "./PageIndex.css";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { codeAPI, quizAPI, videoAPI } from "../api";

type VideoItem = {
  id: number;
  video_link: string;
  title?: string | null;
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

  const [code, setCode] = useState("# Select a quiz to load starter code");
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
    const question = quiz.questions[currentQuestionIndex];
    setCode(question?.starter_code || "# Write your Python solution here");
    setCodeOutput("");
    setCodeError("");
  }, [quiz, currentQuestionIndex]);

  useEffect(() => {
    if (!preferredVideoId || videos.length === 0) {
      return;
    }
    const target = videos.find((video) => video.id === preferredVideoId);
    if (target) {
      void handleGenerateQuiz(target.id);
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
    setLoading(true);
    setError("");
    try {
      const response = await videoAPI.generateQuiz(videoId, userId);
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
      const testBlock = currentQuestion?.test_cases?.join("\n") || "";
      const script = testBlock ? `${code}\n\n${testBlock}\nprint("All tests passed")` : code;
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
    setCode("# Select a quiz to load starter code");
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
      {loading && <div className="page-loading">正在分析影片並產生填空題...</div>}

      <section className="video-library-grid">
        {videos.map((video) => (
          <article key={video.id} className="video-library-card">
            <div className="video-library-top">
              <div className="video-library-badge">Quiz Source</div>
              <h3>{video.title || "Untitled Video"}</h3>
              <p className="video-library-description">
                Added at {new Date(video.created_at).toLocaleString("zh-TW")}
              </p>
            </div>
            <div className="video-library-actions">
              <button
                onClick={() => void handleGenerateQuiz(video.id)}
                disabled={loading}
                className="page-primary-button"
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
        <>
          <section className="panel-card">
            <div className="quiz-question-card">
              <div className="quiz-question-number">
                Question {currentQuestionIndex + 1} / {quiz.questions.length}
              </div>
              <h2>{currentQuestion.question}</h2>

              <div style={{ marginTop: "20px" }}>
                <p className="page-eyebrow">Your Answer</p>
                <textarea
                  className="page-input"
                  style={{ width: "100%", minHeight: "120px", fontFamily: "monospace", padding: "12px" }}
                  placeholder="輸入要填入 ___ 的答案"
                  value={userAnswers[currentQuestionIndex]}
                  onChange={(e) => handleAnswerChange(e.target.value)}
                />
              </div>

              {(currentQuestion.source_time || currentQuestion.source_excerpt) && (
                <div style={{ marginTop: "20px" }}>
                  <p className="page-eyebrow">出題依據</p>
                  <p>{currentQuestion.source_time || "unknown"}</p>
                  {currentQuestion.source_excerpt && <pre className="code-snippet">{currentQuestion.source_excerpt}</pre>}
                </div>
              )}
            </div>

            <div className="quiz-nav-row">
              <button
                onClick={handlePrevious}
                disabled={currentQuestionIndex === 0}
                className="page-secondary-button"
              >
                Previous
              </button>
              <button onClick={() => void handleNext()} className="page-primary-button">
                {currentQuestionIndex === quiz.questions.length - 1 ? "Finish Quiz" : "Next"}
              </button>
            </div>
          </section>

          <section className="panel-card">
            <div className="panel-header">
              <div>
                <div className="page-eyebrow">Editor</div>
                <h2>Starter Code 與測試案例</h2>
              </div>
            </div>

            <div style={{ height: "320px", border: "1px solid #d9d9d9", marginBottom: "12px" }}>
              <Editor
                height="100%"
                language="python"
                value={code}
                onChange={(value) => setCode(value || "")}
                theme="vs-light"
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

            <div className="quiz-review-list">
              <article className="quiz-review-card">
                <div className="quiz-review-status">Test Cases</div>
                <pre className="code-snippet">
                  {(currentQuestion.test_cases || []).join("\n") || "目前沒有測試案例"}
                </pre>
              </article>
            </div>

            <div className="quiz-nav-row">
              <button onClick={() => void executeCode()} disabled={codeLoading} className="page-primary-button">
                {codeLoading ? "執行中..." : "Run Code"}
              </button>
            </div>

            {(codeOutput || codeError) && (
              <div className="quiz-review-list">
                {codeOutput && (
                  <article className="quiz-review-card">
                    <div className="quiz-review-status">Output</div>
                    <pre className="code-snippet">{codeOutput}</pre>
                  </article>
                )}
                {codeError && (
                  <article className="quiz-review-card">
                    <div className="quiz-review-status">Error</div>
                    <pre className="code-snippet">{codeError}</pre>
                  </article>
                )}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
};

export default Quiz;
