import { useState, useRef, useEffect, useCallback } from "react";
import api from "./api";

// Namespace declaration for JSX (React 17+ compatibility)
declare namespace JSX {
  type Element = React.ReactElement<any, any>;
}

/* ─── THEME TOKENS ─── */
const T = {
  bg: "#080c16",
  surface: "#0f1623",
  surface2: "#161f30",
  border: "#1c2d45",
  accent: "#00d4ff",
  accent2: "#7c3aed",
  accent3: "#10b981",
  danger: "#ef4444",
  gold: "#f59e0b",
  text: "#e2e8f0",
  text2: "#7a90a8",
  text3: "#3a4a5c",
};

/* ─── GLOBAL STYLES ─── */
const globalCSS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: ${T.bg}; color: ${T.text}; font-family: 'Noto Sans TC', sans-serif; overflow-x: hidden; }
  body::before {
    content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image: linear-gradient(rgba(0,212,255,0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,255,0.025) 1px, transparent 1px);
    background-size: 48px 48px;
  }
  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: ${T.border}; border-radius: 2px; }
  select { appearance: none; }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-10px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.92); }
    to   { opacity: 1; transform: scale(1); }
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
  }
  @keyframes spin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
  .anim-fadeUp   { animation: fadeUp   0.35s ease both; }
  .anim-scaleIn  { animation: scaleIn  0.25s ease both; }
  .anim-slideDown{ animation: slideDown 0.2s ease both; }
`;

/* ─── TINY UTILS ─── */
const mono = { fontFamily: "'JetBrains Mono', monospace" };
const glow  = (c = T.accent) => `0 0 20px ${c}44`;

function cx(...args: (string | undefined | boolean)[]): string {
  return args.filter(Boolean).join(" ");
}

const ACCOUNTS_KEY = 'aha_accounts';
const SESSION_KEY  = 'aha_session';
const TOKEN_KEY = 'aha_auth_token';

function loadAccounts(): Record<string, any> {
  try { return JSON.parse(localStorage.getItem(ACCOUNTS_KEY) || '{}'); } catch { return {}; }
}
function saveAccounts(a: any): void { localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(a)); }
function loadSession(): any {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); } catch { return null; }
}
function saveSession(u: any): void { localStorage.setItem(SESSION_KEY, JSON.stringify(u)); }
function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(TOKEN_KEY);
}

function loadVideos(): any[] {
  // For demo, return default data; in real app, fetch from API
  return [
    { name: "Python 基礎語法入門",      recognized: true,  outline: true,  pts: "-50", date: "2026/03/20" },
    { name: "資料結構 - 陣列與串列",    recognized: true,  outline: true,  pts: "-50", date: "2026/03/18" },
    { name: "演算法 - 排序方法比較",    recognized: false, outline: false, pts: "-50", date: "2026/03/24" },
  ];
}

function loadQuizzes() {
  // For demo, return default data; in real app, fetch from API
  return [
    {
      name: "Python 變數與資料型別",
      source: "Python 基礎語法入門",
      questions: [
        { q: "下列哪個關鍵字用於在 Python 中定義一個函式？", opts: ["function", "void", "def", "lambda"], ans: 2 },
        { q: "Python 中用來迭代一個序列的關鍵字是？", opts: ["loop", "for", "each", "iterate"], ans: 1 },
        { q: "以下何者是 Python 的字典型別？", opts: ["[1,2,3]", "(1,2,3)", "{1,2,3}", "{'a':1}"], ans: 3 },
        { q: "Python 中 `len()` 函式的用途為何？", opts: ["計算最大值", "回傳元素數量", "排列序列", "刪除元素"], ans: 1 },
        { q: "下列哪個不是 Python 的基本資料型別？", opts: ["int", "float", "char", "bool"], ans: 2 },
      ],
      lastRate: "90%", rateColor: T.accent3, done: true,
    },
    {
      name: "迴圈與條件判斷",
      source: "Python 基礎語法入門",
      questions: [
        { q: "Python 中 `while` 迴圈的終止條件通常是？", opts: ["條件為 True", "條件為 False", "使用 break", "計數歸零"], ans: 1 },
        { q: "`if-elif-else` 結構中，`elif` 代表什麼？", opts: ["否則如果", "else if 的縮寫", "額外條件", "以上皆是"], ans: 3 },
        { q: "以下哪個關鍵字可以跳出迴圈？", opts: ["skip", "exit", "break", "stop"], ans: 2 },
        { q: "`continue` 關鍵字的作用是？", opts: ["終止程式", "跳過本次迭代", "退出迴圈", "重啟迴圈"], ans: 1 },
        { q: "Python 的 `range(3)` 會產生哪些數值？", opts: ["1,2,3", "0,1,2,3", "0,1,2", "1,2"], ans: 2 },
      ],
      lastRate: "73%", rateColor: T.gold, done: true,
    },
  ];
}

/* ══════════════════════════════════════════
   SHARED UI ATOMS
══════════════════════════════════════════ */

function Tag({ children, color = "blue" }: { children: React.ReactNode; color?: string }): JSX.Element {
  const palettes: Record<string, { bg: string; color: string }> = {
    blue:   { bg: "rgba(0,212,255,0.12)",   color: T.accent },
    green:  { bg: "rgba(16,185,129,0.12)",  color: T.accent3 },
    purple: { bg: "rgba(124,58,237,0.12)",  color: "#a78bfa" },
    gold:   { bg: "rgba(245,158,11,0.12)",  color: T.gold },
    muted:  { bg: "rgba(74,85,104,0.2)",    color: T.text3 },
    red:    { bg: "rgba(239,68,68,0.12)",   color: T.danger },
  };
  const p = palettes[color as keyof typeof palettes] || palettes.blue;
  return (
    <span style={{
      display: "inline-block", padding: "3px 10px", borderRadius: 20,
      fontSize: "0.7rem", fontWeight: 700,
      background: p.bg, color: p.color,
      border: `1px solid ${p.color}33`,
    }}>{children}</span>
  );
}

function Btn({ children, onClick = () => {}, variant = "ghost", style: s, disabled = false }: { children: React.ReactNode; onClick?: () => void; variant?: string; style?: React.CSSProperties; disabled?: boolean }): JSX.Element {
  const [hov, setHov] = useState(false);
  const base = {
    padding: "9px 18px", borderRadius: 9, cursor: disabled ? "not-allowed" : "pointer",
    fontFamily: "inherit", fontSize: "0.84rem", fontWeight: 500,
    border: "none", transition: "all 0.18s", outline: "none",
    opacity: disabled ? 0.5 : 1,
  };
  const variants: Record<string, React.CSSProperties> = {
    ghost:   { background: hov ? T.surface2 : "transparent", color: hov ? T.text : T.text2, border: `1px solid ${T.border}` },
    primary: { background: hov ? T.accent : "rgba(0,212,255,0.12)", color: T.accent, border: `1px solid ${T.accent}`, boxShadow: hov ? glow() : "none" },
    solid:   { background: `linear-gradient(135deg,${T.accent},#009dbb)`, color: T.bg, fontWeight: 700, boxShadow: hov ? glow() : "none", transform: hov ? "translateY(-1px)" : "none" },
    danger:  { background: T.danger, color: "#fff", fontWeight: 700, boxShadow: hov ? glow(T.danger) : "none" },
  };
  return (
    <button
      style={{ ...base, ...variants[variant as keyof typeof variants], ...s }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      onClick={onClick}
      disabled={disabled}
    >{children}</button>
  );
}

function Input({ label, type = "text", placeholder, value, onChange, style: s }: { label?: string; type?: string; placeholder?: string; value: string; onChange: (e: React.ChangeEvent<HTMLInputElement>) => void; style?: React.CSSProperties }): JSX.Element {
  const [focus, setFocus] = useState(false);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, ...s }}>
      {label && <label style={{ fontSize: "0.72rem", color: T.text2, letterSpacing: "1px", textTransform: "uppercase" }}>{label}</label>}
      <input
        type={type} placeholder={placeholder} value={value} onChange={onChange}
        onFocus={() => setFocus(true)} onBlur={() => setFocus(false)}
        style={{
          padding: "12px 16px", background: T.bg,
          border: `1px solid ${focus ? T.accent : T.border}`,
          borderRadius: 9, color: T.text, fontFamily: "inherit", fontSize: "0.92rem",
          outline: "none", boxShadow: focus ? `0 0 0 3px ${T.accent}18` : "none",
          transition: "border-color 0.2s, box-shadow 0.2s",
        }}
      />
    </div>
  );
}

function Card({ children, onClick, style: s, className }: { children: React.ReactNode; onClick?: () => void; style?: React.CSSProperties; className?: string }): JSX.Element {
  const [hov, setHov] = useState(false);
  return (
    <div
      className={cx("anim-fadeUp", className)}
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: T.surface, border: `1px solid ${hov && onClick ? T.accent : T.border}`,
        borderRadius: 14, padding: 24, position: "relative", overflow: "hidden",
        cursor: onClick ? "pointer" : "default",
        transform: hov && onClick ? "translateY(-4px)" : "none",
        boxShadow: hov && onClick ? `0 14px 40px rgba(0,0,0,0.5), ${glow()}` : "none",
        transition: "all 0.22s ease",
        ...s,
      }}
    >
      {hov && onClick && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, height: 3,
          background: `linear-gradient(90deg,${T.accent},${T.accent2})`,
        }} />
      )}
      {children}
    </div>
  );
}

function StatCard({ num, label }: { num: string; label: string }): JSX.Element {
  return (
    <div className="anim-fadeUp" style={{
      background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: 12, padding: "20px 16px", textAlign: "center",
    }}>
      <div style={{ ...mono, fontSize: "2rem", fontWeight: 700,
        background: `linear-gradient(135deg,${T.accent},${T.accent2})`,
        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>{num}</div>
      <div style={{ fontSize: "0.75rem", color: T.text2, marginTop: 4 }}>{label}</div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <h2 style={{ fontSize: "1.55rem", fontWeight: 800, letterSpacing: "-0.5px", marginBottom: 6 }}>
      {children}
    </h2>
  );
}

function BackBtn({ onClick }: { onClick: () => void }): JSX.Element {
  return <Btn onClick={onClick} variant="ghost" style={{ fontSize: "0.8rem" }} disabled={false}>← 返回</Btn>;
}

function DataTable({ cols, rows }: { cols: string[]; rows: JSX.Element[] }): JSX.Element {
  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 14, overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
        <thead>
          <tr style={{ background: T.surface2 }}>
            {cols.map((c: string) => (
              <th key={c} style={{ padding: "12px 16px", textAlign: "left", color: T.text2, fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "1px", fontWeight: 600, borderBottom: `1px solid ${T.border}` }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  );
}

function TR({ cells }: { cells: JSX.Element[] }): JSX.Element {
  const [hov, setHov] = useState(false);
  return (
    <tr
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ background: hov ? "rgba(0,212,255,0.025)" : "transparent" }}
    >
      {cells.map((c: JSX.Element, i: number) => (
        <td key={i} style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}44`, verticalAlign: "middle" }}>{c}</td>
      ))}
    </tr>
  );
}

/* ══════════════════════════════════════════
   TOAST
══════════════════════════════════════════ */
function Toast({ message, visible }: { message: string; visible: boolean }): JSX.Element {
  return (
    <div style={{
      position: "fixed", bottom: 96, right: 24, zIndex: 900,
      background: T.surface, border: `1px solid ${T.accent3}`,
      borderRadius: 11, padding: "14px 20px",
      boxShadow: `0 8px 32px rgba(0,0,0,0.5)`,
      display: "flex", alignItems: "center", gap: 10,
      fontSize: "0.86rem",
      transform: visible ? "translateY(0)" : "translateY(24px)",
      opacity: visible ? 1 : 0,
      transition: "all 0.3s ease",
      pointerEvents: "none",
    }}>
      <span style={{ color: T.accent3, fontSize: "1rem" }}>✅</span>
      {message}
    </div>
  );
}

function useToast(): [{ msg: string; visible: boolean }, (msg: string) => void] {
  const [state, setState] = useState({ msg: "", visible: false });
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const show = useCallback((msg: string) => {
    setState({ msg, visible: true });
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setState(s => ({ ...s, visible: false })), 2400);
  }, []);
  return [state, show];
}

/* ══════════════════════════════════════════
   MODAL
══════════════════════════════════════════ */
function Modal({ open, onClose, title, children, footer }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode; footer?: JSX.Element[] }): JSX.Element | null {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    if (open) window.addEventListener("keydown", h as EventListener);
    return () => window.removeEventListener("keydown", h as EventListener);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 1000,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 24, backdropFilter: "blur(6px)", animation: "fadeIn 0.2s ease",
      }}
    >
      <div className="anim-scaleIn" style={{
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: 16, padding: 32, width: "100%", maxWidth: 480,
        boxShadow: "0 32px 80px rgba(0,0,0,0.7)",
      }}>
        <div style={{ display: "flex", alignItems: "center", marginBottom: 22, fontSize: "1.15rem", fontWeight: 700 }}>
          {title}
          <button onClick={onClose} style={{ marginLeft: "auto", background: "none", border: "none", color: T.text2, cursor: "pointer", fontSize: "1.5rem", lineHeight: 1, padding: "0 4px" }}>×</button>
        </div>
        {children}
        {footer && <div style={{ display: "flex", gap: 10, marginTop: 18, justifyContent: "flex-end" }}>{footer}</div>}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════
   FAB
══════════════════════════════════════════ */
function FAB({ onClick }: { onClick: () => void }): JSX.Element {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        position: "fixed", right: 24, bottom: 24, zIndex: 700,
        width: 54, height: 54, borderRadius: "50%",
        background: `linear-gradient(135deg,${T.danger},#c2185b)`,
        border: "none", cursor: "pointer",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "1.35rem",
        boxShadow: hov ? `0 12px 32px ${T.danger}88` : `0 6px 20px ${T.danger}55`,
        transform: hov ? "scale(1.12) rotate(8deg)" : "scale(1)",
        transition: "all 0.2s ease",
      }}
      title="錯誤回報"
    >🚨</button>
  );
}

/* ══════════════════════════════════════════
   AUTH PAGE
══════════════════════════════════════════ */
function AuthPage({ onLogin, showToast }: { onLogin: (user: any) => void; showToast: (msg: string) => void }): JSX.Element {
  const [tab, setTab] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [message, setMessage] = useState("");

  const validateEmail = (v: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);

  const handleLogin = async () => {
    if (!email || !pw) { setMessage("請輸入電子信箱與密碼。"); return; }
    try {
      const response = await api.post('/auth/login', { email, password: pw });
      localStorage.setItem(TOKEN_KEY, response.data.token);
      saveSession(response.data.user);
      showToast("✅ 登入成功");
      onLogin(response.data.user);
      return;
    } catch {
      // Fallback to local account for offline/demo mode
      const accounts = loadAccounts();
      if (!accounts[email]) { setMessage("此電子信箱尚未註冊。"); return; }
      if (accounts[email].password !== pw) { setMessage("密碼不正確。"); return; }
      const user = { email, name: accounts[email].name };
      saveSession(user);
      showToast("✅ 登入成功（本地模式）");
      onLogin(user);
    }
  };

  const handleRegister = async () => {
    if (!name || !email || !pw || !pw2) { setMessage("請填寫所有欄位。"); return; }
    if (!validateEmail(email)) { setMessage("請輸入有效的電子信箱格式。"); return; }
    if (pw.length < 8) { setMessage("密碼至少 8 個字元。"); return; }
    if (pw !== pw2) { setMessage("兩次密碼不一致。"); return; }
    try {
      const response = await api.post('/auth/register', { name, email, password: pw });
      localStorage.setItem(TOKEN_KEY, response.data.token);
      saveSession(response.data.user);
      showToast("✅ 註冊成功");
      onLogin(response.data.user);
      return;
    } catch {
      // Fallback to local account for offline/demo mode
      const accounts = loadAccounts();
      if (accounts[email]) { setMessage("此電子信箱已註冊。"); return; }
      accounts[email] = { name, password: pw };
      saveAccounts(accounts);
      const user = { email, name };
      saveSession(user);
      showToast("✅ 註冊成功（本地模式）");
      onLogin(user);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 24, position: "relative", zIndex: 1 }}>
      <div className="anim-fadeUp" style={{ textAlign: "center", marginBottom: 40 }}>
        <div style={{ ...mono, fontSize: "2.8rem", fontWeight: 700,
          background: `linear-gradient(135deg,${T.accent},${T.accent2})`,
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", letterSpacing: "-1px" }}>
          AHa!! 🤖
        </div>
        <div style={{ fontSize: "0.85rem", color: T.text2, marginTop: 7, letterSpacing: "3px" }}>AI 程式家教平台</div>
      </div>

      <div className="anim-fadeUp" style={{ display: "flex", borderRadius: "12px 12px 0 0", overflow: "hidden", width: "100%", maxWidth: 420 }}>
        {["login", "register"].map(t => (
          <button key={t} onClick={() => { setTab(t); setMessage(""); }} style={{
            flex: 1, padding: "14px 0", cursor: "pointer",
            fontFamily: "inherit", fontSize: "0.92rem", fontWeight: 500, border: "none",
            background: tab === t ? T.surface : T.surface2,
            color: tab === t ? T.accent : T.text2,
            borderBottom: tab === t ? `2px solid ${T.accent}` : "2px solid transparent",
            transition: "all 0.18s",
          }}>{t === "login" ? "登入" : "註冊"}</button>
        ))}
      </div>

      <div className="anim-fadeUp" style={{
        background: T.surface, border: `1px solid ${T.border}`,
        borderRadius: "0 0 16px 16px", padding: "36px",
        width: "100%", maxWidth: 420,
        boxShadow: `0 24px 60px rgba(0,0,0,0.55), ${glow()}`,
      }}>
        {tab === "login" ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Input label="電子信箱" type="email" placeholder="your@email.com" value={email} onChange={e => setEmail(e.target.value)} />
            <Input label="密碼" type="password" placeholder="輸入密碼" value={pw} onChange={e => setPw(e.target.value)} />
            <Btn variant="solid" onClick={handleLogin} style={{ padding: "14px", fontSize: "1rem", marginTop: 8 }}>登入 →</Btn>
            <div style={{ textAlign: "center", fontSize: "0.84rem", color: T.text2 }}>
              還沒有帳號？{" "}
              <span onClick={() => { setTab("register"); setMessage(""); }} style={{ color: T.accent, cursor: "pointer" }}>立即註冊</span>
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Input label="姓名" value={name} onChange={e => setName(e.target.value)} placeholder="王小明" />
            <Input label="電子信箱" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com" />
            <Input label="密碼" type="password" value={pw} onChange={e => setPw(e.target.value)} placeholder="至少8位字元" />
            <Input label="確認密碼" type="password" value={pw2} onChange={e => setPw2(e.target.value)} placeholder="再次輸入密碼" />
            <Btn variant="solid" onClick={handleRegister} style={{ padding: "14px", fontSize: "1rem", marginTop: 8 }}>建立帳號 →</Btn>
            <div style={{ textAlign: "center", fontSize: "0.84rem", color: T.text2 }}>
              已有帳號？{" "}
              <span onClick={() => { setTab("login"); setMessage(""); }} style={{ color: T.accent, cursor: "pointer" }}>返回登入</span>
            </div>
          </div>
        )}
        {message && (
          <div style={{ marginTop: 14, padding: "10px 14px", background: "rgba(239,68,68,0.1)", border: `1px solid ${T.danger}44`, borderRadius: 8, color: T.danger, fontSize: "0.84rem", textAlign: "center" }}>
            ⚠️ {message}
          </div>
        )}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════
   PROFILE DROPDOWN
══════════════════════════════════════════ */
function ProfileDropdown({ open, onClose, onProfile, onLogout, currentUser }: { open: boolean; onClose: () => void; onProfile: () => void; onLogout: () => void; currentUser: any }): JSX.Element | null {
  if (!open) return null;
  const items: any[] = [
    { icon: "👤", label: "個人資料管理", action: onProfile },
    { icon: "💰", label: "儲值點數", action: onClose },
    { icon: "⚙️", label: "帳號設定", action: onClose },
  ];
  return (
    <div className="anim-slideDown" style={{
      position: "absolute", top: 50, right: 0,
      background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: 13, padding: 8, minWidth: 220,
      boxShadow: `0 20px 50px rgba(0,0,0,0.65)`, zIndex: 300,
    }}>
      <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}`, marginBottom: 6 }}>
        <div style={{ fontWeight: 700 }}>{currentUser?.name || "使用者"}</div>
        <div style={{ fontSize: "0.75rem", color: T.text2, marginTop: 2 }}>{currentUser?.email || ""}</div>
      </div>
      {items.map((item: any) => (
        <PDItem key={item.label} icon={item.icon} label={item.label} onClick={() => { item.action(); onClose(); }} />
      ))}
      <div style={{ height: 1, background: T.border, margin: "4px 0" }} />
      <PDItem icon="🚪" label="登出" onClick={onLogout} danger />
    </div>
  );
}

function PDItem({ icon, label, onClick, danger }: { icon: string; label: string; onClick: () => void; danger?: boolean }): JSX.Element {
  const [hov, setHov] = useState(false);
  return (
    <div onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} style={{
      padding: "10px 14px", borderRadius: 8, cursor: "pointer", fontSize: "0.86rem",
      display: "flex", alignItems: "center", gap: 10,
      color: danger ? (hov ? T.danger : T.text2) : (hov ? T.text : T.text2),
      background: hov ? (danger ? "rgba(239,68,68,0.1)" : T.surface2) : "transparent",
      transition: "all 0.15s",
    }}>
      <span style={{ width: 20, textAlign: "center" }}>{icon}</span>{label}
    </div>
  );
}

/* ══════════════════════════════════════════
   TOPBAR
══════════════════════════════════════════ */
function Topbar({ page, setPage, onLogout, currentUser }: { page: string; setPage: (page: string) => void; onLogout: () => void; currentUser: any }): JSX.Element {
  const [profileOpen, setProfileOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setProfileOpen(false); };
    document.addEventListener("mousedown", h as EventListener);
    return () => document.removeEventListener("mousedown", h as EventListener);
  }, []);

  const navItems: any[] = [
    { id: "home",      label: "首頁" },
    { id: "materials", label: "教材管理" },
    { id: "quiz",      label: "測驗管理" },
    { id: "review",    label: "學習回顧" },
  ];

  return (
    <header style={{
      height: 64, background: T.surface, borderBottom: `1px solid ${T.border}`,
      display: "flex", alignItems: "center", padding: "0 24px", gap: 16,
      position: "sticky", top: 0, zIndex: 200,
      backdropFilter: "blur(12px)",
    }}>
      <div onClick={() => setPage("home")} style={{
        ...mono, fontWeight: 700, fontSize: "1.1rem", cursor: "pointer",
        background: `linear-gradient(135deg,${T.accent},${T.accent2})`,
        WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
      }}>AHa!!</div>

      <nav style={{ display: "flex", gap: 2, marginLeft: 8 }}>
        {navItems.map((n: any) => {
          const active = page === n.id;
          return (
            <button key={n.id} onClick={() => setPage(n.id)} style={{
              padding: "7px 16px", border: "none", borderRadius: 8, cursor: "pointer",
              fontFamily: "inherit", fontSize: "0.85rem", fontWeight: active ? 600 : 400,
              background: active ? `rgba(0,212,255,0.1)` : "transparent",
              color: active ? T.accent : T.text2,
              transition: "all 0.18s",
            }}>{n.label}</button>
          );
        })}
      </nav>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginLeft: "auto" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 6, ...mono, fontSize: "0.84rem",
          color: T.gold, padding: "6px 14px",
          background: "rgba(245,158,11,0.1)", border: `1px solid rgba(245,158,11,0.3)`,
          borderRadius: 20,
        }}>⭐ 1,250 pt</div>

        <div ref={ref} style={{ position: "relative" }}>
          <div onClick={() => setProfileOpen(o => !o)} style={{
            width: 38, height: 38, borderRadius: "50%",
            background: `linear-gradient(135deg,${T.accent2},${T.accent})`,
            border: `2px solid ${T.accent}`,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", fontWeight: 700, fontSize: "0.9rem", color: "#fff",
            boxShadow: profileOpen ? glow() : "none",
            transition: "box-shadow 0.2s",
          }} title={currentUser?.name || "使用者"}>{(currentUser?.name || "U").slice(0, 1)}</div>
          <ProfileDropdown
            open={profileOpen}
            onClose={() => setProfileOpen(false)}
            onProfile={() => setPage("profile")}
            onLogout={onLogout}
            currentUser={currentUser}
          />
        </div>
      </div>
    </header>
  );
}

/* ══════════════════════════════════════════
   HOME PAGE
══════════════════════════════════════════ */
function HomePage({ setPage, currentUser }: { setPage: (page: string) => void; currentUser: any }): JSX.Element {
  const features: any[] = [
    { id: "materials", title: "📚 教材管理", desc: "上傳影片、自動辨識內容、生成學習大綱，智慧管理所有素材。", badge: "3 部影片" },
    { id: "quiz",      title: "📝 測驗管理", desc: "AI 依影片內容自動出 5 題、即時批改，統計正確率，精準掌握學習盲點。", badge: "可作答" },
    { id: "ai-tutor",  title: "🤖 AI 家教",  desc: "隨時問、隨時答，AI 陪你解題，查詢所有歷史對話紀錄。" },
    { id: "review",    title: "📊 學習回顧", desc: "圖表化呈現學習歷程，一眼掌握你的進步軌跡。" },
  ];
  const stats: any[] = [
    { num: "12",    label: "學習影片" },
    { num: "87%",   label: "平均正確率" },
    { num: "1,250", label: "剩餘點數" },
    { num: "24",    label: "完成測驗" },
  ];
  return (
    <div className="anim-fadeUp">
      <div style={{ marginBottom: 28 }}>
        <SectionTitle>
          歡迎回來，<span style={{ color: T.accent }}>{currentUser?.name || "使用者"}</span>！👋
        </SectionTitle>
        <div style={{ color: T.text2, fontSize: "0.88rem", marginTop: 6 }}>今天也要好好學習程式喔～</div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(170px,1fr))", gap: 16, marginBottom: 28 }}>
        {stats.map((s: any) => <StatCard key={s.label} num={s.num} label={s.label} />)}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(270px,1fr))", gap: 20 }}>
        {features.map((f: any) => (
          <Card key={f.id} onClick={() => setPage(f.id)}>
            {f.badge && (
              <div style={{ position: "absolute", top: 16, right: 16, padding: "3px 10px", borderRadius: 20, fontSize: "0.7rem", fontWeight: 700, background: `rgba(0,212,255,0.12)`, color: T.accent, border: `1px solid ${T.accent}33` }}>{f.badge}</div>
            )}
            <div style={{ fontSize: "1.05rem", fontWeight: 700, marginBottom: 8 }}>{f.title}</div>
            <div style={{ fontSize: "0.82rem", color: T.text2, lineHeight: 1.65 }}>{f.desc}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════
   MATERIALS PAGE
══════════════════════════════════════════ */
function MaterialsPage({ setPage, showToast, videos, onVideosChange }: { setPage: (page: string) => void; showToast: (msg: string) => void; videos: any[]; onVideosChange: (videos: any[]) => void }): JSX.Element {
  const [videoURL, setVideoURL] = useState("");
  const [loading, setLoading] = useState(false);

  const addVideoLink = async (): Promise<void> => {
    const url = videoURL.trim();
    if (!url) { showToast("⚠️ 請輸入影片連結"); return; }
    try { new URL(url); } catch { showToast("⚠️ 影片連結格式不正確"); return; }

    setLoading(true);
    let videoTitle: string = url;
    let recognized: boolean = false;

    if (url.includes("youtube.com") || url.includes("youtu.be")) {
      try {
        showToast("🔍 正在辨識影片內容...");
        const oembedUrl = `https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`;
        const response = await fetch(oembedUrl);
        if (response.ok) {
          const data = await response.json();
          videoTitle = data.title;
          recognized = true;
        }
      } catch {
        showToast("⚠️ 無法獲取影片資訊，將繼續上傳");
      }
    }

    const newVideo = { name: videoTitle, recognized, outline: false, pts: "-50", date: new Date().toLocaleDateString("zh-TW") };
    try {
      await api.post('/videos', newVideo);
      const next = [newVideo, ...videos];
      onVideosChange(next);
      setVideoURL("");
      setLoading(false);
      showToast(recognized ? "✅ 影片已辨識並加入清單" : "✅ 影片已加入清單（待辨識）");
    } catch (error) {
      showToast("❌ 上傳失敗");
      setLoading(false);
    }
  };

  const recognizeVideo = async (idx: number): Promise<void> => {
    const next = videos.map((v, i) => i === idx ? { ...v, recognized: true } : v);
    try {
      await api.put(`/videos/${idx}`, next[idx]);
      onVideosChange(next);
      showToast("🔍 影片內容辨識完成");
    } catch (error) {
      showToast("❌ 更新失敗");
    }
  };

  const generateOutline = async (idx: number): Promise<void> => {
    if (!videos[idx].recognized) { showToast("⚠️ 請先完成影片辨識"); return; }
    const next = videos.map((v, i) => i === idx ? { ...v, outline: true } : v);
    try {
      await api.put(`/videos/${idx}`, next[idx]);
      onVideosChange(next);
      showToast("📄 大綱已生成");
    } catch (error) {
      showToast("❌ 更新失敗");
    }
  };

  return (
    <div className="anim-fadeUp">
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
        <BackBtn onClick={() => setPage("home")} />
        <SectionTitle>📚 <span style={{ color: T.accent }}>教材管理</span></SectionTitle>
      </div>
      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
        <input
          type="url" placeholder="貼上 YouTube 影片連結 (https://...)"
          value={videoURL} onChange={(e) => setVideoURL(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addVideoLink()}
          style={{ flex: 1, minWidth: 200, padding: "10px 14px", borderRadius: 10, border: `1px solid ${T.border}`, background: T.surface2, color: T.text, fontFamily: "inherit", fontSize: "0.88rem", outline: "none" }}
        />
        <Btn variant="primary" onClick={addVideoLink} disabled={loading}>
          {loading ? "辨識中..." : "＋ 上傳連結"}
        </Btn>
      </div>
      <DataTable
        cols={["影片名稱", "辨識狀態", "大綱", "點數", "上傳日期", "操作"]}
        rows={videos.map((v: any, i: number) => (
          <TR key={i} cells={[
            <span style={{ maxWidth: 200, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v.name}</span>,
            v.recognized ? <Tag color="green">✓ 已辨識</Tag> : <Tag color="gold">⏳ 待辨識</Tag>,
            v.outline ? <Tag color="blue">已生成</Tag> : <Tag color="muted">待生成</Tag>,
            <span style={{ ...mono, color: T.gold }}>{v.pts}</span>,
            v.date,
            <div style={{ display: "flex", gap: 8 }}>
              {!v.recognized && <Btn variant="ghost" onClick={() => recognizeVideo(i)}>辨識</Btn>}
              <Btn variant="ghost" onClick={() => generateOutline(i)}>
                {v.outline ? "查看大綱" : "生成大綱"}
              </Btn>
            </div>,
          ]} />
        ))}
      />
      <div style={{ marginTop: 24, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, fontSize: "0.84rem", color: T.text2 }}>
        每次影片辨識費用：<span style={{ ...mono, color: T.gold }}>50 點</span>
        　｜　剩餘點數：<span style={{ ...mono, color: T.accent }}>1,250 點</span>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════
   QUIZ PAGE — AI 依影片內容生成 5 題
══════════════════════════════════════════ */
async function generateQuizFromVideos(recognizedVideos: any[]): Promise<any[]> {
  const anthropicApiKey = import.meta.env.VITE_ANTHROPIC_API_KEY;
  if (!anthropicApiKey) {
    throw new Error("Missing VITE_ANTHROPIC_API_KEY");
  }
  const videoNames = recognizedVideos.map(v => v.name).join("、");
  const prompt = `你是一位程式教學 AI，請根據以下影片主題，出 5 道繁體中文選擇題（每題 4 個選項），測驗學生對這些主題的理解。

影片主題：${videoNames}

請嚴格以 JSON 陣列格式回覆，不要有任何說明文字或 Markdown 格式，格式如下：
[
  {
    "q": "題目文字",
    "opts": ["選項A", "選項B", "選項C", "選項D"],
    "ans": 0
  }
]
ans 為正確答案的索引（0-3）。共出 5 題。`;

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": anthropicApiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1000,
      messages: [{ role: "user", content: prompt }],
    }),
  });

  const data = await response.json();
  const text = data.content.map((i: any) => i.text || "").join("");
  const clean = text.replace(/```json|```/g, "").trim();
  return JSON.parse(clean);
}

function QuizPage({ setPage, showToast, videos, quizzes, onQuizzesChange }: { setPage: (page: string) => void; showToast: (msg: string) => void; videos: any[]; quizzes: any[]; onQuizzesChange: (quizzes: any[]) => void }): JSX.Element | any {
  const [view, setView] = useState("list");
  const [activeQuiz, setActiveQuiz] = useState<any>(null);
  const [generating, setGenerating] = useState(false);
  const [answers, setAnswers] = useState<number[]>([]);
  const [submitted, setSubmitted] = useState(false);

  const recognizedVideos: any[] = videos.filter(v => v.recognized);

  const handleGenerate = async (): Promise<void> => {
    if (recognizedVideos.length === 0) {
      showToast("⚠️ 尚無已辨識的影片，請先至教材管理完成影片辨識");
      return;
    }
    setGenerating(true);
    showToast("🤖 AI 正在依據影片內容生成 5 題...");
    try {
      const questions = await generateQuizFromVideos(recognizedVideos);
      if (!Array.isArray(questions) || questions.length === 0) throw new Error("Invalid response");
      const sourceName = recognizedVideos.map(v => v.name).join(" + ");
      const today = new Date().toLocaleDateString("zh-TW");
      const newQuiz = {
        name: `AI 生成測驗（${today}）`,
        source: sourceName,
        questions,
        lastRate: "—",
        rateColor: T.text2,
        done: false,
      };
      await api.post('/quizzes', newQuiz);
      const next = [newQuiz, ...quizzes];
      onQuizzesChange(next);
      showToast(`✅ 已生成 ${questions.length} 道題目！`);
    } catch (err) {
      showToast("❌ 生成失敗，請稍後再試");
    }
    setGenerating(false);
  };

  const startQuiz = (quiz: any): void => {
    setActiveQuiz(quiz);
    setAnswers((new Array(quiz.questions.length) as number[]).fill(-1));
    setSubmitted(false);
    setView("do");
  };

  const selectAnswer = (qIdx: number, optIdx: number): void => {
    if (submitted) return;
    setAnswers(prev => { const next = [...prev]; next[qIdx] = optIdx; return next; });
  };

  const handleSubmit = (): void => {
    if (answers.some(a => a === -1)) { showToast("⚠️ 請回答所有題目後再提交"); return; }
    if (!activeQuiz) return;
    setSubmitted(true);
    const correct = answers.filter((a, i) => a === activeQuiz.questions[i]?.ans).length;
    const pct = Math.round((correct / activeQuiz.questions.length) * 100);
    const rateColor = pct >= 80 ? T.accent3 : pct >= 60 ? T.gold : T.danger;
    const next = quizzes.map(q =>
      q.name === activeQuiz.name ? { ...q, lastRate: `${pct}%`, rateColor, done: true } : q
    );
    // Find index and update via API
    const idx = quizzes.findIndex(q => q.name === activeQuiz.name);
    if (idx !== -1) {
      api.put(`/quizzes/${idx}`, next[idx]).catch(() => {});
    }
    onQuizzesChange(next);
    const updatedQuiz = { ...activeQuiz, lastRate: `${pct}%`, rateColor, done: true };
    setActiveQuiz(updatedQuiz);
    showToast(`🎉 作答完成！正確 ${correct} / ${activeQuiz.questions.length} 題（${pct}%）`);
  };

  const correctCount = submitted && activeQuiz ? answers.filter((a, i) => a === activeQuiz?.questions[i]?.ans).length : 0;
  const answeredCount = answers.filter(a => a !== -1).length;

  const optionStyle = (qIdx: number, optIdx: number): React.CSSProperties => {
    if (!submitted) {
      const selected = answers[qIdx] === optIdx;
      return { border: `1px solid ${selected ? T.accent : T.border}`, background: selected ? `rgba(0,212,255,0.1)` : T.surface2, color: T.text, cursor: "pointer" };
    }
    if (!activeQuiz) return {};
    if (optIdx === activeQuiz.questions[qIdx]?.ans)
      return { border: `1px solid ${T.accent3}`, background: "rgba(16,185,129,0.1)", color: T.accent3, cursor: "default" };
    if (answers[qIdx] === optIdx)
      return { border: `1px solid ${T.danger}`, background: "rgba(239,68,68,0.1)", color: T.danger, cursor: "default" };
    return { border: `1px solid ${T.border}`, background: T.surface2, color: T.text2, cursor: "default" };
  };

  if (view === "do" && activeQuiz) {
    return (
      <div className="anim-fadeUp">
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
          <BackBtn onClick={() => { setView("list"); setActiveQuiz(null); }} />
          <div>
            <SectionTitle>{activeQuiz.name}</SectionTitle>
            <div style={{ fontSize: "0.78rem", color: T.text2, marginTop: 2 }}>來源：{activeQuiz.source}</div>
          </div>
        </div>

        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: "14px 20px", marginBottom: 20, display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: "0.82rem", color: T.text2 }}>共 {activeQuiz.questions.length} 題</span>
          <div style={{ flex: 1, height: 4, background: T.border, borderRadius: 2 }}>
            <div style={{ height: "100%", borderRadius: 2, width: `${(answeredCount / activeQuiz.questions.length) * 100}%`, background: `linear-gradient(90deg,${T.accent},${T.accent2})`, transition: "width 0.3s ease" }} />
          </div>
          <span style={{ ...mono, fontSize: "0.82rem", color: T.accent }}>{answeredCount} / {activeQuiz.questions.length} 已作答</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {activeQuiz.questions.map((q: any, qIdx: number) => (
            <div key={qIdx} style={{
              background: T.surface,
              border: submitted ? `1px solid ${answers[qIdx] === q.ans ? T.accent3 : T.danger}` : `1px solid ${T.border}`,
              borderLeft: submitted ? `4px solid ${answers[qIdx] === q.ans ? T.accent3 : T.danger}` : `4px solid ${T.border}`,
              borderRadius: 16, padding: 28,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <span style={{ ...mono, fontSize: "0.78rem", color: T.text2 }}>第 {qIdx + 1} 題</span>
                {submitted && <Tag color={answers[qIdx] === q.ans ? "green" : "red"}>{answers[qIdx] === q.ans ? "✓ 正確" : "✗ 錯誤"}</Tag>}
                {!submitted && answers[qIdx] !== null && <Tag color="blue">已作答</Tag>}
              </div>
              <div style={{ fontSize: "1rem", fontWeight: 600, lineHeight: 1.75, marginBottom: 16 }}>{q.q}</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {q.opts.map((opt: string, optIdx: number) => (
                  <div key={optIdx} onClick={() => selectAnswer(qIdx, optIdx)} style={{ padding: "12px 16px", borderRadius: 10, display: "flex", alignItems: "center", gap: 12, fontSize: "0.88rem", transition: "all 0.15s", ...optionStyle(qIdx, optIdx) }}>
                    <div style={{ width: 26, height: 26, borderRadius: 6, background: T.surface, border: `1px solid ${T.border}`, display: "flex", alignItems: "center", justifyContent: "center", ...mono, fontSize: "0.72rem", fontWeight: 700, flexShrink: 0 }}>{String.fromCharCode(65 + optIdx)}</div>
                    {opt}
                  </div>
                ))}
              </div>
              {submitted && answers[qIdx] !== q.ans && (
                <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(16,185,129,0.08)", border: `1px solid ${T.accent3}33`, borderRadius: 8, fontSize: "0.8rem", color: T.accent3 }}>
                  ✓ 正確答案：{q.opts[q.ans]}
                </div>
              )}
            </div>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 24, flexWrap: "wrap" }}>
          <Btn variant="ghost" onClick={() => { setView("list"); setActiveQuiz(null); }}>結束測驗</Btn>
          {!submitted ? (
            <Btn variant="solid" onClick={handleSubmit} disabled={answeredCount < activeQuiz.questions.length}>
              提交所有答案（{answeredCount}/{activeQuiz.questions.length}）
            </Btn>
          ) : (
            <>
              <div style={{ ...mono, color: T.accent3, fontSize: "1rem", fontWeight: 700 }}>
                得分：{correctCount} / {activeQuiz.questions.length}（{Math.round(correctCount / activeQuiz.questions.length * 100)}%）
              </div>
              <Btn variant="primary" onClick={() => { setView("list"); setActiveQuiz(null); }}>返回列表</Btn>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="anim-fadeUp">
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
        <BackBtn onClick={() => setPage("home")} />
        <SectionTitle>📝 <span style={{ color: T.accent }}>測驗管理</span></SectionTitle>
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <Btn variant="primary" onClick={handleGenerate} disabled={generating}>
          {generating
            ? <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ display: "inline-block", width: 14, height: 14, border: `2px solid ${T.accent}`, borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                生成中...
              </span>
            : "＋ 依影片生成 5 題"}
        </Btn>
        <Btn variant="ghost" onClick={() => showToast("📝 開啟題目編輯器")}>✏️ 更新題目</Btn>
      </div>

      <div style={{
        background: recognizedVideos.length > 0 ? `rgba(0,212,255,0.05)` : `rgba(245,158,11,0.05)`,
        border: `1px solid ${recognizedVideos.length > 0 ? T.accent : T.gold}33`,
        borderRadius: 10, padding: "10px 16px", marginBottom: 20, fontSize: "0.8rem", color: T.text2,
        display: "flex", alignItems: "flex-start", gap: 8,
      }}>
        <span style={{ color: recognizedVideos.length > 0 ? T.accent : T.gold, flexShrink: 0, marginTop: 1 }}>
          {recognizedVideos.length > 0 ? "ℹ" : "⚠"}
        </span>
        <div>
          {recognizedVideos.length > 0 ? (
            <>生成題目將依據以下已辨識的影片出題：<span style={{ color: T.text, fontWeight: 500, marginLeft: 4 }}>{recognizedVideos.map(v => v.name).join("、")}</span></>
          ) : (
            <>尚無已辨識的影片，請先至<span style={{ color: T.gold, cursor: "pointer" }} onClick={() => setPage("materials")}>教材管理</span>完成影片辨識後再生成題目。</>
          )}
        </div>
      </div>

      <DataTable
        cols={["測驗名稱", "來源影片", "題數", "我的正確率", "狀態", "操作"]}
        rows={quizzes.map((q: any, i: number) => (
          <TR key={i} cells={[
            <span style={{ fontWeight: 500 }}>{q.name}</span>,
            <span style={{ fontSize: "0.78rem", color: T.text2, maxWidth: 160, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{q.source}</span>,
            <span>{q.questions.length} 題</span>,
            <span style={{ ...mono, color: q.rateColor }}>{q.lastRate}</span>,
            <Tag color={q.done ? "green" : "purple"}>{q.done ? "已完成" : "未作答"}</Tag>,
            <Btn variant="primary" onClick={() => startQuiz(q)}>{q.done ? "重新作答" : "開始作答"}</Btn>,
          ]} />
        ))}
      />
    </div>
  );
}

/* ══════════════════════════════════════════
   AI TUTOR PAGE
══════════════════════════════════════════ */
async function callAI(userMessage: string, history: any[]): Promise<string> {
  const anthropicApiKey = import.meta.env.VITE_ANTHROPIC_API_KEY;
  if (!anthropicApiKey) {
    throw new Error("Missing VITE_ANTHROPIC_API_KEY");
  }
  const messages: any[] = [
    ...history.filter(m => m.type !== "typing").map(m => ({
      role: m.type === "user" ? "user" : "assistant",
      content: m.text,
    })),
    { role: "user", content: userMessage },
  ];

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": anthropicApiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1000,
      system: "你是 AHa，一位專業的繁體中文 AI 程式家教。請用清楚、友善、有耐心的方式解答學生的程式問題，適時使用 emoji 讓回答更生動。回答請簡潔扼要。",
      messages,
    }),
  });

  const data = await response.json();
  return data.content.map((i: any) => i.text || "").join("");
}

function AiTutorPage({ setPage, showToast }: { setPage: (page: string) => void; showToast: (msg: string) => void }): JSX.Element {
  const [msgs, setMsgs] = useState<any[]>([{ type: "ai", text: "嗨！我是你的 AI 程式家教 AHa 🤖 有任何程式問題都可以問我，我會盡力幫你解答！" }]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, typing]);

  const send = async (): Promise<void> => {
    const t = input.trim();
    if (!t || typing) return;
    const userMsg = { type: "user", text: t };
    setMsgs(m => [...m, userMsg]);
    setInput("");
    setTyping(true);
    try {
      const reply = await callAI(t, msgs);
      setMsgs(m => [...m, { type: "ai", text: reply }]);
    } catch {
      setMsgs(m => [...m, { type: "ai", text: "抱歉，目前無法連線，請稍後再試 😅" }]);
    }
    setTyping(false);
  };

  return (
    <div className="anim-fadeUp">
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
        <BackBtn onClick={() => setPage("home")} />
        <SectionTitle>🤖 <span style={{ color: T.accent }}>AI 家教</span></SectionTitle>
      </div>
      <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, height: 500, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          {msgs.map((m: any, i: number) => (
            <div key={i} style={{ display: "flex", gap: 10, flexDirection: m.type === "user" ? "row-reverse" : "row", animation: "fadeUp 0.3s ease" }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.85rem", background: m.type === "ai" ? `linear-gradient(135deg,${T.accent},${T.accent2})` : `linear-gradient(135deg,${T.accent2},${T.accent3})` }}>
                {m.type === "ai" ? "🤖" : "👤"}
              </div>
              <div style={{ maxWidth: "75%", padding: "11px 15px", fontSize: "0.87rem", lineHeight: 1.65, background: m.type === "ai" ? T.surface2 : `rgba(0,212,255,0.12)`, border: m.type === "user" ? `1px solid rgba(0,212,255,0.2)` : "none", borderRadius: m.type === "ai" ? "4px 12px 12px 12px" : "12px 4px 12px 12px", whiteSpace: "pre-wrap" }}>
                {m.text}
              </div>
            </div>
          ))}
          {typing && (
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: `linear-gradient(135deg,${T.accent},${T.accent2})`, display: "flex", alignItems: "center", justifyContent: "center" }}>🤖</div>
              <div style={{ background: T.surface2, borderRadius: "4px 12px 12px 12px", padding: "14px 18px", display: "flex", gap: 6, alignItems: "center" }}>
                {[0, 1, 2].map((i: number) => <div key={i} style={{ width: 7, height: 7, borderRadius: "50%", background: T.accent, animation: `pulse 1.2s ease ${i * 0.2}s infinite` }} />)}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <div style={{ padding: 16, borderTop: `1px solid ${T.border}`, display: "flex", gap: 10 }}>
          <textarea
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="輸入你的程式問題... (Enter 送出，Shift+Enter 換行)"
            rows={2}
            style={{ flex: 1, background: T.bg, border: `1px solid ${T.border}`, borderRadius: 10, padding: "12px 15px", color: T.text, fontFamily: "inherit", fontSize: "0.87rem", outline: "none", resize: "none" }}
          />
          <Btn variant="solid" onClick={send} disabled={typing} style={{ padding: "12px 20px", alignSelf: "flex-end" }}>送出</Btn>
        </div>
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
        <Btn variant="ghost" onClick={() => { setMsgs([{ type: "ai", text: "對話已清除，有什麼新問題嗎？😊" }]); showToast("🗑 對話紀錄已清除"); }}>🗑 清除對話紀錄</Btn>
        <Btn variant="ghost" onClick={() => showToast("📋 已複製對話紀錄")}>📋 查詢對話紀錄</Btn>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════
   REVIEW PAGE
══════════════════════════════════════════ */
function ReviewPage({ setPage }: { setPage: (page: string) => void }): JSX.Element {
  const bars: any[] = [
    { label: "變數",  pct: 90, color: T.accent },
    { label: "迴圈",  pct: 73, color: T.gold },
    { label: "函式",  pct: 85, color: T.accent },
    { label: "陣列",  pct: 92, color: T.accent3 },
    { label: "遞迴",  pct: 65, color: T.danger },
  ];
  const timeline: any[] = [
    { dot: T.accent3, title: "函式與模組測驗", meta: "2026/03/24 14:32 ｜ AI 批改完成", score: "92%", scoreLabel: "正確率" },
    { dot: T.accent,  title: "觀看「演算法排序」影片", meta: "2026/03/24 10:15 ｜ 已生成大綱", score: "-50", scoreLabel: "扣除點數" },
    { dot: T.gold,    title: "與 AI 家教對話 15 則", meta: "2026/03/23 20:40 ｜ 主題：遞歸概念", score: "+5%", scoreLabel: "理解提升" },
    { dot: T.accent3, title: "迴圈與條件判斷測驗", meta: "2026/03/22 16:00 ｜ AI 批改完成", score: "73%", scoreLabel: "正確率" },
  ];
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setTimeout(() => setMounted(true), 100); }, []);

  return (
    <div className="anim-fadeUp">
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
        <BackBtn onClick={() => setPage("home")} />
        <SectionTitle>📊 <span style={{ color: T.accent }}>學習回顧</span></SectionTitle>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(160px,1fr))", gap: 14, marginBottom: 28 }}>
        {[["87%","整體正確率"],["24","完成測驗場數"],["240","作答題目數"],["18天","連續學習"]].map(([n,l]: string[]) => <StatCard key={l} num={n} label={l} />)}
      </div>

      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: 2, color: T.text2, marginBottom: 14, paddingBottom: 8, borderBottom: `1px solid ${T.border}` }}>📈 各章節正確率</div>
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 14, padding: 24 }}>
          <div style={{ display: "flex", gap: 14, alignItems: "flex-end", height: 180, paddingBottom: 8 }}>
            {bars.map((b: any) => (
              <div key={b.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6, height: "100%", justifyContent: "flex-end" }}>
                <div style={{ ...mono, fontSize: "0.75rem", color: b.color }}>{b.pct}%</div>
                <div style={{ width: "100%", borderRadius: "6px 6px 0 0", transition: "height 0.9s cubic-bezier(0.34,1.4,0.64,1)", height: mounted ? `${b.pct}%` : "0%", background: `linear-gradient(180deg,${b.color},${b.color}44)` }} />
                <div style={{ fontSize: "0.7rem", color: T.text2 }}>{b.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div>
        <div style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: 2, color: T.text2, marginBottom: 14, paddingBottom: 8, borderBottom: `1px solid ${T.border}` }}>🕐 最近學習紀錄</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {timeline.map((t: any, i: number) => {
            const [hov, setHov] = useState(false);
            return (
              <div key={i} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} style={{ display: "flex", gap: 14, alignItems: "flex-start", background: T.surface, border: `1px solid ${hov ? T.accent : T.border}`, borderRadius: 12, padding: 16, transition: "border-color 0.2s" }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", marginTop: 5, flexShrink: 0, background: t.dot, boxShadow: `0 0 8px ${t.dot}` }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "0.88rem", fontWeight: 600, marginBottom: 3 }}>{t.title}</div>
                <div style={{ fontSize: "0.76rem", color: T.text2 }}>{t.meta}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ ...mono, fontSize: "1.05rem", fontWeight: 700, color: T.accent }}>{t.score}</div>
                <div style={{ fontSize: "0.7rem", color: T.text2 }}>{t.scoreLabel}</div>
              </div>
            </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════
   PROFILE PAGE
══════════════════════════════════════════ */
function ProfilePage({ setPage, showToast, currentUser, onUpdateProfile }: { setPage: (page: string) => void; showToast: (msg: string) => void; currentUser: any; onUpdateProfile: (updates: any) => void }): JSX.Element {
  const [name, setName] = useState(currentUser?.name || "");
  const [nick, setNick] = useState(currentUser?.nick || "");
  const [phone, setPhone] = useState("0912-345-678");
  const email = currentUser?.email || "";

  useEffect(() => { setName(currentUser?.name || ""); }, [currentUser]);

  return (
    <div className="anim-fadeUp">
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
        <BackBtn onClick={() => setPage("home")} />
        <SectionTitle>👤 <span style={{ color: T.accent }}>個人資料管理</span></SectionTitle>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "clamp(240px,25%,290px) 1fr", gap: 24 }}>
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 28, textAlign: "center" }}>
          <div style={{ width: 80, height: 80, borderRadius: "50%", margin: "0 auto 16px", background: `linear-gradient(135deg,${T.accent2},${T.accent})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "2rem", fontWeight: 700, border: `3px solid ${T.accent}`, boxShadow: glow() }}>{name ? name.slice(0,1) : "U"}</div>
          <div style={{ fontWeight: 700, fontSize: "1.1rem" }}>{name || "使用者"}</div>
          <div style={{ fontSize: "0.75rem", color: T.accent, marginTop: 4, letterSpacing: 1 }}>學習者 ｜ Lv.12</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 18 }}>
            {[["1,250","剩餘點數"],["24","測驗場次"],["87%","正確率"],["18","連續天數"]].map(([n,l]: string[]) => (
              <div key={l} style={{ background: T.surface2, borderRadius: 10, padding: 12 }}>
                <div style={{ ...mono, fontSize: "1.3rem", fontWeight: 700, color: T.accent }}>{n}</div>
                <div style={{ fontSize: "0.68rem", color: T.text2, marginTop: 2 }}>{l}</div>
              </div>
            ))}
          </div>
          <Btn variant="primary" onClick={() => showToast("💳 開啟儲值頁面")} style={{ width: "100%", marginTop: 16, textAlign: "center" }}>💰 儲值點數</Btn>
        </div>

        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 28 }}>
          <div style={{ fontWeight: 700, marginBottom: 18, paddingBottom: 12, borderBottom: `1px solid ${T.border}` }}>修改個人資料</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Input label="姓名" value={name} onChange={e => setName(e.target.value)} />
            <Input label="暱稱" value={nick} onChange={e => setNick(e.target.value)} />
            <Input label="電子信箱（不可修改）" type="email" value={email} onChange={() => {}} />
            <Input label="手機號碼" type="tel" value={phone} onChange={e => setPhone(e.target.value)} />
          </div>
          <div style={{ height: 1, background: T.border, margin: "24px 0" }} />
          <div style={{ fontWeight: 700, marginBottom: 18 }}>修改密碼</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Input label="目前密碼" type="password" placeholder="輸入目前密碼" value="" onChange={() => {}} />
            <Input label="新密碼" type="password" placeholder="輸入新密碼" value="" onChange={() => {}} />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 24 }}>
            <Btn variant="primary" onClick={() => {
              if (!name.trim()) { showToast("⚠️ 名稱不能為空"); return; }
              onUpdateProfile({ name: name.trim() });
              showToast("✅ 個人資料已儲存！");
            }}>儲存變更</Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════
   FEEDBACK MODAL
══════════════════════════════════════════ */
function FeedbackModal({ open, onClose, showToast }: { open: boolean; onClose: () => void; showToast: (msg: string) => void }): JSX.Element {
  const [type, setType] = useState("題目內容錯誤");
  const [desc, setDesc] = useState("");
  const submit = (): void => { onClose(); showToast("📬 回報已送出，感謝您的反饋！"); setDesc(""); };
  return (
    <Modal open={open} onClose={onClose} title="🚨 錯誤回報"
      footer={[
        <Btn key="cancel" variant="ghost" onClick={onClose}>取消</Btn>,
        <Btn key="submit" variant="danger" onClick={submit}>送出回報</Btn>,
      ]}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label style={{ fontSize: "0.72rem", color: T.text2, letterSpacing: "1px", textTransform: "uppercase" }}>回報類型</label>
          <select value={type} onChange={e => setType(e.target.value)} style={{ padding: "12px 16px", background: T.bg, border: `1px solid ${T.border}`, borderRadius: 9, color: T.text, fontFamily: "inherit", fontSize: "0.9rem", outline: "none" }}>
            {["題目內容錯誤","影片無法播放","點數計算異常","系統錯誤","其他問題"].map((o: string) => <option key={o}>{o}</option>)}
          </select>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label style={{ fontSize: "0.72rem", color: T.text2, letterSpacing: "1px", textTransform: "uppercase" }}>詳細描述</label>
          <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="請詳細描述您遇到的問題..." rows={5}
            style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 10, padding: 14, color: T.text, fontFamily: "inherit", fontSize: "0.87rem", resize: "vertical", outline: "none" }} />
        </div>
        <div style={{ fontSize: "0.73rem", color: T.text3, textAlign: "center" }}>＊ 若積分有誤，審核通過後將退還扣除點數</div>
      </div>
    </Modal>
  );
}

/* ══════════════════════════════════════════
   APP ROOT
══════════════════════════════════════════ */
export default function App() {
  const [currentUser, setCurrentUser] = useState<any>(loadSession);
  const [authed, setAuthed]           = useState<boolean>(() => !!loadSession());
  const [page, setPage]               = useState<string>("home");
  const [feedback, setFeedback]       = useState<boolean>(false);
  const [toastState, showToast]       = useToast();
  const [videos, setVideos]           = useState<any[]>([]);
  const [quizzes, setQuizzes]         = useState<any[]>([]);

  // Load data from API on mount
  useEffect(() => {
    const loadData = async (): Promise<void> => {
      try {
        const [vRes, qRes] = await Promise.all([
          api.get('/videos'),
          api.get('/quizzes')
        ]);
        setVideos(vRes.data);
        setQuizzes(qRes.data);
      } catch (error: any) {
        // Fallback to default data
        setVideos(loadVideos());
        setQuizzes(loadQuizzes());
      }
    };
    loadData();
  }, []);

  const handleVideosChange  = (next: any[]): void => { setVideos(next); /* In real app, call API to save */ };
  const handleQuizzesChange = (next: any[]): void => { setQuizzes(next); /* In real app, call API to save */ };

  const handleLogout = (): void => {
    api.post('/auth/logout').catch(() => {});
    setAuthed(false);
    setCurrentUser(null);
    setPage("home");
    clearSession();
  };
  const handleLogin  = (user: any): void => { setCurrentUser(user); setAuthed(true); setPage("home"); };
  const updateProfile = (updates: any): void => {
    const next = { ...currentUser, ...updates };
    setCurrentUser(next); saveSession(next);
    const accounts = loadAccounts();
    if (accounts[next.email]) { accounts[next.email] = { ...accounts[next.email], name: next.name }; saveAccounts(accounts); }
  };

  const sharedProps = { setPage, showToast, currentUser, onUpdateProfile: updateProfile, videos, onVideosChange: handleVideosChange, quizzes, onQuizzesChange: handleQuizzesChange };

  const renderPage = (): JSX.Element => {
    switch (page) {
      case "home":      return <HomePage {...sharedProps} />;
      case "materials": return <MaterialsPage {...sharedProps} />;
      case "quiz":      return <QuizPage {...sharedProps} />;
      case "ai-tutor":  return <AiTutorPage {...sharedProps} />;
      case "review":    return <ReviewPage {...sharedProps} />;
      case "profile":   return <ProfilePage {...sharedProps} />;
      default:          return <HomePage {...sharedProps} />;
    }
  };

  return (
    <>
      <style>{globalCSS}</style>
      {!authed ? (
        <AuthPage onLogin={handleLogin} showToast={showToast} />
      ) : (
        <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", position: "relative", zIndex: 1 }}>
          <Topbar page={page} setPage={setPage} onLogout={handleLogout} currentUser={currentUser} />
          <main style={{ flex: 1, padding: "32px 24px", maxWidth: 1180, width: "100%", margin: "0 auto" }}>
            {renderPage()}
          </main>
          <FAB onClick={() => setFeedback(true)} />
          <FeedbackModal open={feedback} onClose={() => setFeedback(false)} showToast={showToast} />
          <Toast message={toastState.msg} visible={toastState.visible} />
        </div>
      )}
    </>
  );
}