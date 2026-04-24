import "./PageIndex.css";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../api";

type Video = {
  id: number;
  video_link: string;
  title?: string | null;
  created_at: string;
};

type VideoStausProps = {
  VideoName: string;   // 你原本傳的 prop，暫時保留（之後可移除）
};

const Video = (_props: VideoStausProps) => {
  const navigate = useNavigate();
  const [videoLink, setVideoLink] = useState("");
  const [videoTitle, setVideoTitle] = useState("");
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(false);
  const [generatingQuizId, setGeneratingQuizId] = useState<number | null>(null);
  const [error, setError] = useState("");

  // Debug: Log API base URL
  useEffect(() => {
    console.log("API_BASE_URL:", API_BASE_URL);
  }, []);

  // 載入時取得已上傳的影片列表
  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      console.log("Fetching videos from:", `${API_BASE_URL}/api/videos`);
      const res = await fetch(`${API_BASE_URL}/api/videos`);
      console.log("Response status:", res.status);
      if (!res.ok) throw new Error(`HTTP ${res.status}: 無法取得影片列表`);
      const data: Video[] = await res.json();
      console.log("Received data:", data);
      setVideos(data);
      setError(""); // Clear error on success
    } catch (err: any) {
      console.error("Error fetching videos:", err);
      setError(`載入影片失敗: ${err.message}`);
    }
  };

  const handleUpload = async () => {
    if (!videoLink.trim()) {
      alert("請輸入影片連結！");
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
          title: videoTitle.trim() || null
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "上傳失敗");
      }

      const newVideo: Video = await res.json();

      // 即時更新頁面
      setVideos((prev) => [newVideo, ...prev]);
      setVideoLink("");           // 清空輸入框
      setVideoTitle("");          // 清空標題輸入框
      alert("✅ 影片連結上傳成功！");
    } catch (err: any) {
      console.error(err);
      setError(err.message || "上傳發生錯誤");
      alert(err.message || "上傳失敗，請稍後再試");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (videoId: number) => {
    if (!confirm("確定要刪除這個影片嗎？")) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/videos/${videoId}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        throw new Error("刪除失敗");
      }

      // 即時更新頁面
      setVideos((prev) => prev.filter(video => video.id !== videoId));
      alert("✅ 影片已刪除！");
    } catch (err: any) {
      console.error(err);
      alert("刪除失敗，請稍後再試");
    }
  };

  const handleGenerateQuiz = async (videoId: number) => {
    setGeneratingQuizId(videoId);
    try {
      // Navigate to Quiz page with the video ID
      navigate(`/Quiz?videoId=${videoId}`);
    } catch (err: any) {
      console.error(err);
      alert("無法生成測驗，請稍後再試");
    } finally {
      setGeneratingQuizId(null);
    }
  };

  return (
    <div className="main">
      <div>
        <h1>Learning Material</h1>
      </div>

      <div className="upload-section">
        <input
          type="text"
          value={videoTitle}
          onChange={(e) => setVideoTitle(e.target.value)}
          placeholder="影片標題 (選填)"
          className="video-input"
        />
        <input
          type="text"
          id="VideoID"
          value={videoLink}
          onChange={(e) => setVideoLink(e.target.value)}
          placeholder="影片連結 (https://...)"
          className="video-input"
        />
        <button onClick={handleUpload} disabled={loading}>
          <span>{loading ? "上傳中..." : "上傳影片連結"}</span>
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="video-container">
        {videos.length === 0 ? (
          <p className="no-video">目前還沒有上傳任何影片</p>
        ) : (
          videos.map((video) => (
            <div key={video.id} className="box">
              <a
                href={video.video_link}
                target="_blank"
                rel="noopener noreferrer"
                className="video-link"
              >
                {video.title || "未命名影片"}
              </a>
              <p className="video-time">
                上傳時間：{new Date(video.created_at + 'Z').toLocaleString("zh-TW")}
              </p>
              <div style={{ display: "flex", gap: "10px" }}>
                <button 
                  onClick={() => handleGenerateQuiz(video.id)}
                  disabled={generatingQuizId === video.id}
                  className="quiz-btn"
                  style={{
                    backgroundColor: "#4CAF50",
                    color: "white",
                    padding: "8px 16px",
                    border: "none",
                    borderRadius: "4px",
                    cursor: generatingQuizId === video.id ? "not-allowed" : "pointer",
                    opacity: generatingQuizId === video.id ? 0.6 : 1,
                  }}
                >
                  {generatingQuizId === video.id ? "⏳ 生成中..." : "📝 生成測驗"}
                </button>
                <button 
                  onClick={() => handleDelete(video.id)} 
                  className="delete-btn"
                >
                  刪除
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      
    </div>
  );
};

export default Video;
