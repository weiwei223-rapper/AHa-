import "./PageIndex.css";
import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { API_BASE_URL } from "../api";

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
};

type Quiz = {
  video_id: number;
  video_title: string;
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
  const videoIdFromUrl = searchParams.get('videoId');
  
  const [videos, setVideos] = useState<Video[]>([]);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState<number[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resultSaved, setResultSaved] = useState(false);

  // 載入影片列表
  useEffect(() => {
    fetchVideos();
  }, []);

  // 如果 URL 中有 videoId，自動生成該影片的測驗
  useEffect(() => {
    if (videoIdFromUrl && videos.length > 0) {
      const video = videos.find(v => v.id === parseInt(videoIdFromUrl));
      if (video) {
        generateQuiz(video);
      }
    }
  }, [videoIdFromUrl, videos]);

  const fetchVideos = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/videos`);
      if (!res.ok) throw new Error("無法取得影片列表");
      const data: Video[] = await res.json();
      setVideos(data);
    } catch (err: any) {
      console.error(err);
      setError("載入影片失敗");
    }
  };

  const generateQuiz = async (video: Video) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/videos/${video.id}/quiz`);
      if (!res.ok) throw new Error("無法產生測驗題目");
      const data: Quiz = await res.json();
      setQuiz(data);
      setCurrentQuestionIndex(0);
      setSelectedAnswers(new Array(data.questions.length).fill(-1));
      setShowResults(false);
      setResultSaved(false);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "產生測驗失敗");
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSelect = (questionIndex: number, answerIndex: number) => {
    const newAnswers = [...selectedAnswers];
    newAnswers[questionIndex] = answerIndex;
    setSelectedAnswers(newAnswers);
  };

  const saveQuizResult = async (score: number, totalQuestions: number) => {
    if (!quiz) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/quiz-results`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: quiz.video_id,
          score: score,
          total_questions: totalQuestions
        }),
      });

      if (!res.ok) {
        console.error("Failed to save quiz result");
      }
    } catch (err) {
      console.error("Error saving quiz result:", err);
    }
  };

  const handleNext = () => {
    if (currentQuestionIndex < (quiz?.questions.length || 0) - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } else {
      // Quiz completed - save result
      const score = calculateScore();
      if (quiz) {
        saveQuizResult(score, quiz.questions.length);
      }
      setShowResults(true);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  const calculateScore = () => {
    if (!quiz) return 0;
    let correct = 0;
    selectedAnswers.forEach((answer, index) => {
      if (answer === quiz.questions[index].correct_answer) {
        correct++;
      }
    });
    return correct;
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

  if (showResults && quiz) {
    const score = calculateScore();
    const totalQuestions = quiz.questions.length;
    const percentage = Math.round((score / totalQuestions) * 100);

    return (
      <div className="main">
        <div className="quiz-container">
          <h1>測驗結果</h1>
          <h2>影片：{quiz.video_title}</h2>
          <div className="score-display">
            <h3>得分：{score}/{totalQuestions} ({percentage}%)</h3>
            {percentage >= 80 && <p>🎉 優秀！</p>}
            {percentage >= 60 && percentage < 80 && <p>👍 不錯！</p>}
            {percentage < 60 && <p>💪 繼續努力！</p>}
          </div>

          <div className="results-review">
            <h3>答案回顧：</h3>
            {quiz.questions.map((question, index) => (
              <div key={index} className="question-review">
                <p><strong>問題 {index + 1}：</strong> {question.question}</p>
                <p>你的答案：{selectedAnswers[index] !== undefined && selectedAnswers[index] !== -1 ? question.options[selectedAnswers[index]] : "未作答"}</p>
                <p>正確答案：{question.options[question.correct_answer]}</p>
                <p className={selectedAnswers[index] === question.correct_answer ? "correct" : "incorrect"}>
                  {selectedAnswers[index] === question.correct_answer ? "✓ 正確" : selectedAnswers[index] !== undefined && selectedAnswers[index] !== -1 ? "✗ 錯誤" : "未作答"}
                </p>
              </div>
            ))}
          </div>

          <button onClick={resetQuiz} className="reset-btn">重新選擇影片</button>
        </div>
      </div>
    );
  }

  if (quiz && !showResults) {
    const currentQuestion = quiz.questions[currentQuestionIndex];

    return (
      <div className="main">
        <div className="quiz-container">
          <h1>影片測驗</h1>
          <h2>{quiz.video_title}</h2>
          <div className="progress">
            問題 {currentQuestionIndex + 1} / {quiz.questions.length}
          </div>

          <div className="question">
            <h3>{currentQuestion.question}</h3>
            <div className="options">
              {currentQuestion.options.map((option, index) => (
                <label key={index} className="option">
                  <input
                    type="radio"
                    name={`question-${currentQuestionIndex}`}
                    value={index}
                    checked={selectedAnswers[currentQuestionIndex] === index}
                    onChange={() => handleAnswerSelect(currentQuestionIndex, index)}
                  />
                  {option}
                </label>
              ))}
            </div>
          </div>

          <div className="navigation">
            <button
              onClick={handlePrevious}
              disabled={currentQuestionIndex === 0}
              className="nav-btn"
            >
              上一題
            </button>
            <button
              onClick={handleNext}
              disabled={selectedAnswers[currentQuestionIndex] === -1}
              className="nav-btn"
            >
              {currentQuestionIndex === quiz.questions.length - 1 ? "完成測驗" : "下一題"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="main">
      <div className="quiz-container">
        <h1>影片測驗</h1>
        <p>選擇一個影片來開始測驗：</p>

        {error && <div className="error">{error}</div>}

        {loading && <div className="loading">載入中...</div>}

        <div className="video-list">
          {videos.length === 0 ? (
            <p>目前沒有影片，請先上傳影片。</p>
          ) : (
            videos.map((video) => (
              <div key={video.id} className="video-item">
                <h3>{video.title || "未命名影片"}</h3>
                <p>上傳時間：{new Date(video.created_at).toLocaleString()}</p>
                <button
                  onClick={() => generateQuiz(video)}
                  disabled={loading}
                  className="quiz-btn"
                >
                  開始測驗
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default Quiz;
