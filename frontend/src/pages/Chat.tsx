import React, { useEffect, useState, useRef } from 'react';
import { chatAPI, feedbackAPI, videoAPI } from '../api';
import './PageIndex.css';
import ChatDB from './ChatDB';
import ReportModal from '../component/ReportModal';

type MessageRole = 'user' | 'assistant';

interface Message {
  role: MessageRole;
  content: string;
}

interface ChatSession {
  id: string;
  title: string;
  updatedAt: string;
  messages: Message[];
  selectedVideoId?: number | null;
  selectedVideoTitle?: string | null;
}

const STORAGE_KEY = 'aha-chat-history-v1';

const createSessionId = () =>
  `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const buildSessionTitle = (messages: Message[]) => {
  const firstUserMessage = messages.find((message) => message.role === 'user');
  if (!firstUserMessage) {
    return 'New conversation';
  }

  const normalized = firstUserMessage.content.replace(/\s+/g, ' ').trim();
  return normalized.length > 24 ? `${normalized.slice(0, 24)}...` : normalized;
};

const createEmptySession = (): ChatSession => ({
  id: createSessionId(),
  title: 'New conversation',
  updatedAt: new Date().toISOString(),
  messages: [],
  selectedVideoId: null,
  selectedVideoTitle: null,
});

const formatUpdatedAt = (value: string) => {
  try {
    return new Intl.DateTimeFormat('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(value));
  } catch {
    return value;
  }
};

const Chat: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState('');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [videos, setVideos] = useState<Array<{ id: number; title?: string | null }>>([]);
  const [videosLoading, setVideosLoading] = useState(false);
  const [videosError, setVideosError] = useState('');
  const [isSidebarVisible, setIsSidebarVisible] = useState(true);

  // Modal State
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportingMessage, setReportingMessage] = useState<Message | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [sessions, loading]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);

    if (!raw) {
      const initialSession = createEmptySession();
      setSessions([initialSession]);
      setActiveSessionId(initialSession.id);
      return;
    }

    try {
      const parsed = JSON.parse(raw) as ChatSession[];
      if (!Array.isArray(parsed) || parsed.length === 0) {
        const fallbackSession = createEmptySession();
        setSessions([fallbackSession]);
        setActiveSessionId(fallbackSession.id);
        return;
      }

      setSessions(parsed);
      setActiveSessionId(parsed[0].id);
    } catch {
      const fallbackSession = createEmptySession();
      setSessions([fallbackSession]);
      setActiveSessionId(fallbackSession.id);
    }
  }, []);

  useEffect(() => {
    void fetchVideos();
  }, []);

  useEffect(() => {
    if (sessions.length === 0) {
      return;
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  const activeSession =
    sessions.find((session) => session.id === activeSessionId) ?? sessions[0] ?? null;

  const fetchVideos = async () => {
    const userId = Number(localStorage.getItem('userId') || 0);
    if (!userId) {
      setVideos([]);
      setVideosError('請先登入以載入影片列表。');
      return;
    }

    setVideosLoading(true);
    setVideosError('');
    try {
      const response = await videoAPI.getVideos(userId);
      const rawVideos = (response.data ?? []) as Array<{ id: number; title?: string | null }>;
      setVideos(rawVideos);
    } catch (requestError: unknown) {
      console.error('Error fetching videos:', requestError);
      const errorObject = requestError as { response?: { data?: { detail?: string } } };
      setVideosError(errorObject.response?.data?.detail || '無法載入影片列表');
      setVideos([]);
    } finally {
      setVideosLoading(false);
    }
  };

  const updateSession = (sessionId: string, nextMessages: Message[]) => {
    const nextUpdatedAt = new Date().toISOString();

    setSessions((prev) =>
      prev
        .map((session) =>
          session.id === sessionId
            ? {
              ...session,
              messages: nextMessages,
              title: buildSessionTitle(nextMessages),
              updatedAt: nextUpdatedAt
            }
            : session
        )
        .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))
    );
  };

  const updateSessionSelection = (sessionId: string, videoId: number, videoTitle: string) => {
    const nextUpdatedAt = new Date().toISOString();
    const greeting: Message = {
      role: 'assistant',
      content: `你好！我是你的 AI 學習助理。關於「${videoTitle}」，你有什麼問題想問嗎？`,
    };

    setSessions((prev) =>
      prev
        .map((session) =>
          session.id === sessionId
            ? {
              ...session,
              selectedVideoId: videoId,
              selectedVideoTitle: videoTitle,
              updatedAt: nextUpdatedAt,
              messages: session.messages.length === 0 ? [greeting] : session.messages,
              title:
                session.title === 'New conversation'
                  ? `「${videoTitle}」`
                  : session.title,
            }
            : session
        )
        .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))
    );
  };

  const handleCreateSession = () => {
    const newSession = createEmptySession();
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    setInput('');
    setError('');
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSessionId(sessionId);
    setError('');
  };

  const handleSend = async () => {
    if (!activeSession || !input.trim() || loading) return;
    if (!activeSession.selectedVideoId) return;

    const trimmedInput = input.trim();
    const userMessage: Message = { role: 'user', content: trimmedInput };
    const nextMessages = [...activeSession.messages, userMessage];

    updateSession(activeSession.id, nextMessages);
    setInput('');
    setLoading(true);
    setError('');

    try {
      const response = await chatAPI.sendMessage({
        message: trimmedInput,
        history: nextMessages,
        user_id: Number(localStorage.getItem('userId') || 0) || undefined,
        video_id: activeSession.selectedVideoId ?? null,
      });

      let reply =
        response.data?.reply ||
        response.data?.message ||
        'Gemini did not return a valid reply.';

      // Validate the reply
      if (!reply || reply.trim().length === 0) {
        reply = '抱歉，Gemini 沒有收到有效的回應。請再試一次。';
      } else if (reply.length > 10000) {
        reply = reply.substring(0, 10000) + '...';
      }

      updateSession(activeSession.id, [
        ...nextMessages,
        { role: 'assistant', content: reply },
      ]);
    } catch (requestError: unknown) {
      console.error('Error sending message:', requestError);

      let errorMessage = '無法連線到 Gemini 服務，請稍後再試。';
      const errorObject = requestError as {
        code?: string;
        response?: { status?: number };
      };
      if (errorObject.code === 'ECONNABORTED') {
        errorMessage = '請求超時，請檢查網路連線後再試。';
      } else if (errorObject.response?.status === 500) {
        errorMessage = '伺服器內部錯誤，請稍後再試。';
      }

      updateSession(activeSession.id, [
        ...nextMessages,
        {
          role: 'assistant',
          content: errorMessage
        },
      ]);
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectVideo = (videoId: number) => {
    if (!activeSession) return;
    const selected = videos.find((video) => video.id === videoId);
    const videoTitle = (selected?.title || `Video #${videoId}`).toString();
    
    const greeting = `你好！我是你的 AI 學習助理。關於「${videoTitle}」，你有什麼問題想問嗎？`;
    const greetingMessage: Message = { role: 'assistant', content: greeting };

    setSessions((prev) =>
      prev.map((session) =>
        session.id === activeSession.id
          ? {
            ...session,
            selectedVideoId: videoId,
            selectedVideoTitle: videoTitle,
            title: videoTitle,
            messages: session.messages.length === 0 ? [greetingMessage] : session.messages,
            updatedAt: new Date().toISOString()
          }
          : session
      )
    );
    setError('');
  };

  const handleReportError = (message: Message) => {
    setReportingMessage(message);
    setIsReportModalOpen(true);
  };

  const handleModalSubmit = async (errorDesc: string) => {
    const userId = Number(localStorage.getItem('userId') || 0);
    if (!reportingMessage) return;

    try {
      await feedbackAPI.createFeedback({
        user_id: userId,
        video_id: activeSession?.selectedVideoId ?? null,
        ai_message: reportingMessage.content,
        user_message: 'USER_ERROR_REPORT',
        error_report: errorDesc,
      });
      setError('感謝您的回報！');
      setTimeout(() => setError(''), 3000);
    } catch (err) {
      console.error('Error submitting report:', err);
      setError('回報失敗，請稍後再試。');
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={`chat-page ${isSidebarVisible ? 'sidebar-open' : 'sidebar-collapsed'}`}>
      <aside className="chat-sidebar">
        <div className="chat-sidebar-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '10px' }}>
          <div className="chat-sidebar-label">歷史紀錄 (History)</div>
          <button 
            className="chat-sidebar-toggle-v-btn"
            onClick={() => setIsSidebarVisible(!isSidebarVisible)}
            title={isSidebarVisible ? "向上收起" : "向下展開"}
          >
            {isSidebarVisible ? '▲' : '▼'}
          </button>
        </div>

        {isSidebarVisible && (
          <div className="chat-history-list">
            {sessions.map((session) => (
              <button
                key={session.id}
                className={`chat-history-card ${session.id === activeSession?.id ? 'active' : ''}`}
                onClick={() => handleSelectSession(session.id)}
              >
                <span className="chat-history-title">{session.title}</span>
                <span className="chat-history-preview">
                  {session.messages[session.messages.length - 1]?.content || 'No messages yet'}
                </span>
                <span className="chat-history-time">{formatUpdatedAt(session.updatedAt)}</span>
              </button>
            ))}
            {sessions.length === 0 && <p style={{ padding: '20px', color: '#8da3bd', textAlign: 'center' }}>尚無對話紀錄</p>}
            
            <button className="chat-new-session" onClick={handleCreateSession} style={{ marginTop: '10px' }}>
              + New Chat
            </button>
          </div>
        )}
      </aside>

      <section className="chat-panel">
        <div className="chat-hero">
          <div className="chat-hero-copy">
            <div className="chat-hero-label">Powered by Gemini</div>
            <h1>聊天工作台</h1>
          </div>
          <div className="chat-hero-stats">
            <div className="chat-stat-card">
              <span>Conversations</span>
              <strong>{sessions.length}</strong>
            </div>
            <div className="chat-stat-card">
              <span>Messages</span>
              <strong>{activeSession?.messages.length ?? 0}</strong>
            </div>
          </div>
        </div>

        <div className="chat-thread-shell">
          <div className="chat-thread-header">
            <div>
              <div className="chat-thread-eyebrow">Current Session</div>
              <h3>{activeSession?.title || 'New conversation'}</h3>
            </div>
            <div className="chat-thread-meta">
              {activeSession ? `Updated ${formatUpdatedAt(activeSession.updatedAt)}` : ''}
            </div>
          </div>

          {!activeSession?.selectedVideoId ? (
            <div className="chat-video-picker">
              <div className="chat-video-picker-head">
                <div className="chat-video-picker-title">請選擇要討論的影片</div>
                <div className="chat-video-picker-subtitle">
                  選定後我會用該影片作為上下文，幫你整理重點、回答問題與延伸學習。
                </div>
              </div>

              {videosError && <div className="chat-video-picker-error">{videosError}</div>}

              <div className="chat-video-picker-actions">
                <button
                  className="chat-video-picker-refresh"
                  onClick={() => void fetchVideos()}
                  disabled={videosLoading}
                  type="button"
                >
                  {videosLoading ? '載入中...' : '重新載入影片'}
                </button>
              </div>

              <div className="chat-video-picker-list" role="list">
                {!videosLoading && videos.length === 0 ? (
                  <div className="chat-video-picker-empty">
                    目前沒有可用影片。請先到 Video 頁上傳影片後再回來。
                  </div>
                ) : (
                  videos.map((video) => (
                    <button
                      key={video.id}
                      className="chat-video-card"
                      onClick={() => handleSelectVideo(video.id)}
                      type="button"
                      role="listitem"
                    >
                      <div className="chat-video-card-title">{video.title || `Video #${video.id}`}</div>
                      <div className="chat-video-card-meta">ID: {video.id}</div>
                    </button>
                  ))
                )}
              </div>
            </div>
          ) : (
            <>
              <div className="chat-thread">
                {activeSession?.messages.map((message, index) => (
                  <article
                    key={`${message.role}-${index}`}
                    className={`chat-message-row ${message.role === 'user' ? 'user' : 'assistant'}`}
                  >
                    <div className="chat-avatar">{message.role === 'user' ? 'You' : 'Gemini'}</div>
                    <div className="chat-message-card">
                      <div className="chat-message-role">
                        {message.role === 'user' ? 'You' : 'Gemini'}
                        {message.role === 'assistant' && (
                          <button 
                            className="chat-message-report-btn"
                            onClick={() => handleReportError(message)}
                            title="回報錯誤"
                          >
                            🚩 回報
                          </button>
                        )}
                      </div>
                      <p>{message.content}</p>
                    </div>
                  </article>
                ))}

                {loading && (
                  <article className="chat-message-row assistant">
                    <div className="chat-avatar">Gemini</div>
                    <div className="chat-message-card typing">
                      <div className="chat-message-role">Gemini</div>
                      <p>Thinking about your question...</p>
                    </div>
                  </article>
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="chat-composer">
                <textarea
                  ref={textareaRef}
                  className="chat-composer-input"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="輸入問題，按 Enter 送出，Shift + Enter 換行"
                  disabled={loading || !activeSession}
                />
                <div className="chat-composer-footer">
                  <div className="chat-composer-hint">
                    可以詢問影片內容整理、重點摘要、題目解析或延伸學習方向。
                  </div>
                  <button className="chat-send-button" onClick={handleSend} disabled={loading || !input.trim()}>
                    {loading ? 'Sending...' : 'Send Message'}
                  </button>
                </div>
                {error && <div className="chat-error-banner">{error}</div>}
              </div>
            </>
          )}
        </div>
      </section>

      <ReportModal 
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        onSubmit={handleModalSubmit}
        title="錯誤回報"
        subtitle="請告訴我們這則訊息哪裡有誤，我們會儘速修正。"
      />
    </div>
  );
};

export default Chat;
