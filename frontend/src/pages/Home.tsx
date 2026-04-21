import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { userAPI } from "../api";
import "./PageIndex.css";

type UserStatusProps = {
  name: string;
};

type Video = {
  id: number;
  video_link: string;
  title?: string | null;
  created_at: string;
};

type QuizResult = {
  videoId: number;
  score: number;
  totalQuestions: number;
  percentage: number;
  completedAt: string;
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
      const response = await fetch("http://localhost:8000/api/videos");
      if (!response.ok) {
        return 0;
      }

      const videos: Video[] = await response.json();
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
      label: "學習影片",
      value: stats.videoCount.toString(),
      hint: "參照 Video 頁面的影片列表",
      to: "/Video",
    },
    {
      label: "剩餘點數",
      value: stats.points.toString(),
      hint: "參照 Profile 頁面的點數資料",
      to: "/Profile",
    },
    {
      label: "完成測驗",
      value: stats.completedQuizCount.toString(),
      hint: "參照 Quiz 頁面的作答紀錄",
      to: "/Quiz",
    },
    {
      label: "平均正確率",
      value: `${stats.averageAccuracy}%`,
      hint: "參照 Quiz 頁面的歷次成績",
      to: "/Quiz",
    },
  ];

  return (
    <div className="main">
      <div className="Welcome">
        <h1>Welcome Back, {name}!</h1>
      </div>

      <div className="home-stats-grid">
        {cards.map((card) => (
          <Link key={card.label} to={card.to} className="home-stat-card">
            <span className="home-stat-label">{card.label}</span>
            <span className="home-stat-value">{card.value}</span>
            <span className="home-stat-hint">{card.hint}</span>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default Home;
