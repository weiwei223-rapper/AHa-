import { useEffect, useState, useMemo } from "react";
import { quizAPI } from "../api";
import "./PageIndex.css";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line, Bar, Radar } from "react-chartjs-2";
import ReportModal from "../component/ReportModal";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
);

type QuizResultItem = {
  id: number;
  video_id: number;
  title?: string | null;
  score: number;
  total_questions: number;
  details_json?: string | null;
  completed_at: string;
};

const Review = () => {
  const userId = Number(localStorage.getItem("userId") || 1);
  const [results, setResults] = useState<QuizResultItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedResult, setSelectedResult] = useState<QuizResultItem | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  useEffect(() => {
    void fetchResults();
  }, []);

  const handleReportQuizError = async (description: string) => {
    if (!selectedResult) return;
    try {
      await quizAPI.reportQuizError(selectedResult.id, description);
      alert("感謝您的回報！題目錯誤已記錄。");
    } catch (err) {
      console.error("Error reporting quiz error:", err);
      alert("提交回報時發生錯誤，請稍後再試。");
    }
  };

  const fetchResults = async () => {
    try {
      setLoading(true);
      const res = await quizAPI.getResults(userId);
      setResults(res.data);
    } catch (err: any) {
      console.error("Error fetching results:", err);
      setError("無法載入歷史作答紀錄");
    } finally {
      setLoading(false);
    }
  };

  // 1. Line Chart: 學習進度曲線 (累計平均分數)
  const progressChartData = useMemo(() => {
    const sorted = [...results].sort((a, b) => new Date(a.completed_at).getTime() - new Date(b.completed_at).getTime());
    let sum = 0;
    const runningAvg = sorted.map((r, i) => {
      sum += r.score;
      return sum / (i + 1);
    });

    return {
      labels: sorted.map(r => new Date(r.completed_at).toLocaleDateString("zh-TW")),
      datasets: [
        {
          label: "累計平均正確率 (%)",
          data: runningAvg,
          borderColor: "#2bc1f1",
          backgroundColor: "rgba(43, 193, 241, 0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointBackgroundColor: "#2bc1f1",
        },
      ],
    };
  }, [results]);

  // 2. Radar Chart: 技能掌握分布
  const skillChartData = useMemo(() => {
    const recentDetails = results.slice(0, 8).map(r => {
      try { return JSON.parse(r.details_json || "[]"); } catch { return []; }
    }).flat();

    const stats: Record<string, { total: number; passed: number }> = {};
    recentDetails.forEach((d: any) => {
      let concept = d.reference_concept || "基礎語法";
      // Legacy mapping
      if (concept === "關鍵字熟練") concept = "基礎語法";
      if (concept === "邏輯運算") concept = "條件判斷";
      if (concept === "函式架構") concept = "函式應用";

      if (!stats[concept]) stats[concept] = { total: 0, passed: 0 };
      stats[concept].total += 1;
      if (d.passed) stats[concept].passed += 1;
    });

    const labels = ["基礎語法", "條件判斷", "迴圈控制", "資料處理", "函式應用", "物件導向"];

    return {
      labels,
      datasets: [
        {
          label: "當前能力分布",
          data: labels.map(l => stats[l] ? (stats[l].passed / stats[l].total) * 100 : 20),
          backgroundColor: "rgba(129, 140, 248, 0.2)",
          borderColor: "#818cf8",
          borderWidth: 2,
          pointBackgroundColor: "#818cf8",
        },
      ],
    };
  }, [results]);

  // 3. Bar Chart: 答題正確率分析 (答對 vs 答錯題數)
  const ratioChartData = useMemo(() => {
    const lastSix = [...results].sort((a, b) => new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime()).slice(0, 6).reverse();
    return {
      labels: lastSix.map(r => r.title || "未命名"),
      datasets: [
        {
          label: "答對題數",
          data: lastSix.map(r => Math.round((r.score / 100) * r.total_questions)),
          backgroundColor: "rgba(74, 222, 128, 0.6)",
          borderRadius: 4,
        },
        {
          label: "答錯題數",
          data: lastSix.map(r => r.total_questions - Math.round((r.score / 100) * r.total_questions)),
          backgroundColor: "rgba(251, 113, 133, 0.6)",
          borderRadius: 4,
        }
      ],
    };
  }, [results]);

  // 4. Bar Chart: 學習活躍度 (每日測驗次數)
  const activityChartData = useMemo(() => {
    const dailyCount: Record<string, number> = {};
    results.forEach(r => {
      const date = new Date(r.completed_at).toLocaleDateString("zh-TW");
      dailyCount[date] = (dailyCount[date] || 0) + 1;
    });

    const lastSevenDays = [...Array(7)].map((_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (6 - i));
      return d.toLocaleDateString("zh-TW");
    });

    return {
      labels: lastSevenDays,
      datasets: [
        {
          label: "每日完成測驗數",
          data: lastSevenDays.map(date => dailyCount[date] || 0),
          backgroundColor: "#38bdf8",
          borderColor: "#0ea5e9",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    };
  }, [results]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' as const, labels: { color: "#94a3b8", font: { size: 12 } } },
      tooltip: { backgroundColor: '#0f172a', titleColor: '#fff', bodyColor: '#cbd5e1' }
    },
    scales: {
      y: { stacked: false, ticks: { color: "#94a3b8" }, grid: { color: "rgba(148, 163, 184, 0.05)" } },
      x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
    },
  };

  const stackedOptions = {
    ...chartOptions,
    scales: {
      y: { stacked: true, ticks: { color: "#94a3b8" }, grid: { color: "rgba(148, 163, 184, 0.05)" } },
      x: { stacked: true, ticks: { color: "#94a3b8" }, grid: { display: false } },
    }
  };

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: { color: "rgba(148, 163, 184, 0.2)" },
        grid: { color: "rgba(148, 163, 184, 0.2)" },
        pointLabels: { color: "#94a3b8", font: { size: 12 } },
        ticks: { display: false },
        suggestedMin: 0,
        suggestedMax: 100,
      },
    },
    plugins: {
      legend: { labels: { color: "#94a3b8" } },
    },
  };

  const startEdit = (e: React.MouseEvent, res: QuizResultItem) => {
    e.stopPropagation();
    setEditingId(res.id);
    setNewTitle(res.title || "未命名測驗");
  };

  const handleRename = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await quizAPI.updateResult(id, { title: newTitle });
      setResults(results.map((r) => (r.id === id ? { ...r, title: newTitle } : r)));
      setEditingId(null);
    } catch (err) {
      alert("更改名稱失敗");
    }
  };


  const renderDetails = (detailsJson: string | null | undefined) => {
    if (!detailsJson) return <p>無詳細作答資料</p>;
    try {
      const details = JSON.parse(detailsJson);
      return (
        <div className="quiz-review-list">
          {details.map((detail: any, index: number) => (
            <article key={index} className="quiz-review-card">
              <div className={`quiz-review-status ${detail.passed ? "correct" : "review"}`}>
                {detail.passed ? "Logic Correct" : "Logic Failed"}
              </div>
              {detail.question_text && (
                <h3 style={{ marginTop: "12px", fontSize: "1.1em" }}>{detail.question_text}</h3>
              )}
              <div style={{ marginTop: "12px" }}>
                <p><strong>驗證詳情：</strong></p>
                <ul style={{ listStyle: "none", padding: 0 }}>
                  {detail.test_results?.map((res: any, i: number) => (
                    <li key={i} style={{ color: res.passed ? "#4ade80" : "#fb7185", fontSize: "0.9em", marginBottom: "4px" }}>
                      Test {i+1}: {res.passed ? "✓ Passed" : `✗ Failed (Expected: ${res.expected}, Actual: ${res.actual})`}
                    </li>
                  ))}
                </ul>
              </div>
              <div style={{ marginTop: "12px" }}>
                <p><strong>當時作答：</strong></p>
                <pre className="code-snippet">{detail.user_answer || detail.user_full_code || "N/A"}</pre>
              </div>
            </article>
          ))}
        </div>
      );
    } catch {
      return <p>資料格式錯誤，無法解析詳情。</p>;
    }
  };

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">History Review</div>
          <h1>歷史作答紀錄</h1>
          <p>在這裡你可以回顧過去所有的測驗表現、更改名稱，所有的學習腳印都將被永久保留。</p>
        </div>
      </section>

      {error && <div className="page-error">{error}</div>}
      {loading && <div className="page-loading">正在載入紀錄...</div>}

      {!loading && !selectedResult && results.length > 0 && (
        <section className="dashboard-grid" style={{ marginBottom: '40px', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
          <div className="panel-card" style={{ height: '350px', padding: '20px' }}>
            <h2 style={{ marginBottom: '15px', fontSize: '1.1em', color: '#2bc1f1' }}>學習進度曲線</h2>
            <div style={{ height: '250px' }}>
              <Line data={progressChartData} options={chartOptions} />
            </div>
          </div>
          <div className="panel-card" style={{ height: '350px', padding: '20px' }}>
            <h2 style={{ marginBottom: '15px', fontSize: '1.1em', color: '#818cf8' }}>技能掌握分布</h2>
            <div style={{ height: '250px' }}>
              <Radar data={skillChartData} options={radarOptions} />
            </div>
          </div>
          <div className="panel-card" style={{ height: '350px', padding: '20px' }}>
            <h2 style={{ marginBottom: '15px', fontSize: '1.1em', color: '#fb7185' }}>答題正確率分析</h2>
            <div style={{ height: '250px' }}>
              <Bar data={ratioChartData} options={stackedOptions} />
            </div>
          </div>
          <div className="panel-card" style={{ height: '350px', padding: '20px' }}>
            <h2 style={{ marginBottom: '15px', fontSize: '1.1em', color: '#38bdf8' }}>學習活躍度 (最近 7 日)</h2>
            <div style={{ height: '250px' }}>
              <Bar data={activityChartData} options={chartOptions} />
            </div>
          </div>
        </section>
      )}

      {!loading && !selectedResult && (
        <section className="video-library-grid">
          {results.map((res) => (
            <article key={res.id} className="video-library-card" style={{ cursor: "pointer" }} onClick={() => setSelectedResult(res)}>
              <div className="video-library-top">
                <div className="video-library-badge">Score: {res.score}%</div>
                {editingId === res.id ? (
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }} onClick={e => e.stopPropagation()}>
                    <input 
                      className="page-input" 
                      value={newTitle} 
                      onChange={e => setNewTitle(e.target.value)} 
                      autoFocus
                    />
                    <button className="page-primary-button" onClick={(e) => handleRename(e, res.id)}>儲存</button>
                    <button className="page-secondary-button" onClick={() => setEditingId(null)}>取消</button>
                  </div>
                ) : (
                  <h3 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    {res.title || "未命名測驗"}
                    <button style={{ background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer', fontSize: '0.8em' }} onClick={(e) => startEdit(e, res)}>✎ 修改</button>
                  </h3>
                )}
                <p className="video-library-description">
                  測驗時間: {new Date(res.completed_at).toLocaleString("zh-TW")}
                </p>
                <p className="video-library-description">
                  答對題數: {Math.round((res.score / 100) * res.total_questions)} / {res.total_questions}
                </p>
              </div>
              <div className="video-library-actions" style={{ marginTop: '12px' }}>
                <button className="page-primary-button" style={{ flex: 1 }}>查看詳情</button>
              </div>
            </article>
          ))}
          {results.length === 0 && (
            <div className="empty-state-card">
              <h3>尚無測驗紀錄</h3>
              <p>完成測驗後，紀錄會自動出現在這裡。</p>
            </div>
          )}
        </section>
      )}

      {selectedResult && (
        <section className="panel-card">
          <div style={{ marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button onClick={() => setSelectedResult(null)} className="page-secondary-button">
              ← 返回列表
            </button>
            <button onClick={() => setIsReportModalOpen(true)} className="chat-message-report-btn">
              回報題目錯誤
            </button>
          </div>
          <h2>{selectedResult.title || "測驗詳細回顧"}</h2>
          <p style={{ color: "#94a3b8", marginBottom: "20px" }}>
            完成時間：{new Date(selectedResult.completed_at).toLocaleString("zh-TW")} | 分數：{selectedResult.score}%
          </p>
          {renderDetails(selectedResult.details_json)}
        </section>
      )}
      <ReportModal 
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        onSubmit={handleReportQuizError}
        title="回報題目錯誤"
        subtitle="如果您發現 AI 生成的題目有亂碼、邏輯錯誤時告訴我們。"
      />
    </div>
  );
};

export default Review;
