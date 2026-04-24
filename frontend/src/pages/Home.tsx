import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE_URL, parseResponseBody, userAPI } from "../api";
import "./PageIndex.css";

type UserStatusProps = {
  name: string;
};

type Video = {
  id: number;
};

type QuizResult = {
  videoId: number;
  score: number;
  totalQuestions: number;
};

type HomeStats = {
  videoCount: number;
  points: number;
  completedQuizCount: number;
  averageAccuracy: number;
};

const QUIZ_RESULTS_KEY = "quizResults";

const Home = ({ name }: UserStatusProps) => {
  const [stats, setStats] = useState<HomeStats>({
    videoCount: 0,
    points: 0,
    completedQuizCount: 0,
    averageAccuracy: 0,
  });

  useEffect(() => {
    void loadStats();
  }, []);

  const loadStats = async () => {
    const [videoCount, points, quizResults] = await Promise.all([
      getVideoCount(),
      getPoints(),
      Promise.resolve(getQuizResults()),
    ]);

    const totalCorrect = quizResults.reduce((sum, item) => sum + item.score, 0);
    const totalQuestions = quizResults.reduce((sum, item) => sum + item.totalQuestions, 0);

    setStats({
      videoCount,
      points,
      completedQuizCount: quizResults.length,
      averageAccuracy: totalQuestions > 0 ? Math.round((totalCorrect / totalQuestions) * 100) : 0,
    });
  };

  const getVideoCount = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/videos`);
      if (!response.ok) {
        return 0;
      }

      const videos = await parseResponseBody<Video[]>(response);
      if (!videos) {
        return 0;
      }
      return videos.length;
    } catch (error) {
      console.error("Failed to load videos:", error);
      return 0;
    }
  };

  const getPoints = async () => {
    const userId = localStorage.getItem("userId");
    if (!userId) {
      return readStoredUserPoints();
    }

    try {
      const response = await userAPI.getUser(Number(userId));
      localStorage.setItem("userData", JSON.stringify(response.data));
      return response.data.points ?? 0;
    } catch (error) {
      console.error("Failed to load user points:", error);
      return readStoredUserPoints();
    }
  };

  const readStoredUserPoints = () => {
    try {
      const raw = localStorage.getItem("userData");
      if (!raw) {
        return 0;
      }

      const userData = JSON.parse(raw);
      return userData?.points ?? 0;
    } catch (error) {
      console.error("Failed to read cached user data:", error);
      return 0;
    }
  };

  const getQuizResults = (): QuizResult[] => {
    try {
      const raw = localStorage.getItem(QUIZ_RESULTS_KEY);
      if (!raw) {
        return [];
      }

      const data = JSON.parse(raw);
      return Array.isArray(data) ? data : [];
    } catch (error) {
      console.error("Failed to read quiz results:", error);
      return [];
    }
  };

  const cards = [
    {
      label: "Uploaded Videos",
      value: stats.videoCount.toString(),
      hint: "管理已上傳的學習影片與教材來源",
      to: "/Video",
    },
    {
      label: "Available Points",
      value: stats.points.toString(),
      hint: "查看帳戶點數與充值紀錄",
      to: "/Profile",
    },
    {
      label: "Quiz Completed",
      value: stats.completedQuizCount.toString(),
      hint: "回看完成的 AI 程式測驗次數",
      to: "/Quiz",
    },
    {
      label: "Average Accuracy",
      value: `${stats.averageAccuracy}%`,
      hint: "追蹤最近作答的正確率變化",
      to: "/Quiz",
    },
  ];

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero">
        <div className="dashboard-hero-copy">
          <div className="page-eyebrow">AHa Learning Workspace</div>
          <h1>Welcome back, {name}</h1>
          <p>
            從影片、聊天到 AI 程式測驗，這裡是你目前的學習總覽。先看進度，再決定下一步要補哪一段。
          </p>
        </div>
        <div className="dashboard-highlight-card">
          <span>Study Snapshot</span>
          <strong>{stats.videoCount}</strong>
          <p>支影片已可用來生成聊天上下文與 AI 程式題。</p>
        </div>
      </section>

      <section className="dashboard-grid">
        {cards.map((card) => (
          <Link key={card.label} to={card.to} className="dashboard-stat-card">
            <span className="dashboard-stat-label">{card.label}</span>
            <strong className="dashboard-stat-value">{card.value}</strong>
          </Link>
        ))}
      </section>

      <section className="dashboard-action-band">
        <div className="dashboard-action-copy">
          <div className="page-eyebrow">Next Move</div>
          <h2>先上傳影片，再讓 AI 依完整內容出題</h2>
          <p>新的 Quiz 流程會優先根據影片逐字稿，生成偏程式理解、除錯與流程推理的題目。</p>
        </div>
        <div className="dashboard-action-links">
          <Link to="/Video" className="dashboard-primary-link">Upload Video</Link>
          <Link to="/Quiz" className="dashboard-secondary-link">Open Quiz</Link>
        </div>
      </section>
    </div>
  );
};

export default Home;
