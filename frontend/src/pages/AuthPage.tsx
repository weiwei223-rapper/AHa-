import { useState } from 'react';
import { authAPI } from '../api';
import './AuthPage.css';
import logoIcon from "../assets/logo_v3.jpg";

export default function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [registerName, setRegisterName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerPasswordConfirm, setRegisterPasswordConfirm] = useState('');

  const handleSkipLogin = () => {
    const guestUser = {
      id: 1,
      name: 'wei',
      email: 'wei@gmail.com',
      uid: 'UID-20260419',
      points: 10000,
    };

    localStorage.setItem('userId', guestUser.id.toString());
    localStorage.setItem('userData', JSON.stringify(guestUser));
    window.location.href = '/';
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await authAPI.login({
        email: loginEmail,
        password: loginPassword,
      });

      const { user } = response.data;
      localStorage.setItem('userId', user.id.toString());
      localStorage.setItem('userData', JSON.stringify(user));
      window.location.href = '/';
    } catch (err: any) {
      setError(err.response?.data?.detail || '登入失敗，請確認帳號密碼。');
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!registerName.trim()) {
      setError('請輸入姓名。');
      return;
    }
    if (!registerEmail.trim()) {
      setError('請輸入電子郵件。');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerEmail)) {
      setError('請輸入有效的電子郵件格式。');
      return;
    }
    if (!registerPassword) {
      setError('請輸入密碼。');
      return;
    }
    if (registerPassword.length < 6) {
      setError('密碼長度至少要 6 碼。');
      return;
    }
    if (registerPassword !== registerPasswordConfirm) {
      setError('兩次輸入的密碼不一致。');
      return;
    }

    setLoading(true);

    try {
      const response = await authAPI.register({
        name: registerName,
        email: registerEmail,
        password: registerPassword,
      });

      const user = response.data;
      localStorage.setItem('userId', user.id.toString());
      localStorage.setItem('userData', JSON.stringify(user));
      window.location.href = '/';
    } catch (err: any) {
      setError(err.response?.data?.detail || '註冊失敗，請稍後再試。');
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        {/* 新增的科技感頭部視覺 */}
        <div className="auth-header-visual">
          <img src={logoIcon} alt="Logo" className="auth-logo-img" />
          <div className="auth-brand-name">AHA AI</div>
        </div>

        <div className={`auth-section login-section ${mode === 'login' ? 'active' : 'hidden'}`}>
          <h2>登入系統</h2>
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label htmlFor="login-email">電子郵件</label>
              <input
                id="login-email"
                type="email"
                placeholder="請輸入電子郵件"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="login-password">密碼</label>
              <input
                id="login-password"
                type="password"
                placeholder="請輸入密碼"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            {error && mode === 'login' && <div className="error-message">{error}</div>}

            <button type="submit" className="auth-button" disabled={loading}>
              {loading ? '驗證中...' : '進入工作台'}
            </button>
            <button type="button" className="auth-button skip-button" onClick={handleSkipLogin} disabled={loading} style={{ background: 'transparent', border: '1px solid rgba(43, 193, 241, 0.4)', color: '#94a3b8', boxShadow: 'none', marginTop: '14px' }}>
              訪客模式 (跳過登入)
            </button>
          </form>

          <div className="auth-toggle">
            <p>
              還沒有帳號？
              <button
                type="button"
                className="toggle-link"
                onClick={() => {
                  setMode('register');
                  setError('');
                  setLoginEmail('');
                  setLoginPassword('');
                }}
              >
                立即註冊
              </button>
            </p>
          </div>
        </div>

        <div className={`auth-section register-section ${mode === 'register' ? 'active' : 'hidden'}`}>
          <h2>建立帳號</h2>
          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label htmlFor="register-name">姓名</label>
              <input
                id="register-name"
                type="text"
                placeholder="請輸入姓名"
                value={registerName}
                onChange={(e) => setRegisterName(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="register-email">電子郵件</label>
              <input
                id="register-email"
                type="email"
                placeholder="請輸入電子郵件"
                value={registerEmail}
                onChange={(e) => setRegisterEmail(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="register-password">密碼</label>
              <input
                id="register-password"
                type="password"
                placeholder="請輸入至少 6 碼密碼"
                value={registerPassword}
                onChange={(e) => setRegisterPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="register-password-confirm">確認密碼</label>
              <input
                id="register-password-confirm"
                type="password"
                placeholder="請再次輸入密碼"
                value={registerPasswordConfirm}
                onChange={(e) => setRegisterPasswordConfirm(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            {error && mode === 'register' && <div className="error-message">{error}</div>}

            <button type="submit" className="auth-button" disabled={loading}>
              {loading ? '註冊中...' : '註冊帳號'}
            </button>
            <button type="button" className="auth-button skip-button" onClick={handleSkipLogin} disabled={loading} style={{ background: 'transparent', border: '1px solid rgba(43, 193, 241, 0.4)', color: '#94a3b8', boxShadow: 'none', marginTop: '14px' }}>
              訪客模式 (跳過登入)
            </button>
          </form>

          <div className="auth-toggle">
            <p>
              已經有帳號？
              <button
                type="button"
                className="toggle-link"
                onClick={() => {
                  setMode('login');
                  setError('');
                  setRegisterName('');
                  setRegisterEmail('');
                  setRegisterPassword('');
                  setRegisterPasswordConfirm('');
                }}
              >
                返回登入
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
