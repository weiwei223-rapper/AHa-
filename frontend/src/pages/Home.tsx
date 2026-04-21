import { useEffect, useState } from "react";
import "./PageIndex.css";
import { userAPI } from "../api";

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
  videos: number;
  points: number;
  completedQuizzes: number;
  averageAccuracy: number;
};

const QUIZ_RESULTS_KEY = "quizResults";

const Home = ({ name }: UserStatusProps) => {
  const [stats, setStats] = useState<HomeStats>({
    videos: 0,
    points: 0,
    completedQuizzes: 0,
    averageAccuracy: 0,
  });

  useEffect(() => {
    void loadHomeStats();
  }, []);

  const loadHomeStats = async () => {
    try {
      const [videosRes, points] = await Promise.all([
        fetch("http://localhost:8000/api/videos"),
        getUserPoints(),
      ]);

      const videos: Video[] = videosRes.ok ? await videosRes.json() : [];
      const quizResults = readQuizResults();
      const totalCorrect = quizResults.reduce((sum, item) => sum + item.score, 0);
      const totalQuestions = quizResults.reduce((sum, item) => sum + item.totalQuestions, 0);
      const averageAccuracy = totalQuestions > 0 ? Math.round((totalCorrect / totalQuestions) * 100) : 0;

      setStats({
        videos: videos.length,
        points,
        completedQuizzes: quizResults.length,
        averageAccuracy,
      });
    } catch (error) {
      console.error("Failed to load home stats:", error);
    }
  };

  const getUserPoints = async () => {
    const userId = localStorage.getItem("userId");
    const storedUserData = localStorage.getItem("userData");
    const fallbackPoints = storedUserData ? JSON.parse(storedUserData).points ?? 0 : 0;

    if (!userId) {
      return fallbackPoints;
    }

    try {
      const response = await userAPI.getUser(Number(userId));
      const freshUser = response.data;
      localStorage.setItem("userData", JSON.stringify(freshUser));
      return freshUser.points ?? 0;
    } catch (error) {
      console.error("Failed to fetch user points:", error);
      return fallbackPoints;
    }
  };

  const readQuizResults = (): QuizResult[] => {
    try {
      const raw = localStorage.getItem(QUIZ_RESULTS_KEY);
      if (!raw) {
        return [];
      }

      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.error("Failed to parse quiz results:", error);
      return [];
    }
  };

  const statCards = [
    { label: "\u5b78\u7fd2\u5f71\u7247", value: stats.videos.toString() },
    { label: "\u5269\u9918\u9ede\u6578", value: stats.points.toString() },
    { label: "\u5b8c\u6210\u6e2c\u9a57", value: stats.completedQuizzes.toString() },
    { label: "\u5e73\u5747\u6b63\u78ba\u7387", value: `${stats.averageAccuracy}%` },
  ];

  return (
    <div className="main">
      <div className="Welcome">
        <h1>Welcome Back, {name}!</h1>
      </div>

      <div className="home-stats-grid">
        {statCards.map((card) => (
          <div key={card.label} className="home-stat-card">
            <span className="home-stat-label">{card.label}</span>
            <span className="home-stat-value">{card.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Home;
