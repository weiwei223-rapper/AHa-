import React, { useEffect, useMemo, useState, useRef } from 'react';
import { chatAPI, feedbackAPI, videoAPI } from '../api';
import './PageIndex.css';
import ReportModal from '../component/ReportModal';

type MessageRole = 'user' | 'assistant';

type Message = {
  role: MessageRole;
  content: string;
};

type Video = {
  id: number;
  title?: string | null;
};

type ChatSession = {
  id: string; // conversation id (frontend token)
  title: string;
  updatedAt: string;
  messages: Message[];
  selectedVideoId?: number | null;
  selectedVideoTitle?: string | null;
  isPersisted: boolean; // backed by ai_feedback rows
};

const CHAT_ERROR_REPORT_PREFIX = 'chat-session:';

const createConversationId = () => `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const formatUpdatedAt = (value: string) => {
  try {
    return new Intl.DateTimeFormat('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return value;
  }
};

const extractConversationIdFromErrorReport = (errorReport: string | null | undefined): string | null => {
  if (!errorReport) return null;
  if (!errorReport.startsWith(CHAT_ERROR_REPORT_PREFIX)) return null;
  return errorReport.slice(CHAT_ERROR_REPORT_PREFIX.length);
};

const extractVideoTitleFromGreeting = (assistantMessage: string): string | null => {
  // Expected: 關於「{videoTitle}」
  const match = assistantMessage.match(/關於「(.+?)」/);
  return match?.[1] ?? null;
};

const buildGreeting = (videoTitle: string) =>
  `你好！我是你的 AI 學習助理。關於「${videoTitle}」，你有什麼問題想問嗎？`;

const ChatDB: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>('');

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [videos, setVideos] = useState<Video[]>([]);
  const [videosLoading, setVideosLoading] = useState(false);
  const [videosError, setVideosError] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Modal State
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportingMessage, setReportingMessage] = useState<Message | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const userId = Number(localStorage.getItem('userId') || 0);

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

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) ?? sessions[0] ?? null,
    [sessions, activeSessionId]
  );

  const fetchVideos = async () => {
    if (!userId) {
      setVideos([]);
      setVideosError('請先登入以載入教材列表。');
      return [];
    }

    setVideosLoading(true);
    setVideosError('');
    try {
      const response = await videoAPI.getVideos(userId);
      const nextVideos = (response.data ?? []) as Video[];
      setVideos(nextVideos);
      return nextVideos;
    } catch (requestError: unknown) {
      console.error('Error fetching videos:', requestError);
      const errorObject = requestError as { response?: { data?: { detail?: string } } };
      setVideosError(errorObject.response?.data?.detail || '無法載入教材列表');
      setVideos([]);
      return [];
    } finally {
      setVideosLoading(false);
    }
  };

  const fetchConversationsFromAIFeedback = async (videoList: Video[] = videos) => {
    if (!userId) {
      setSessions([]);
      setActiveSessionId('');
      return;
    }

    try {
      const response = await feedbackAPI.getFeedbacks();
      const allFeedbacks = (response.data ?? []) as Array<{
        id: number;
        user_id: number;
        video_id?: number | null;
        ai_message: string;
        user_message: string;
        error_report: string | null;
        created_at: string;
      }>;

      const myFeedbacks = allFeedbacks
        .filter((f) => f.user_id === userId)
        .filter((f) => extractConversationIdFromErrorReport(f.error_report) !== null);

      const groups = new Map<string, typeof myFeedbacks>();

      for (const f of myFeedbacks) {
        const conversationId = extractConversationIdFromErrorReport(f.error_report);
        if (!conversationId) continue;
        const prev = groups.get(conversationId) ?? [];
        prev.push(f);
        groups.set(conversationId, prev);
      }

      const nextSessions: ChatSession[] = Array.from(groups.entries()).map(([conversationId, items]) => {
        const sorted = [...items].sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));

        const messages: Message[] = [];
        let title = 'New conversation';
        let selectedVideoTitle: string | null = null;
        let selectedVideoId: number | null = sorted.find((item) => item.video_id)?.video_id ?? null;

        for (const item of sorted) {
          if (item.user_message && item.user_message.trim()) {
            messages.push({ role: 'user', content: item.user_message });
          }

          if (item.ai_message && item.ai_message.trim()) {
            messages.push({ role: 'assistant', content: item.ai_message });

            // Derive title from greeting if present.
            const maybeVideoTitle = extractVideoTitleFromGreeting(item.ai_message);
            if (maybeVideoTitle && !selectedVideoTitle) {
              selectedVideoTitle = maybeVideoTitle;
              title = maybeVideoTitle;
            }
          }
        }

        if (selectedVideoId) {
          const selectedVideo = videoList.find((video) => video.id === selectedVideoId);
          if (selectedVideo?.title) {
            selectedVideoTitle = selectedVideo.title;
            title = selectedVideo.title;
          }
        } else if (selectedVideoTitle) {
          const matchedVideo = videoList.find((video) => video.title === selectedVideoTitle);
          if (matchedVideo) {
            selectedVideoId = matchedVideo.id;
          }
        }

        const updatedAt = sorted.reduce((max, cur) => (Date.parse(cur.created_at) > Date.parse(max) ? cur.created_at : max), sorted[0]?.created_at ?? new Date().toISOString());

        return {
          id: conversationId,
          title,
          updatedAt,
          messages,
          selectedVideoTitle,
          selectedVideoId,
          isPersisted: true,
        };
      });

      nextSessions.sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));

      // If no persisted conversations, still show a fresh "New Chat" experience.
      if (nextSessions.length === 0) {
        const newEphemeral = {
          id: createConversationId(),
          title: 'New conversation',
          updatedAt: new Date().toISOString(),
          messages: [],
          selectedVideoTitle: null,
          selectedVideoId: null,
          isPersisted: false,
        };
        setSessions([newEphemeral]);
        setActiveSessionId(newEphemeral.id);
        return;
      }

      setSessions(nextSessions);
      setActiveSessionId(nextSessions[0].id);
    } catch (requestError: unknown) {
      console.error('Error fetching conversations:', requestError);
      setSessions([]);
      setActiveSessionId('');
    }
  };

  useEffect(() => {
    const initChat = async () => {
      const nextVideos = await fetchVideos();
      await fetchConversationsFromAIFeedback(nextVideos);
    };
    void initChat();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isConversationInitialized = (activeSession?.messages.length ?? 0) > 0;

  const handleCreateSession = () => {
    const newSession: ChatSession = {
      id: createConversationId(),
      title: 'New conversation',
      updatedAt: new Date().toISOString(),
      messages: [],
      selectedVideoId: null,
      selectedVideoTitle: null,
      isPersisted: false,
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    setInput('');
    setError('');
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSessionId(sessionId);
    setInput('');
    setError('');
  };

  const handleSelectVideo = async (videoId: number) => {
    if (!activeSession) return;
    const selected = videos.find((v) => v.id === videoId);
    const videoTitle = (selected?.title || `Video #${videoId}`).toString();
    const greeting = buildGreeting(videoTitle);
    const token = `${CHAT_ERROR_REPORT_PREFIX}${activeSession.id}`;

    // Optimistic update: show chat immediately.
    const greetingMessage: Message = { role: 'assistant', content: greeting };
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              title: videoTitle,
              selectedVideoId: videoId,
              selectedVideoTitle: videoTitle,
              updatedAt: new Date().toISOString(),
              messages: s.messages.length === 0 ? [greetingMessage] : s.messages,
              isPersisted: true,
            }
          : s
      )
    );

    setError('');
    try {
      if (!userId) throw new Error('Not logged in');
      await feedbackAPI.createFeedback({
        user_id: userId,
        video_id: videoId,
        ai_message: greeting,
        user_message: '',
        error_report: token,
      });
      // Keep local state consistent with DB ordering/updatedAt.
      await fetchConversationsFromAIFeedback();
    } catch (requestError: unknown) {
      console.error('Error persisting greeting:', requestError);
      setError('無法儲存聊天初始化，請稍後再試。');
    }
  };

  const handleSend = async () => {
    if (!activeSession || !input.trim() || loading) return;
    if (!isConversationInitialized) return;

    if (!userId) {
      setError('請先登入');
      return;
    }

    if (!activeSession.selectedVideoId) {
      setError('這個聊天尚未綁定教材，請開新聊天並選擇教材後再提問。');
      return;
    }

    const trimmedInput = input.trim();
    const token = `${CHAT_ERROR_REPORT_PREFIX}${activeSession.id}`;

    const userMessage: Message = { role: 'user', content: trimmedInput };
    const nextMessages = [...activeSession.messages, userMessage];

    // optimistic UI update for user message
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSession.id
          ? {
              ...s,
              updatedAt: new Date().toISOString(),
              messages: nextMessages,
            }
          : s
      )
    );

    setInput('');
    setLoading(true);
    setError('');

    try {
      const response = await chatAPI.sendMessage({
        message: trimmedInput,
        history: nextMessages,
        user_id: userId,
        video_id: activeSession.selectedVideoId ?? null,
      });

      let reply =
        response.data?.reply ||
        response.data?.message ||
        'The assistant did not return a valid reply.';

      if (!reply || reply.trim().length === 0) {
        reply = '抱歉，我沒有收到有效的回應。請再試一次。';
      } else if (reply.length > 10000) {
        reply = reply.substring(0, 10000) + '...';
      }

      const assistantMessage: Message = { role: 'assistant', content: reply };
      const persistedHistory = [...nextMessages, assistantMessage];

      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSession.id
            ? {
                ...s,
                updatedAt: new Date().toISOString(),
                messages: persistedHistory,
              }
            : s
        )
      );

      await feedbackAPI.createFeedback({
        user_id: userId,
        video_id: activeSession.selectedVideoId ?? null,
        ai_message: reply,
        user_message: trimmedInput,
        error_report: token,
      });
      // Optional: refresh to keep ordering accurate.
      await fetchConversationsFromAIFeedback();
    } catch (requestError: unknown) {
      console.error('Error sending message:', requestError);

      let errorMessage = '無法連線到聊天服務，請稍後再試。';
      const errorObject = requestError as { code?: string; response?: { status?: number } };
      if (errorObject.code === 'ECONNABORTED') {
        errorMessage = '請求超時，請檢查網路連線後再試。';
      } else if (errorObject.response?.status === 500) {
        errorMessage = '伺服器內部錯誤，請稍後再試。';
      }

      setError(errorMessage);
      const assistantMessage: Message = { role: 'assistant', content: errorMessage };
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSession.id ? { ...s, updatedAt: new Date().toISOString(), messages: [...s.messages, assistantMessage] } : s
        )
      );
      // Save error reply too (still under the conversation token).
      await feedbackAPI.createFeedback({
        user_id: userId,
        video_id: activeSession.selectedVideoId ?? null,
        ai_message: errorMessage,
        user_message: trimmedInput,
        error_report: token,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleReportError = (message: Message) => {
    setReportingMessage(message);
    setIsReportModalOpen(true);
  };

  const handleModalSubmit = async (errorDesc: string) => {
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
      void handleSend();
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    if (!userId) return;
    const ok = window.confirm('確定要刪除這個聊天嗎？刪除後無法復原。');
    if (!ok) return;

    try {
      await feedbackAPI.deleteConversation(conversationId, userId);
      await fetchConversationsFromAIFeedback();
      setActiveSessionId((prev) => (prev === conversationId ? '' : prev));
      setInput('');
      setError('');
    } catch (requestError: unknown) {
      console.error('Error deleting conversation:', requestError);
      setError('刪除失敗，請稍後再試。');
    }
  };

  return (
    <div className="chat-page">
      <div className="chat-unified-scroll">
        <aside className={`chat-sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}>
          <div className="chat-sidebar-top">
            <div>
              <div className="chat-sidebar-label">Workspace Chat</div>
              <h2>歷史對話</h2>
            </div>
            <div className="chat-sidebar-actions">
              <button className="chat-new-session" onClick={handleCreateSession} type="button">
                + New Chat
              </button>
              <button
                className="chat-sidebar-toggle"
                onClick={() => setIsSidebarCollapsed((prev) => !prev)}
                type="button"
                aria-expanded={!isSidebarCollapsed}
                aria-controls="chat-history-list"
              >
                {isSidebarCollapsed ? '展開歷史' : '收合歷史'}
              </button>
            </div>
          </div>

          <div id="chat-history-list" className="chat-history-list">
            {sessions.map((session) => {
              const isActive = session.id === activeSession?.id;
              const lastMessage = session.messages[session.messages.length - 1]?.content;
              return (
                <div key={session.id} className={`chat-history-item ${isActive ? 'active' : ''}`}>
                  <button
                    className="chat-history-card"
                    onClick={() => handleSelectSession(session.id)}
                    type="button"
                  >
                    <span className="chat-history-title">{session.title}</span>
                    <span className="chat-history-preview">{lastMessage || '請先選擇教材'}</span>
                    <span className="chat-history-time">{formatUpdatedAt(session.updatedAt)}</span>
                  </button>
                  {session.isPersisted ? (
                    <button
                      className="chat-history-delete"
                      aria-label="Delete chat"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        void handleDeleteConversation(session.id);
                      }}
                      type="button"
                    >
                      ×
                    </button>
                  ) : null}
                </div>
              );
            })}
          </div>
        </aside>

        <section className="chat-panel">
          <div className="chat-thread-shell">
          <div className="chat-thread-header">
            <div>
              <div className="chat-thread-eyebrow">Current Session</div>
              <h3>{activeSession?.title || 'New conversation'}</h3>
              {activeSession?.selectedVideoTitle ? (
                <div className="chat-session-source">
                  <span>教材</span>
                  <strong>{activeSession.selectedVideoTitle}</strong>
                  {activeSession.selectedVideoId ? <em>#{activeSession.selectedVideoId}</em> : null}
                </div>
              ) : null}
            </div>
            <div className="chat-thread-meta">
              {activeSession ? (
                <>
                  <span>{activeSession.messages.length} messages</span>
                  <span>Updated {formatUpdatedAt(activeSession.updatedAt)}</span>
                </>
              ) : null}
            </div>
          </div>

          {!isConversationInitialized ? (
            <div className="chat-video-picker">
              <div className="chat-video-picker-head">
                <div className="chat-video-picker-title">請選擇要討論的教材</div>
                <div className="chat-video-picker-subtitle">
                  選定後我會用該教材作為上下文，幫你整理重點、回答問題與延伸學習。
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
                  {videosLoading ? '載入中...' : '重新載入教材'}
                </button>
              </div>

              <div className="chat-video-picker-list" role="list">
                {!videosLoading && videos.length === 0 ? (
                  <div className="chat-video-picker-empty">
                    目前沒有可用教材。請先到 Material 頁上傳教材後再回來。
                  </div>
                ) : (
                  videos.map((video) => (
                    <button
                      key={video.id}
                      className="chat-video-card"
                      onClick={() => void handleSelectVideo(video.id)}
                      type="button"
                      role="listitem"
                    >
                      <div className="chat-video-card-title">{video.title || `Material #${video.id}`}</div>
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
                    <div className="chat-avatar">AI</div>
                    <div className="chat-message-card typing">
                      <div className="chat-message-role">Assistant</div>
                      <p>正在依照教材與題目整理回答...</p>
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
                    可以詢問教材內容整理、重點摘要、題目解析或延伸學習方向。
                  </div>
                  <button className="chat-send-button" onClick={() => void handleSend()} disabled={loading || !input.trim()}>
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

export default ChatDB;
