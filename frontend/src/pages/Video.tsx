import "./PageIndex.css";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { videoAPI, documentAPI } from "../api";
import ReportModal from "../component/ReportModal";

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

type DocumentItem = {
  id: number;
  filename: string;
  title: string;
  content_text?: string;
  outline?: string;
  created_at: string;
};

type TranscriptChunk = {
  index: number;
  content: string;
  score?: number | null;
};

type TokenUsage = {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
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
  token_usage?: TokenUsage;
  consumed_points?: number;
};

const Video = () => {
  const navigate = useNavigate();
  const userId = Number(localStorage.getItem("userId") || 1);
  const [activeTab, setActiveTab] = useState<'video' | 'pdf'>('video');

  // Video States
  const [videoLink, setVideoLink] = useState("");
  const [videoTitle, setVideoTitle] = useState("");
  const [videos, setVideos] = useState<VideoItem[]>([]);
  
  // Document States
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionId, setActionId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportingVideoId, setReportingVideoId] = useState<number | null>(null);

  useEffect(() => {
    void fetchVideos();
    void fetchDocs();
  }, [userId]);

  const fetchVideos = async () => {
    try {
      const response = await videoAPI.getVideos(userId);
      setVideos(response.data);
    } catch (err: any) {
      console.error("Error fetching videos:", err);
    }
  };

  const fetchDocs = async () => {
    try {
      const response = await documentAPI.getDocuments(userId);
      setDocs(response.data);
    } catch (err: any) {
      console.error("Error fetching docs:", err);
    }
  };

  const handleVideoUpload = async () => {
    if (!videoLink.trim()) { setError("請輸入 YouTube 影片連結"); return; }
    setLoading(true);
    setError("");
    try {
      const response = await videoAPI.createVideo({
        video_link: videoLink.trim(),
        title: videoTitle.trim() || null,
        user_id: userId,
      });
      setVideos((prev) => [response.data, ...prev]);
      setVideoLink("");
      setVideoTitle("");
      window.dispatchEvent(new CustomEvent('video-updated', { detail: { userId } }));
    } catch (err: any) {
      setError(err.response?.data?.detail || "新增影片失敗");
    } finally {
      setLoading(false);
    }
  };

  const handlePdfUpload = async () => {
    if (!selectedFile) { setError("請選擇 PDF 檔案"); return; }
    setLoading(true);
    setError("");
    try {
      const response = await documentAPI.uploadDocument(userId, selectedFile);
      setDocs((prev) => [response.data, ...prev]);
      setSelectedFile(null);
      const fileInput = document.getElementById('pdf-input') as HTMLInputElement;
      if (fileInput) fileInput.value = "";
      window.dispatchEvent(new CustomEvent('video-updated', { detail: { userId } }));
    } catch (err: any) {
      setError(err.response?.data?.detail || "上傳 PDF 失敗");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeVideo = async (videoId: number) => {
    setActionId(videoId);
    setError("");
    try {
      const response = await videoAPI.analyzeVideo(videoId, userId);
      setAnalysis(response.data);
      await fetchVideos();
      window.dispatchEvent(new CustomEvent('points-updated', { detail: { userId } }));
    } catch (err: any) {
      setError(err.response?.data?.detail || "影片分析失敗");
    } finally {
      setActionId(null);
    }
  };

  const handleAnalyzeDoc = async (docId: number) => {
    setActionId(docId);
    setError("");
    try {
      const response = await documentAPI.analyzeDocument(docId, userId);
      setAnalysis(response.data);
      await fetchDocs();
      window.dispatchEvent(new CustomEvent('points-updated', { detail: { userId } }));
    } catch (err: any) {
      setError(err.response?.data?.detail || "文件分析失敗");
    } finally {
      setActionId(null);
    }
  };

  const handleOpenQuiz = (id: number, type: 'video' | 'pdf') => {
    if (type === 'video') navigate(`/Quiz?videoId=${id}`);
    else navigate(`/Quiz?docId=${id}`);
  };

  const handleDeleteVideo = async (videoId: number) => {
    if (!window.confirm("確定要刪除此影片嗎？")) return;
    try {
      await videoAPI.deleteVideo(videoId);
      setVideos(prev => prev.filter(v => v.id !== videoId));
    } catch (err) {
      alert("刪除影片失敗");
    }
  };

  const handleDeleteDoc = async (docId: number) => {
    if (!window.confirm("確定要刪除此文件嗎？")) return;
    try {
      await documentAPI.deleteDocument(docId);
      setDocs(prev => prev.filter(d => d.id !== docId));
    } catch (err) {
      alert("刪除文件失敗");
    }
  };

  const handleReportError = async (report: string) => {
    if (!reportingVideoId) return;
    try {
      await videoAPI.reportError(reportingVideoId, report);
      alert("回報已送出，謝謝您的回饋！");
    } catch (err) {
      alert("回報失敗，請稍後再試。");
    }
  };

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Knowledge Library</div>
          <h1>影片與文件資料庫</h1>
          <p>支援 YouTube 影片解析與 PDF 文件匯入，AI 將自動為您提取 Python 知識要點。</p>
        </div>
        <div className="page-hero-metric">
          <span>Sources</span>
          <strong>{videos.length + docs.length}</strong>
        </div>
      </section>

      <div className="profile-tab-row" style={{ marginBottom: '20px' }}>
        <button 
          className={`profile-tab-btn ${activeTab === 'video' ? 'active' : ''}`}
          onClick={() => setActiveTab('video')}
        >
          YouTube 影片
        </button>
        <button 
          className={`profile-tab-btn ${activeTab === 'pdf' ? 'active' : ''}`}
          onClick={() => setActiveTab('pdf')}
        >
          PDF 文件
        </button>
      </div>

      {activeTab === 'video' ? (
        <section className="panel-card">
          <div className="panel-header">
            <div>
              <div className="page-eyebrow">Video Upload</div>
              <h2>新增 YouTube 來源</h2>
            </div>
          </div>
          <div className="video-upload-grid">
            <input type="text" value={videoTitle} onChange={e => setVideoTitle(e.target.value)} placeholder="影片標題 (可選)" />
            <input type="text" value={videoLink} onChange={e => setVideoLink(e.target.value)} placeholder="https://www.youtube.com/watch?v=..." />
            <button onClick={handleVideoUpload} disabled={loading} className="page-primary-button">
              {loading ? "處理中..." : "Add Video"}
            </button>
          </div>
          {error && activeTab === 'video' && <div className="page-error">{error}</div>}
        </section>
      ) : (
        <section className="panel-card">
          <div className="panel-header">
            <div>
              <div className="page-eyebrow">Document Upload</div>
              <h2>上傳 PDF 講義</h2>
            </div>
          </div>
          <div className="video-upload-grid">
            <input 
              id="pdf-input"
              type="file" 
              accept=".pdf" 
              onChange={e => setSelectedFile(e.target.files?.[0] || null)}
              style={{ padding: '10px' }}
            />
            <button onClick={handlePdfUpload} disabled={loading} className="page-primary-button">
              {loading ? "解析中..." : "Upload PDF"}
            </button>
          </div>
          {error && activeTab === 'pdf' && <div className="page-error">{error}</div>}
        </section>
      )}

      <section className="video-library-grid">
        {activeTab === 'video' ? (
          videos.map(v => (
            <article key={v.id} className="video-library-card">
              <div className="video-library-top">
                <div className="video-library-badge">Video</div>
                <h3 className="video-library-title">{v.title || "Untitled Video"}</h3>
              </div>
              <div className="video-library-actions">
                <button onClick={() => handleAnalyzeVideo(v.id)} disabled={actionId === v.id} className="page-secondary-button">
                  {actionId === v.id ? "分析中..." : "Analyze"}
                </button>
                <button onClick={() => {
                  setReportingVideoId(v.id);
                  setIsReportModalOpen(true);
                }} className="page-secondary-button">Report</button>
                <button onClick={() => handleDeleteVideo(v.id)} className="page-secondary-button" style={{color: '#ef4444'}}>Delete</button>
                <button onClick={() => handleOpenQuiz(v.id, 'video')} className="page-primary-button">Quiz</button>
              </div>
            </article>
          ))
        ) : (
          docs.map(d => (
            <article key={d.id} className="video-library-card">
              <div className="video-library-top">
                <div className="video-library-badge" style={{ backgroundColor: 'rgba(168, 85, 247, 0.15)', color: '#a855f7' }}>PDF</div>
                <h3 className="video-library-title">{d.title}</h3>
              </div>
              <div className="video-library-actions">
                <button onClick={() => handleAnalyzeDoc(d.id)} disabled={actionId === d.id} className="page-secondary-button">
                  {actionId === d.id ? "分析中..." : "Analyze"}
                </button>
                <button onClick={() => handleDeleteDoc(d.id)} className="page-secondary-button" style={{color: '#ef4444'}}>Delete</button>
                <button onClick={() => handleOpenQuiz(d.id, 'pdf')} className="page-primary-button">Quiz</button>
              </div>
            </article>
          ))
        )}
      </section>

      {analysis && (
        <section className="panel-card" style={{ marginTop: '30px' }}>
          <div className="panel-header"><h2>{analysis.video_title} - 分析內容</h2></div>
          <pre className="code-snippet" style={{ whiteSpace: 'pre-wrap', maxHeight: '400px', overflowY: 'auto' }}>{analysis.outline_markdown}</pre>
        </section>
      )}

      <ReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        onSubmit={handleReportError}
        title="回報大綱錯誤"
        subtitle="如果您發現 AI 生成的大綱有誤、格式混亂或不完整，請告訴我們。"
      />
    </div>
  );
};

export default Video;
