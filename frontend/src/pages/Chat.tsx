import React, { useEffect, useState } from 'react';
import { chatAPI } from '../api';
import './PageIndex.css';

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
  messages: [
    {
      role: 'assistant',
      content: 'Hello! I am your AI study assistant. Ask about your video content, quiz ideas, or learning notes.'
    }
  ]
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
    if (sessions.length === 0) {
      return;
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  const activeSession =
    sessions.find((session) => session.id === activeSessionId) ?? sessions[0] ?? null;

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

      const reply =
        response.data?.reply ||
        response.data?.message ||
        'The assistant did not return a valid reply.';

      updateSession(activeSession.id, [
        ...nextMessages,
        { role: 'assistant', content: reply },
      ]);
    } catch (requestError) {
      console.error('Error sending message:', requestError);

      updateSession(activeSession.id, [
        ...nextMessages,
        {
          role: 'assistant',
          content: 'Sorry, something went wrong while contacting the chat service.'
        },
      ]);
      setError('無法連線到聊天服務，請稍後再試。');
    } finally {
      setLoading(false);
    }
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
        <div className="chat-hero">
          <div className="chat-hero-copy">
            <div className="chat-hero-label">AI Study Assistant</div>
            <h1>更清楚的聊天工作台</h1>
            <p>
              用側欄管理歷史紀錄，在主畫面專注追問影片內容、測驗重點與學習摘要。
            </p>
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
        </div>
      </section>
    </div>
  );
};

export default Chat;
