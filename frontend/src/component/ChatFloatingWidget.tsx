import React, { useEffect, useState, useRef } from "react";
import { useChatContext } from "../context/ChatContext";
import Chat from "../pages/Chat";
import "../pages/PageIndex.css";

const STORAGE_POS_KEY = "aha-chat-button-pos";

const ChatFloatingWidget: React.FC = () => {
  const { isChatOpen, toggleChat, closeChat } = useChatContext();
  
  // 1. 從 localStorage 讀取先前儲存的位置，若無則預設右下角 30, 30
  const [position, setPosition] = useState(() => {
    const saved = localStorage.getItem(STORAGE_POS_KEY);
    return saved ? JSON.parse(saved) : { x: 30, y: 30 };
  });

  const [isDragging, setIsDragging] = useState(false);
  const dragStartPos = useRef({ mouseX: 0, mouseY: 0, startX: 0, startY: 0 });
  const moved = useRef(false);

  useEffect(() => {
    if (!isChatOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeChat();
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [isChatOpen, closeChat]);

  // 處理拖動開始
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    moved.current = false;
    dragStartPos.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      startX: position.x,
      startY: position.y
    };
  };

  // 處理拖動中
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      
      const deltaX = dragStartPos.current.mouseX - e.clientX;
      const deltaY = dragStartPos.current.mouseY - e.clientY;
      
      // 判定是否真的有移動 (避免微小手抖誤判為拖動)
      if (Math.abs(deltaX) > 3 || Math.abs(deltaY) > 3) {
        moved.current = true;
      }

      // 計算新位置並限制在螢幕範圍內 (扣除按鈕寬高 60px)
      const newX = Math.max(0, Math.min(window.innerWidth - 60, dragStartPos.current.startX + deltaX));
      const newY = Math.max(0, Math.min(window.innerHeight - 60, dragStartPos.current.startY + deltaY));
      
      const newPos = { x: newX, y: newY };
      setPosition(newPos);
    };

    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false);
        // 拖動結束，儲存位置到 localStorage
        localStorage.setItem(STORAGE_POS_KEY, JSON.stringify(position));
      }
    };

    if (isDragging) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, position]);

  const handleClick = (e: React.MouseEvent) => {
    // 如果發生了拖動，則阻止觸發 click 事件 (避免放開時視窗彈出)
    if (moved.current) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    toggleChat();
  };

  return (
    <>
      <button
        className="chat-fab-button"
        onMouseDown={handleMouseDown}
        onClick={handleClick}
        style={{
          bottom: `${position.y}px`,
          right: `${position.x}px`,
          position: "fixed",
          cursor: isDragging ? "grabbing" : "grab",
          transition: isDragging ? "none" : "all 0.15s cubic-bezier(0.2, 0, 0, 1)",
          zIndex: 10000,
          touchAction: "none" // 優化移動端體驗
        }}
        aria-label={isChatOpen ? "Close chat" : "Open chat"}
        aria-expanded={isChatOpen}
        type="button"
      >
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
