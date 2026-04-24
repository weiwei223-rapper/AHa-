import "./PageIndex.css";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../api";

type Video = {
  id: number;
  video_link: string;
  title?: string | null;
  created_at: string;
};

type VideoStatusProps = {
  VideoName: string;
};

const Video = (_props: VideoStatusProps) => {
  const navigate = useNavigate();
  const [videoLink, setVideoLink] = useState("");
  const [videoTitle, setVideoTitle] = useState("");
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(false);
  const [generatingQuizId, setGeneratingQuizId] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/videos`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data: Video[] = await res.json();
      setVideos(data);
      setError("");
    } catch (err: any) {
      console.error("Error fetching videos:", err);
      setError(`載入影片失敗：${err.message}`);
    }
  };

  const handleUpload = async () => {
    if (!videoLink.trim()) {
      setError("請先輸入影片連結。");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE_URL}/api/videos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_link: videoLink,
          title: videoTitle.trim() || null,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "新增影片失敗");
      }

      const newVideo: Video = await res.json();
      setVideos((prev) => [newVideo, ...prev]);
      setVideoLink("");
      setVideoTitle("");
    } catch (err: any) {
      console.error(err);
      setError(err.message || "新增影片時發生錯誤");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (videoId: number) => {
    if (!confirm("確定要刪除這支影片嗎？")) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/videos/${videoId}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        throw new Error("刪除影片失敗");
      }

      setVideos((prev) => prev.filter((video) => video.id !== videoId));
    } catch (err) {
      console.error(err);
      setError("刪除影片時發生錯誤。");
    }
  };

  const handleGenerateQuiz = async (videoId: number) => {
    setGeneratingQuizId(videoId);
    navigate(`/Quiz?videoId=${videoId}`);
    setGeneratingQuizId(null);
  };

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Video Library</div>
          <h1>影片素材工作台</h1>
          <p>上傳 YouTube 影片後，Chat 可使用影片內容回答問題，Quiz 也會依完整影片內容生成 AI 程式題。</p>
        </div>
        <div className="page-hero-metric">
          <span>Library Size</span>
          <strong>{videos.length}</strong>
          <p>支影片可供 AI 分析</p>
        </div>
      </section>

      <section className="panel-card">
        <div className="panel-header">
          <div>
            <div className="page-eyebrow">Upload Source</div>
            <h2>新增學習影片</h2>
          </div>
        </div>
        <div className="video-upload-grid">
          <input
            type="text"
            value={videoTitle}
            onChange={(e) => setVideoTitle(e.target.value)}
            placeholder="影片標題（可選）"
          />
          <input
            type="text"
            value={videoLink}
            onChange={(e) => setVideoLink(e.target.value)}
            placeholder="YouTube 影片連結"
          />
          <button onClick={handleUpload} disabled={loading} className="page-primary-button">
            {loading ? "Uploading..." : "Add Video"}
          </button>
        </div>
        {error && <div className="page-error">{error}</div>}
      </section>

      <section className="video-library-grid">
        {videos.length === 0 ? (
          <div className="empty-state-card">
            <h3>目前還沒有影片</h3>
            <p>先加入一支 YouTube 影片，系統才能生成聊天上下文與 AI 程式測驗。</p>
          </div>
        ) : (
          videos.map((video) => (
            <article key={video.id} className="video-library-card">
              <div className="video-library-top">
                <div className="video-library-badge">AI Source</div>
                <h3>{video.title || "Untitled Video"}</h3>
                <a
                  href={video.video_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="video-library-link"
                >
                  {video.video_link}
                </a>
              </div>
              <div className="video-library-meta">
                Added at {new Date(`${video.created_at}Z`).toLocaleString("zh-TW")}
              </div>
              <div className="video-library-actions">
                <button
                  onClick={() => handleGenerateQuiz(video.id)}
                  disabled={generatingQuizId === video.id}
                  className="page-primary-button"
                >
                  {generatingQuizId === video.id ? "Opening..." : "Generate AI Quiz"}
                </button>
                <button onClick={() => handleDelete(video.id)} className="page-danger-button">
                  Delete
                </button>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
};

export default Video;
