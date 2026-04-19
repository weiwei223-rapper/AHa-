import "./PageIndex.css";
import { useState, useEffect } from "react";

type Video = {
  id: number;
  video_link: string;
  title?: string | null;
  created_at: string;
};

type VideoStausProps = {
  VideoName: string;   // 你原本傳的 prop，暫時保留（之後可移除）
};

const Video = (props: VideoStausProps) => {
  const [videoLink, setVideoLink] = useState("");
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // 載入時取得已上傳的影片列表
  useEffect(() => {
    fetchVideos();
  }, []);

  const fetchVideos = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/videos");
      if (!res.ok) throw new Error("無法取得影片列表");
      const data: Video[] = await res.json();
      setVideos(data);
    } catch (err: any) {
      console.error(err);
      setError("載入影片失敗");
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
      const res = await fetch("http://localhost:8000/api/videos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_link: videoLink }),   // ← 後端 schema 的欄位名稱
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "上傳失敗");
      }

      const newVideo: Video = await res.json();

      // 即時更新頁面
      setVideos((prev) => [newVideo, ...prev]);
      setVideoLink("");           // 清空輸入框
      alert("✅ 影片連結上傳成功！");
    } catch (err: any) {
      console.error(err);
      setError(err.message || "上傳發生錯誤");
      alert(err.message || "上傳失敗，請稍後再試");
    } finally {
      setLoading(false);
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
          id="VideoID"
          value={videoLink}
          onChange={(e) => setVideoLink(e.target.value)}
          placeholder="影片連結[](https://...)"
          className="video-input"
        />
        <button onClick={handleUpload} disabled={loading}>
          <span>{loading ? "上傳中..." : "上傳影片連結"}</span>
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="container">
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
                {video.title || video.video_link}
              </a>
              <p className="video-time">
                上傳時間：{new Date(video.created_at).toLocaleString("zh-TW")}
              </p>
            </div>
          ))
        )}
      </div>

      {/* 保留原本的 props 顯示（可自行移除） */}
      <div style={{ marginTop: "30px", opacity: 0.5 }}>
        <small>原本的 prop 測試：{props.VideoName}</small>
      </div>
    </div>
  );
};

export default Video;