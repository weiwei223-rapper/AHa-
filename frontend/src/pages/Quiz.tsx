import "./PageIndex.css";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { API_BASE_URL, codeAPI, getErrorMessage, parseResponseBody } from "../api";
import Editor from "@monaco-editor/react";

type Video = {
  id: number;
  video_link: string;
  title?: string | null;
  created_at: string;
};

type QuizQuestion = {
  question: string;
  options: string[];
  correct_answer: number;
  explanation?: string | null;
};

type QuizData = {
  video_id: number;
  video_title: string;
  quiz_type?: string;
  questions: QuizQuestion[];
};

type QuizResult = {
  videoId: number;
  score: number;
  totalQuestions: number;
  percentage: number;
  completedAt: string;
};

const QUIZ_RESULTS_KEY = "quizResults";

const Quiz = () => {
  const [searchParams] = useSearchParams();
  const videoIdFromUrl = searchParams.get("videoId");

  const [videos, setVideos] = useState<Video[]>([]);
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<number[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resultSaved, setResultSaved] = useState(false);

  // Code editor state
  const [code, setCode] = useState("# Write your Python code here\nprint('Hello, World!')");
  const [codeOutput, setCodeOutput] = useState("");
  const [codeError, setCodeError] = useState("");
  const [codeLoading, setCodeLoading] = useState(false);

  useEffect(() => {
    void fetchVideos();
  }, []);

  useEffect(() => {
    if (videoIdFromUrl && videos.length > 0) {
      const video = videos.find((item) => item.id === Number(videoIdFromUrl));
      if (video) {
        void generateQuiz(video);
      }
    }
  }, [videoIdFromUrl, videos]);

  const fetchVideos = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/videos`);
      if (!res.ok) {
        throw new Error(await getErrorMessage(res, "無法載入影片清單"));
      }

      const data = await parseResponseBody<Video[]>(res);
      if (!data) {
        throw new Error("無法載入影片清單：伺服器未回傳有效資料");
      }
      setVideos(data);
    } catch (err) {
      console.error(err);
      setError("載入影片失敗。");
    }
  };

  const generateQuiz = async (video: Video) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/videos/${video.id}/quiz`);
      if (!res.ok) {
        throw new Error(await getErrorMessage(res, "AI 測驗生成失敗"));
      }

      const data = await parseResponseBody<QuizData>(res);
      if (!data) {
        throw new Error("AI 測驗生成失敗：伺服器未回傳有效資料");
      }
      setQuiz(data);
      setCurrentQuestionIndex(0);
      setSelectedAnswers(new Array(data.questions.length).fill(-1));
      setShowResults(false);
      setResultSaved(false);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "無法生成測驗");
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSelect = (questionIndex: number, answerIndex: number) => {
    const newAnswers = [...selectedAnswers];
    newAnswers[questionIndex] = answerIndex;
    setSelectedAnswers(newAnswers);
  };

  const calculateScore = () => {
    if (!quiz) {
      return 0;
    }

    return selectedAnswers.reduce((correct, answer, index) => {
      return answer === quiz.questions[index].correct_answer ? correct + 1 : correct;
    }, 0);
  };

  const saveQuizResult = async (score: number, totalQuestions: number) => {
    if (!quiz) {
      return;
    }

    try {
      await fetch(`${API_BASE_URL}/api/quiz-results`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: quiz.video_id,
          score,
          total_questions: totalQuestions,
        }),
      });
    } catch (err) {
      console.error("Error saving quiz result:", err);
    }
  };

  const handleNext = async () => {
    if (!quiz) {
      return;
    }

    if (currentQuestionIndex < quiz.questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      return;
    }

    const score = calculateScore();
    await saveQuizResult(score, quiz.questions.length);
    setShowResults(true);
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  useEffect(() => {
    if (!showResults || !quiz || resultSaved) {
      return;
    }

    const score = calculateScore();
    const totalQuestions = quiz.questions.length;
    const percentage = Math.round((score / totalQuestions) * 100);
    const nextResult: QuizResult = {
      videoId: quiz.video_id,
      score,
      totalQuestions,
      percentage,
      completedAt: new Date().toISOString(),
    };

    try {
      const raw = localStorage.getItem(QUIZ_RESULTS_KEY);
      const existingResults: QuizResult[] = raw ? JSON.parse(raw) : [];
      const safeResults = Array.isArray(existingResults) ? existingResults : [];
      localStorage.setItem(QUIZ_RESULTS_KEY, JSON.stringify([nextResult, ...safeResults]));
      setResultSaved(true);
    } catch (storageError) {
      console.error("Failed to save quiz result:", storageError);
    }
  }, [showResults, quiz, resultSaved, selectedAnswers]);

  const resetQuiz = () => {
    setQuiz(null);
    setCurrentQuestionIndex(0);
    setSelectedAnswers([]);
    setShowResults(false);
    setResultSaved(false);
  };

  const executeCode = async () => {
    setCodeLoading(true);
    setCodeOutput("");
    setCodeError("");

    try {
      const response = await codeAPI.executeCode({ code });
      setCodeOutput(response.data.output);
      setCodeError(response.data.error);
    } catch (error: any) {
      console.error('Error executing code:', error);
      setCodeError(error.response?.data?.detail || 'Failed to execute code');
    } finally {
      setCodeLoading(false);
    }
  };

  if (showResults && quiz) {
    const score = calculateScore();
    const totalQuestions = quiz.questions.length;
    const percentage = Math.round((score / totalQuestions) * 100);

    return (
      <div className="page-shell">
        <section className="page-hero">
          <div>
            <div className="page-eyebrow">AI Coding Quiz</div>
            <h1>測驗結果</h1>
            <p>這份題目是 AI 根據完整影片內容優先生成的程式理解題。</p>
          </div>
          <div className="page-hero-metric">
            <span>Score</span>
            <strong>{percentage}%</strong>
            <p>{score} / {totalQuestions}</p>
          </div>
        </section>

        <section className="panel-card">
          <div className="quiz-score-band">
            <h2>{quiz.video_title}</h2>
            <p>
              {percentage >= 80 && "表現很好，對影片中的程式概念已經有不錯掌握。"}
              {percentage >= 60 && percentage < 80 && "基礎理解到位，但還有幾題需要補強推理細節。"}
              {percentage < 60 && "建議回看影片中的程式流程與除錯段落，再做一次測驗。"}
            </p>
          </div>

          <div className="quiz-review-list">
            {quiz.questions.map((question, index) => {
              const selectedIndex = selectedAnswers[index];
              const isCorrect = selectedIndex === question.correct_answer;
              return (
                <article key={index} className="quiz-review-card">
                  <div className="quiz-review-status">{isCorrect ? "Correct" : "Review"}</div>
                  <h3>{index + 1}. {question.question}</h3>
                  <p>你的答案：{selectedIndex >= 0 ? question.options[selectedIndex] : "未作答"}</p>
                  <p>正確答案：{question.options[question.correct_answer]}</p>
                  {question.explanation && <p>解析：{question.explanation}</p>}
                </article>
              );
            })}
          </div>

          <div className="quiz-nav-row">
            <button onClick={resetQuiz} className="page-primary-button">重新選擇影片</button>
          </div>
        </section>
      </div>
    );
  }

  if (quiz && !showResults) {
    const currentQuestion = quiz.questions[currentQuestionIndex];

    return (
      <div className="page-shell">
        <section className="page-hero">
          <div>
            <div className="page-eyebrow">AI Coding Quiz</div>
            <h1>{quiz.video_title}</h1>
            <p>這組題目會優先檢查你是否理解影片中的程式流程、觀念與除錯判斷。</p>
          </div>
          <div className="page-hero-metric">
            <span>Progress</span>
            <strong>{currentQuestionIndex + 1}/{quiz.questions.length}</strong>
            <p>{quiz.quiz_type || "ai-coding"}</p>
          </div>
        </section>

        <section className="panel-card">
          <div className="quiz-question-card">
            <div className="quiz-question-number">Question {currentQuestionIndex + 1}</div>
            <h2>{currentQuestion.question}</h2>
            <div className="quiz-options-grid">
              {currentQuestion.options.map((option, index) => (
                <label
                  key={index}
                  className={`quiz-option-tile code-option ${selectedAnswers[currentQuestionIndex] === index ? "selected" : ""}`}
                >
                  <input
                    type="radio"
                    name={`question-${currentQuestionIndex}`}
                    value={index}
                    checked={selectedAnswers[currentQuestionIndex] === index}
                    onChange={() => handleAnswerSelect(currentQuestionIndex, index)}
                  />
                  <pre className="code-snippet">{option}</pre>
                </label>
              ))}
            </div>
          </div>

          <div className="quiz-nav-row">
            <button onClick={handlePrevious} disabled={currentQuestionIndex === 0} className="page-secondary-button">
              Previous
            </button>
            <button
              onClick={() => void handleNext()}
              disabled={selectedAnswers[currentQuestionIndex] === -1}
              className="page-primary-button"
            >
              {currentQuestionIndex === quiz.questions.length - 1 ? "Finish Quiz" : "Next"}
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
          <div className="page-eyebrow">AI Coding Quiz</div>
          <h1>選擇影片並生成測驗</h1>
          <p>AI 會優先根據整支影片的逐字稿與內容脈絡，產生偏程式理解、除錯與實作決策的題目。</p>
        </div>
        <div className="page-hero-metric">
          <span>Quiz Sources</span>
          <strong>{videos.length}</strong>
          <p>支影片可生成新題目</p>
        </div>
      </section>

      {error && <div className="page-error">{error}</div>}
      {loading && <div className="page-loading">AI 正在讀取影片並生成程式題...</div>}

      {/* Code Editor Section - Always visible */}
      <section className="panel-card">
        <h3>程式碼編輯器</h3>
        <p>在這裡寫並執行 Python 程式碼來練習程式設計。</p>
        <div style={{ height: '300px', border: '1px solid #ccc', marginBottom: '10px' }}>
          <Editor
            height="100%"
            language="python"
            value={code}
            onChange={(value) => setCode(value || "")}
            theme="vs-light"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              roundedSelection: false,
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        </div>
        <div className="quiz-nav-row">
          <button onClick={executeCode} disabled={codeLoading} className="page-primary-button">
            {codeLoading ? "執行中..." : "執行程式碼"}
          </button>
        </div>
        {(codeOutput || codeError) && (
          <div style={{ marginTop: '10px' }}>
            <h4>輸出結果：</h4>
            {codeOutput && (
              <pre style={{ backgroundColor: '#f0f0f0', padding: '10px', borderRadius: '4px', marginBottom: '10px', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                {codeOutput}
              </pre>
            )}
            {codeError && (
              <pre style={{ backgroundColor: '#ffe6e6', color: '#d32f2f', padding: '10px', borderRadius: '4px', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                {codeError}
              </pre>
            )}
          </div>
        )}
      </section>

      <section className="video-library-grid">
        {videos.length === 0 ? (
          <div className="empty-state-card">
            <h3>還沒有影片可出題</h3>
            <p>先到 Video 頁面加入影片，Quiz 才能依影片內容生成 AI 程式題。</p>
          </div>
        ) : (
          videos.map((video) => (
            <article key={video.id} className="video-library-card">
              <div className="video-library-top">
                <div className="video-library-badge">Coding Source</div>
                <h3>{video.title || "Untitled Video"}</h3>
                <p className="video-library-description">
                  上傳時間：{new Date(video.created_at).toLocaleString("zh-TW")}
                </p>
              </div>
              <div className="video-library-actions">
                <button onClick={() => void generateQuiz(video)} disabled={loading} className="page-primary-button">
                  Generate AI Coding Quiz
                </button>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
};

export default Quiz;
