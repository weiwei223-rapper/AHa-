import { useState } from "react";
import { chatAPI } from "../api";
import "./PageIndex.css";

type ChatMessage = {
  role: string;
  content: string;
};

const Chat = () => {
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async () => {
    if (!message.trim()) return;

    const newUserMessage: ChatMessage = { role: "user", content: message.trim() };
    const nextHistory = [...history, newUserMessage];
    setHistory(nextHistory);
    setMessage("");
    setLoading(true);
    setError(null);

    try {
      const response = await chatAPI.sendMessage({
        message: newUserMessage.content,
        history: nextHistory,
      });

      const reply = response.data.reply;
      setHistory((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (err) {
      console.error("Chat API error", err);
      setError("無法連線到聊天服務，請稍後再試。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-shell">
      <div className="chat-header">
        <div className="chat-eyebrow">AI 聊天</div>
        <h1>與學習助手對話</h1>
        <p className="chat-subtitle">輸入你的問題，系統將根據最近影片與聊天紀錄回應。</p>
      </div>

      <div className="chat-messages">
        {history.length === 0 ? (
          <div className="chat-bubble assistant">還沒有訊息，開始問一個問題吧。</div>
        ) : (
          history.map((item, index) => (
            <div
              key={index}
              className={`chat-bubble ${item.role === "assistant" ? "assistant" : "user"}`}
            >
              <div className="chat-role">{item.role === "assistant" ? "Assistant" : "You"}</div>
              <p>{item.content}</p>
            </div>
          ))
        )}
      </div>

      <div className="chat-form">
        <textarea
          className="chat-textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="輸入你的問題..."
          rows={4}
        />
        <button className="chat-send" onClick={handleSend} disabled={loading}>
          {loading ? "傳送中..." : "傳送"}
        </button>
      </div>

      {error && <div className="text-red-400 mt-3">{error}</div>}
    </div>
  );
};

export default Chat;
