import "./PageIndex.css";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { videoAPI } from "../api";

type VideoItem = {
  id: number;
  video_link: string;
  title?: string | null;
  outline?: string | null;
  user_id?: number | null;
  cost_points?: number;
  error_report?: string | null;
  created_at: string;
};

type TranscriptChunk = {
  index: number;
  content: string;
  score?: number | null;
};

type VideoAnalysis = {
  video_id: number;
  video_title: string;
  transcript_source: string;
  transcript_excerpt: string;
  outline_markdown: string;
  key_topics: string[];
  retrieved_chunks: TranscriptChunk[];
  vector_backend: string;
  generated_at: string;
};

type VideoStatusProps = {
  VideoName: string;
};

const Video = (_props: VideoStatusProps) => {
  const navigate = useNavigate();
  const userId = Number(localStorage.getItem("userId") || 1);
  const [videoLink, setVideoLink] = useState("");
  const [videoTitle, setVideoTitle] = useState("");
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzingVideoId, setAnalyzingVideoId] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      const response = await videoAPI.getVideos(userId);
      setVideos(response.data);
      setError("");
    } catch (err: any) {
      console.error("Error fetching videos:", err);
      setError(err.response?.data?.detail || "無法載入影片列表");
    }
  };

  const handleUpload = async () => {
    if (!videoLink.trim()) {
      setError("請輸入 YouTube 影片連結");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await videoAPI.createVideo({
        video_link: videoLink.trim(),
        title: videoTitle.trim() || null,
        user_id: userId,
        cost_points: 0,
      });
      setVideos((prev) => [response.data, ...prev]);
      setVideoLink("");
      setVideoTitle("");

      // 發送自定義事件通知其他頁面影片數量已更新
      window.dispatchEvent(new CustomEvent('video-updated', {
        detail: { userId, newVideoCount: videos.length + 1 }
      }));
    } catch (err: any) {
      console.error("Error uploading video:", err);
      setError(err.response?.data?.detail || "新增影片失敗");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (videoId: number) => {
    if (!window.confirm("確定要刪除這支影片嗎？")) {
      return;
    }
    try {
      await videoAPI.deleteVideo(videoId);
      setVideos((prev) => prev.filter((video) => video.id !== videoId));
      if (analysis?.video_id === videoId) {
        setAnalysis(null);
      }
      window.dispatchEvent(new CustomEvent('video-updated', {
        detail: { userId, newVideoCount: Math.max(0, videos.length - 1) }
      }));
    } catch (err: any) {
      console.error("Error deleting video:", err);
      setError(err.response?.data?.detail || "刪除影片失敗");
    }
  };

  const handleAnalyze = async (videoId: number) => {
    setAnalyzingVideoId(videoId);
    setError("");
    try {
      const response = await videoAPI.analyzeVideo(videoId);
      setAnalysis(response.data);
      await fetchVideos();

      // 影片分析完成後，觸發成就更新事件
      // 因為 analyzed_video_count 已更新
      window.dispatchEvent(new CustomEvent('video-updated', {
        detail: { userId, videoIdAnalyzed: videoId }
      }));
    } catch (err: any) {
      console.error("Error analyzing video:", err);
      setError(err.response?.data?.detail || "影片分析失敗");
    } finally {
      setAnalyzingVideoId(null);
    }
  };

  const handleOpenQuiz = (videoId: number) => {
    navigate(`/Quiz?videoId=${videoId}`);
  };

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Video Library</div>
          <h1>影片與知識庫</h1>
          <p>上傳 YouTube 影片後，系統會用 Gemini 建立逐字稿摘要、課程大綱與檢索片段。</p>
        </div>
        <div className="page-hero-metric">
          <span>Videos</span>
          <strong>{videos.length}</strong>
          <p>可用於測驗生成與家教問答</p>
        </div>
      </section>

      <section className="panel-card">
        <div className="panel-header">
          <div>
            <div className="page-eyebrow">Upload Source</div>
            <h2>新增影片</h2>
          </div>
        </div>
        <div className="video-upload-grid">
          <input
            type="text"
            value={videoTitle}
            onChange={(event) => setVideoTitle(event.target.value)}
            placeholder="影片標題，可留空"
          />
          <input
            type="text"
            value={videoLink}
            onChange={(event) => setVideoLink(event.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
          />
          <button onClick={handleUpload} disabled={loading} className="page-primary-button">
            {loading ? "新增中..." : "Add Video"}
          </button>
        </div>
        {error && <div className="page-error">{error}</div>}
      </section>

      <section className="video-library-grid">
        {videos.map((video) => (
          <article key={video.id} className="video-library-card">
            <div className="video-library-top">
              <div className="video-library-badge">Gemini Source</div>
              <h3>{video.title || "Untitled Video"}</h3>
              <a href={video.video_link} target="_blank" rel="noreferrer" className="video-library-link">
                {video.video_link}
              </a>
            </div>
            <div className="video-library-meta">
              Added at {new Date(video.created_at).toLocaleString("zh-TW")}
            </div>
            <div className="video-library-actions">
              <button
                onClick={() => void handleAnalyze(video.id)}
                disabled={analyzingVideoId === video.id}
                className="page-secondary-button"
              >
                {analyzingVideoId === video.id ? "分析中..." : "Analyze"}
              </button>
              <button onClick={() => handleOpenQuiz(video.id)} className="page-primary-button">
                Generate Quiz
              </button>
              <button onClick={() => void handleDelete(video.id)} className="page-danger-button">
                Delete
              </button>
            </div>
          </article>
        ))}

        {videos.length === 0 && (
          <div className="empty-state-card">
            <h3>目前還沒有影片</h3>
            <p>先新增一支教學影片，再建立分析結果與題目。</p>
          </div>
        )}
      </section>

      {analysis && (
        <section className="panel-card">
          <div className="panel-header">
            <div>
              <div className="page-eyebrow">Analysis Result</div>
              <h2>{analysis.video_title}</h2>
            </div>
          </div>

          <div className="quiz-score-band">
            <p>逐字稿來源：{analysis.transcript_source}</p>
            <p>檢索方式：{analysis.vector_backend}</p>
          </div>

          <div className="quiz-review-list">
            <article className="quiz-review-card">
              <div className="quiz-review-status">Outline</div>
              <pre className="code-snippet">{analysis.outline_markdown}</pre>
            </article>

            <article className="quiz-review-card">
              <div className="quiz-review-status">Topics</div>
              <p>{analysis.key_topics.join("、") || "尚未擷取到主題"}</p>
            </article>

            <article className="quiz-review-card">
              <div className="quiz-review-status">Transcript</div>
              <p>{analysis.transcript_excerpt || "沒有逐字稿內容"}</p>
            </article>

            {analysis.retrieved_chunks.map((chunk) => (
              <article key={chunk.index} className="quiz-review-card">
                <div className="quiz-review-status">
                  Chunk {chunk.index} {typeof chunk.score === "number" ? `(${chunk.score.toFixed(3)})` : ""}
                </div>
                <p>{chunk.content}</p>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default Video;
