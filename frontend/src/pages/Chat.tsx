import React, { useEffect, useState } from 'react';
import { chatAPI, videoAPI } from '../api';
import './PageIndex.css';
import ChatDB from './ChatDB';

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
      });

      let reply =
        response.data?.reply ||
        response.data?.message ||
        'The assistant did not return a valid reply.';

      // Validate the reply
      if (!reply || reply.trim().length === 0) {
        reply = '抱歉，我沒有收到有效的回應。請再試一次。';
      } else if (reply.length > 10000) {
        reply = reply.substring(0, 10000) + '...';
      }

      updateSession(activeSession.id, [
        ...nextMessages,
        { role: 'assistant', content: reply },
      ]);
    } catch (requestError: unknown) {
      console.error('Error sending message:', requestError);

      let errorMessage = '無法連線到聊天服務，請稍後再試。';
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
    const title = (selected?.title || `Video #${videoId}`).toString();
    updateSessionSelection(activeSession.id, videoId, title);
    setError('');
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-page">
      <aside className="chat-sidebar">
        <div className="chat-sidebar-top">
          <div>
            <div className="chat-sidebar-label">Workspace Chat</div>
            <h2>歷史對話</h2>
            <p>切換舊對話、延續問題，或開一個新的聊天視窗。</p>
          </div>
          <button className="chat-new-session" onClick={handleCreateSession}>
            + New Chat
          </button>
        </div>

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
        </div>
      </aside>

      <section className="chat-panel">
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
                    <div className="chat-avatar">{message.role === 'user' ? 'You' : 'AI'}</div>
                    <div className="chat-message-card">
                      <div className="chat-message-role">
                        {message.role === 'user' ? 'You' : 'Assistant'}
                      </div>
                      <p>{message.content}</p>
                    </div>
                  </article>
                ))}

                {loading && (
                  <article className="chat-message-row assistant">
                    <div className="chat-avatar">AI</div>
                    <div className="chat-message-card typing">
                      <div className="chat-message-role">Assistant</div>
                      <p>Thinking about your question...</p>
                    </div>
                  </article>
                )}
              </div>

              <div className="chat-composer">
                <textarea
                  className="chat-composer-input"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="輸入問題，按 Enter 送出，Shift + Enter 換行"
                  rows={4}
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
    </div>
  );
};

export default ChatDB;
export { Chat };
