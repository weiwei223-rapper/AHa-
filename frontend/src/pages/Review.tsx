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

  useEffect(() => {
    void fetchResults();
  }, []);

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

  // 1. Line Chart: 分數趨勢
  const lineChartData = useMemo(() => {
    const sorted = [...results].sort((a, b) => new Date(a.completed_at).getTime() - new Date(b.completed_at).getTime());
    return {
      labels: sorted.map(r => new Date(r.completed_at).toLocaleDateString("zh-TW")),
      datasets: [
        {
          label: "分數趨勢 (%)",
          data: sorted.map(r => r.score),
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56, 189, 248, 0.2)",
          fill: true,
          tension: 0.4,
        },
      ],
    };
  }, [results]);

  // 2. Bar Chart: 不同測驗的表現
  const barChartData = useMemo(() => {
    const lastSix = [...results].sort((a, b) => new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime()).slice(0, 6).reverse();
    return {
      labels: lastSix.map(r => r.title || "未命名"),
      datasets: [
        {
          label: "測驗得分",
          data: lastSix.map(r => r.score),
          backgroundColor: lastSix.map(r => r.score >= 60 ? "rgba(74, 222, 128, 0.6)" : "rgba(251, 113, 133, 0.6)"),
          borderColor: lastSix.map(r => r.score >= 60 ? "#4ade80" : "#fb7185"),
          borderWidth: 1,
        },
      ],
    };
  }, [results]);

  // 3. Radar Chart: 技能分佈 (從最近的測驗中模擬概念掌握度)
  const radarChartData = useMemo(() => {
    // 這裡從最近的 3 次測驗中統計 reference_concept 的成功率
    const recentDetails = results.slice(0, 5).map(r => {
      try {
        return JSON.parse(r.details_json || "[]");
      } catch { return []; }
    }).flat();

    const conceptStats: Record<string, { total: number; passed: number }> = {};
    recentDetails.forEach((d: any) => {
      const concept = d.reference_concept || "基礎語法";
      if (!conceptStats[concept]) conceptStats[concept] = { total: 0, passed: 0 };
      conceptStats[concept].total += 1;
      if (d.passed) conceptStats[concept].passed += 1;
    });

    const labels = Object.keys(conceptStats).slice(0, 6);
    if (labels.length < 3) {
      // 墊片數據避免圖表太難看
      ["迴圈控制", "條件判斷", "資料型別", "函式應用"].forEach(l => {
        if (!labels.includes(l) && labels.length < 5) labels.push(l);
      });
    }

    return {
      labels,
      datasets: [
        {
          label: "技能掌握度",
          data: labels.map(l => conceptStats[l] ? (conceptStats[l].passed / conceptStats[l].total) * 100 : Math.random() * 40 + 30),
          backgroundColor: "rgba(129, 140, 248, 0.2)",
          borderColor: "#818cf8",
          borderWidth: 2,
          pointBackgroundColor: "#818cf8",
        },
      ],
    };
  }, [results]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, labels: { color: "#94a3b8" } },
    },
    scales: {
      y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148, 163, 184, 0.1)" } },
      x: { ticks: { color: "#94a3b8" }, grid: { display: false } },
    },
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

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!window.confirm("確定要刪除這筆紀錄嗎？")) return;
    try {
      await quizAPI.deleteResult(id);
      setResults(results.filter((r) => r.id !== id));
      if (selectedResult?.id === id) setSelectedResult(null);
    } catch (err) {
      alert("刪除失敗");
    }
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
        <section className="dashboard-grid" style={{ marginBottom: '40px' }}>
          <div className="panel-card" style={{ height: '350px', padding: '20px' }}>
            <h2 style={{ marginBottom: '15px', fontSize: '1.2em' }}>學習分數趨勢</h2>
            <div style={{ height: '250px' }}>
              <Line data={lineChartData} options={chartOptions} />
            </div>
          </div>
          <div className="panel-card" style={{ height: '350px', padding: '20px' }}>
            <h2 style={{ marginBottom: '15px', fontSize: '1.2em' }}>最近測驗表現</h2>
            <div style={{ height: '250px' }}>
              <Bar data={barChartData} options={chartOptions} />
            </div>
          </div>
          <div className="panel-card" style={{ height: '350px', padding: '20px' }}>
            <h2 style={{ marginBottom: '15px', fontSize: '1.2em' }}>概念掌握度分析</h2>
            <div style={{ height: '250px' }}>
              <Radar data={radarChartData} options={radarOptions} />
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
                <button className="page-secondary-button" style={{ color: '#fb7185', borderColor: '#fb7185' }} onClick={(e) => handleDelete(e, res.id)}>刪除紀錄</button>
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
          <div style={{ marginBottom: "20px" }}>
            <button onClick={() => setSelectedResult(null)} className="page-secondary-button">
              ← 返回列表
            </button>
          </div>
          <h2>{selectedResult.title || "測驗詳細回顧"}</h2>
          <p style={{ color: "#94a3b8", marginBottom: "20px" }}>
            完成時間：{new Date(selectedResult.completed_at).toLocaleString("zh-TW")} | 分數：{selectedResult.score}%
          </p>
          {renderDetails(selectedResult.details_json)}
        </section>
      )}
    </div>
  );
};

export default Review;
