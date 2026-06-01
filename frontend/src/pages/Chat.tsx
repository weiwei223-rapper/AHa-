import React, { useEffect, useState, useRef } from 'react';
import { chatAPI, feedbackAPI, videoAPI } from '../api';
import './PageIndex.css';
import ChatDB from './ChatDB';
import ReportModal from '../component/ReportModal';
import { usePoints } from '../context/PointsContext';

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
  selectedDocumentId?: number | null;
  selectedDocumentTitle?: string | null;
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
  selectedDocumentId: null,
  selectedDocumentTitle: null,
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
  const { availablePoints, usePoints: deductPoints } = usePoints();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState('');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [videos, setVideos] = useState<Array<{ id: number; title?: string | null }>>([]);
  const [documents, setDocuments] = useState<Array<{ id: number; title?: string | null }>>([]);
  const [materialsLoading, setMaterialsLoading] = useState(false);
  const [materialsError, setMaterialsError] = useState('');
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
    void fetchMaterials();
  }, []);

  useEffect(() => {
    if (sessions.length === 0) {
      return;
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  const activeSession =
    sessions.find((session) => session.id === activeSessionId) ?? sessions[0] ?? null;

  const fetchMaterials = async () => {
    const userId = Number(localStorage.getItem('userId') || 0);
    if (!userId) {
      setVideos([]);
      setDocuments([]);
      setMaterialsError('請先登入以載入教材列表。');
      return;
    }

    setMaterialsLoading(true);
    setMaterialsError('');
    try {
      const [vRes, dRes] = await Promise.all([
        videoAPI.getVideos(userId),
        import('../api').then(m => m.documentAPI.getDocuments(userId))
      ]);
      setVideos((vRes.data ?? []) as Array<{ id: number; title?: string | null }>);
      setDocuments((dRes.data ?? []) as Array<{ id: number; title?: string | null }>);
    } catch (requestError: unknown) {
      console.error('Error fetching materials:', requestError);
      setMaterialsError('無法載入教材列表');
      setVideos([]);
      setDocuments([]);
    } finally {
      setMaterialsLoading(false);
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
    if (!activeSession.selectedVideoId && !activeSession.selectedDocumentId) return;

    if (availablePoints <= 0) {
      setError('點數不足，請先儲值。');
      return;
    }

    const success = deductPoints(1);
    if (!success) {
      setError('點數不足，請先儲值。');
      return;
    }

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
        document_id: activeSession.selectedDocumentId ?? null,
      });

      let reply =
        response.data?.reply ||
        response.data?.message ||
        'AI Tutor did not return a valid reply.';

      // Validate the reply
      if (!reply || reply.trim().length === 0) {
        reply = '抱歉，AI 服務沒有收到有效的回應。請再試一次。';
      } else if (reply.length > 10000) {
        reply = reply.substring(0, 10000) + '...';
      }

      updateSession(activeSession.id, [
        ...nextMessages,
        { role: 'assistant', content: reply },
      ]);
    } catch (requestError: unknown) {
      console.error('Error sending message:', requestError);

      let errorMessage = '無法連線到 AI 服務，請稍後再試。';
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

  const handleSelectMaterial = (type: 'video' | 'document', id: number) => {
    if (!activeSession) return;
    const list = type === 'video' ? videos : documents;
    const selected = list.find((item) => item.id === id);
    const title = (selected?.title || `Material #${id}`).toString();
    
    const greeting = `你好！我是你的 AI 學習助理。關於這份${type === 'video' ? '影片' : '文件'}「${title}」，你有什麼問題想問嗎？`;
    const greetingMessage: Message = { role: 'assistant', content: greeting };

    setSessions((prev) =>
      prev.map((session) =>
        session.id === activeSession.id
          ? {
            ...session,
            selectedVideoId: type === 'video' ? id : null,
            selectedVideoTitle: type === 'video' ? title : null,
            selectedDocumentId: type === 'document' ? id : null,
            selectedDocumentTitle: type === 'document' ? title : null,
            title: `「${title}」`,
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
        document_id: activeSession?.selectedDocumentId ?? null,
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

          {!activeSession?.selectedVideoId && !activeSession?.selectedDocumentId ? (
            <div className="chat-video-picker">
              <div className="chat-video-picker-head">
                <div className="chat-video-picker-title">請選擇要討論的教材</div>
                <div className="chat-video-picker-subtitle">
                  選定後我會用該教材作為上下文，幫你整理重點、回答問題與延伸學習。
                </div>
              </div>

              {materialsError && <div className="chat-video-picker-error">{materialsError}</div>}

              <div className="chat-video-picker-actions">
                <button
                  className="chat-video-picker-refresh"
                  onClick={() => void fetchMaterials()}
                  disabled={materialsLoading}
                  type="button"
                >
                  {materialsLoading ? '載入中...' : '重新載入教材'}
                </button>
              </div>

              <div className="chat-video-picker-list" role="list">
                {!materialsLoading && videos.length === 0 && documents.length === 0 ? (
                  <div className="chat-video-picker-empty">
                    目前沒有可用教材。請先到 Material 頁上傳影片或 PDF 後再回來。
                  </div>
                ) : (
                  <>
                    {videos.length > 0 && <div className="chat-picker-section-label">影片教材 (Videos)</div>}
                    {videos.map((video) => (
                      <button
                        key={`v-${video.id}`}
                        className="chat-video-card video"
                        onClick={() => handleSelectMaterial('video', video.id)}
                        type="button"
                        role="listitem"
                      >
                        <div className="chat-video-card-title">{video.title || `Video #${video.id}`}</div>
                        <div className="chat-video-card-meta">ID: {video.id}</div>
                      </button>
                    ))}
                    {documents.length > 0 && <div className="chat-picker-section-label" style={{marginTop: '20px'}}>PDF 教材 (Documents)</div>}
                    {documents.map((doc) => (
                      <button
                        key={`d-${doc.id}`}
                        className="chat-video-card doc"
                        onClick={() => handleSelectMaterial('document', doc.id)}
                        type="button"
                        role="listitem"
                      >
                        <div className="chat-video-card-title">{doc.title || `Document #${doc.id}`}</div>
                        <div className="chat-video-card-meta">ID: {doc.id}</div>
                      </button>
                    ))}
                  </>
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
                    <div className="chat-avatar">{message.role === 'user' ? 'You' : 'AI Tutor'}</div>
                    <div className="chat-message-card">
                      <div className="chat-message-role">
                        {message.role === 'user' ? 'You' : 'AI Tutor'}
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
                    <div className="chat-avatar">AI Tutor</div>
                    <div className="chat-message-card typing">
                      <div className="chat-message-role">AI Tutor</div>
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
                    可以詢問教材內容整理、重點摘要、題目解析或延伸學習方向。
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
