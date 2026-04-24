import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";

import { chatAPI } from "../api";
import "./PageIndex.css";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  role: ChatRole;
  content: string;
};

const starterMessage =
  "我是 AHa AI 助手。你可以詢問影片內容、測驗重點，或請我整理學習方向。";

const Chat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: starterMessage },
  ]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSubmit = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();

    const text = draft.trim();
    if (!text || loading) {
      return;
    }

    const userMessage: ChatMessage = { role: "user", content: text };
    const nextMessages = [...messages, userMessage];

    setMessages(nextMessages);
    setDraft("");
    setError("");
    setLoading(true);

    try {
      const response = await chatAPI.sendMessage({
        message: text,
        history: messages,
      });

      setMessages((current) => [
        ...current,
        { role: "assistant", content: response.data.reply as string },
      ]);
    } catch (err) {
      console.error("Failed to send chat message:", err);
      setError("目前無法取得 AI 回覆，請稍後再試。");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  };

  return (
    <div className="main">
      <section className="chat-shell">
        <header className="chat-header">
          <div>
            <p className="chat-eyebrow">Chat</p>
            <h1>AHa AI 助手</h1>
            <p className="chat-subtitle">
              直接提問學習問題，系統會透過後端 AI 服務回覆你。
            </p>
          </div>
        </header>

        <div className="chat-messages">
          {messages.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={`chat-bubble ${message.role === "user" ? "user" : "assistant"}`}
            >
              <span className="chat-role">
                {message.role === "user" ? "You" : "AHa AI"}
              </span>
              <p>{message.content}</p>
            </article>
          ))}

          {loading && (
            <article className="chat-bubble assistant">
              <span className="chat-role">AHa AI</span>
              <p>正在思考中...</p>
            </article>
          )}

          <div ref={messagesEndRef} />
        </div>

        {error && <div className="error">{error}</div>}

        <form className="chat-form" onSubmit={handleSubmit}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="輸入你的問題，按 Enter 送出，Shift + Enter 換行"
            rows={4}
            className="chat-textarea"
          />
          <button type="submit" disabled={loading || !draft.trim()} className="chat-send">
            送出
          </button>
        </form>
      </section>
    </div>
  );
};

export default Chat;
