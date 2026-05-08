import React, { useEffect } from "react";
import { useChatContext } from "../context/ChatContext";
import Chat from "../pages/Chat";
import "../pages/PageIndex.css";

const ChatFloatingWidget: React.FC = () => {
  const { isChatOpen, toggleChat, closeChat } = useChatContext();

  useEffect(() => {
    if (!isChatOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeChat();
    };

    // Prevent background scrolling while drawer is open.
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [isChatOpen, closeChat]);

  return (
    <>
      <button
        className="chat-fab-button"
        onClick={toggleChat}
        aria-label={isChatOpen ? "Close chat" : "Open chat"}
        aria-expanded={isChatOpen}
        type="button"
      >
        {/* Simple chat icon; avoids extra assets/deps. */}
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
          <path
            d="M7.5 18.5L4 20V6C4 4.89543 4.89543 4 6 4H18C19.1046 4 20 4.89543 20 6V14C20 15.1046 19.1046 16 18 16H9.5L7.5 18.5Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      <div
        className={`chat-drawer-overlay ${isChatOpen ? "open" : ""}`}
        onClick={closeChat}
        aria-hidden={!isChatOpen}
      />

      <aside
        className={`chat-drawer ${isChatOpen ? "open" : ""}`}
        aria-hidden={!isChatOpen}
      >
        <header className="chat-drawer-header">
          <div className="chat-drawer-title">
            <span className="chat-drawer-title-label">Workspace Chat</span>
          </div>
          <button
            className="chat-drawer-close"
            onClick={closeChat}
            aria-label="Close chat drawer"
            type="button"
          >
            ×
          </button>
        </header>

        <div className="chat-drawer-body">
          {isChatOpen ? <Chat /> : null}
        </div>
      </aside>
    </>
  );
};

export default ChatFloatingWidget;

