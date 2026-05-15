import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE_URL, parseResponseBody, userAPI } from "../api";
import "./PageIndex.css";
import heroImg from "../assets/hero.png";

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
  analyzedVideoCount: number;
};

const QUIZ_RESULTS_KEY = "quizResults";

const Home = ({ name }: UserStatusProps) => {
  const [stats, setStats] = useState<HomeStats>({
    videoCount: 0,
    points: 0,
    completedQuizCount: 0,
    averageAccuracy: 0,
    analyzedVideoCount: 0,
  });

  useEffect(() => {
    void loadStats();
  }, []);

  useEffect(() => {
    const handleVideoUpdated = () => {
      void loadStats();
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void loadStats();
      }
    };

    window.addEventListener("video-updated", handleVideoUpdated);
    window.addEventListener("points-updated", handleVideoUpdated);
    window.addEventListener("focus", handleVideoUpdated);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("video-updated", handleVideoUpdated);
      window.removeEventListener("focus", handleVideoUpdated);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  const loadStats = async () => {
    const userId = Number(localStorage.getItem("userId") || 0);
    if (!userId) return;

    try {
      const [statsResp, quizResults] = await Promise.all([
        userAPI.getStats(userId),
        Promise.resolve(getQuizResults()),
      ]);

      const stats = statsResp.data;
      const totalCorrect = quizResults.reduce((sum, item) => sum + item.score, 0);
      const totalQuestions = quizResults.reduce((sum, item) => sum + item.totalQuestions, 0);

      setStats({
        videoCount: stats.video_count,
        points: stats.remaining_points,
        completedQuizCount: stats.completed_quizzes,
        averageAccuracy: stats.average_accuracy,
        analyzedVideoCount: stats.analyzed_video_count, // Add this
      });
    } catch (error) {
      console.error("Failed to load stats:", error);
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

  const tutorialSteps = [
    {
      title: "1. 探索影片",
      content: "在『Video』頁面貼上 YouTube 連結。我們支援 Python 相關的教學影片，系統會自動為您生成大綱與逐字稿。",
      icon: "📺"
    },
    {
      title: "2. 生成測驗",
      content: "前往『Quiz』頁面選擇已解析的影片，調整您想要練習的題目數量（1-10 題），點擊 Generate 即可開始。",
      icon: "🎯"
    },
    {
      title: "3. 程式實戰",
      content: "在瀏覽器編輯器中補全程式碼。您可以使用『Test』按鈕即時執行程式並查看輸出結果。",
      icon: "💻"
    },
    {
      title: "4. AI 助教",
      content: "測驗完成後，系統會給予邏輯診斷。遇到困難時，右下角的 Workspace Chat 隨時待命為您解答影片中的難點。",
      icon: "🤖"
    }
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
        <div className="dashboard-hero-visual" style={{ flex: '1', display: 'flex', justifyContent: 'center', alignItems: 'center', maxWidth: '300px' }}>
          <img src={heroImg} alt="Hero" style={{ width: '100%', height: 'auto', borderRadius: '20px', boxShadow: '0 10px 30px rgba(0,0,0,0.3)' }} />
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

      {/* Tutorial Content Starts Here */}
      <section className="page-hero" style={{ marginTop: '40px', paddingTop: '40px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
        <div>
          <div className="page-eyebrow">Learning Guide</div>
          <h1>使用教學</h1>
          <p>歡迎來到 AHa AI 學習平台！跟隨以下步驟，開啟您的 Python 學習之旅。</p>
        </div>
      </section>

      <section className="video-library-grid">
        {tutorialSteps.map((step, index) => (
          <article key={index} className="video-library-card" style={{ minHeight: 'auto' }}>
            <div style={{ fontSize: '2rem', marginBottom: '15px' }}>{step.icon}</div>
            <h3 style={{ margin: '0 0 10px 0', color: '#2bc1f1' }}>{step.title}</h3>
            <p style={{ color: '#94a3b8', lineHeight: '1.6', fontSize: '0.95rem' }}>
              {step.content}
            </p>
          </article>
        ))}
      </section>

      <section className="panel-card" style={{ marginTop: '20px', marginBottom: '40px' }}>
        <h2>常見問題</h2>
        <div style={{ marginTop: '20px', display: 'grid', gap: '20px' }}>
          <div>
            <h4 style={{ color: 'white', marginBottom: '8px' }}>Q: 為什麼有些影片無法上傳？</h4>
            <p style={{ color: '#94a3b8' }}>為了保持平台專業性，我們僅允許與 Python 程式設計相關的內容。系統會自動偵測標題與內容進行過濾。</p>
          </div>
          <div>
            <h4 style={{ color: 'white', marginBottom: '8px' }}>Q: 測驗進度會消失嗎？</h4>
            <p style={{ color: '#94a3b8' }}>不會。您的測驗進度會即時同步到雲端資料庫。您可以在『Unfinished Test』中查看並隨時繼續練習。</p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
