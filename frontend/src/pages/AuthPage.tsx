import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../api';
import './AuthPage.css';

export default function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Login state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register state
  const [registerName, setRegisterName] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerPasswordConfirm, setRegisterPasswordConfirm] = useState('');

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
      // Store user ID in localStorage
      localStorage.setItem('userId', user.id.toString());
      localStorage.setItem('userData', JSON.stringify(user));

      // Navigate to home page immediately
      window.location.href = '/';
    } catch (err: any) {
      setError(err.response?.data?.detail || '登入失敗，請檢查您的電子郵件和密碼');
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!registerName.trim()) {
      setError('請輸入您的姓名');
      return;
    }
    if (!registerEmail.trim()) {
      setError('請輸入您的電子郵件');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerEmail)) {
      setError('請輸入有效的電子郵件地址');
      return;
    }
    if (!registerPassword) {
      setError('請設定密碼');
      return;
    }
    if (registerPassword.length < 6) {
      setError('密碼至少需要 6 個字符');
      return;
    }
    if (registerPassword !== registerPasswordConfirm) {
      setError('兩次輸入的密碼不相符');
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
      // Store user ID in localStorage
      localStorage.setItem('userId', user.id.toString());
      localStorage.setItem('userData', JSON.stringify(user));

      // Navigate to home page immediately
      window.location.href = '/';
    } catch (err: any) {
      setError(err.response?.data?.detail || '註冊失敗，請稍後重試');
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        {/* Login Section */}
        <div className={`auth-section login-section ${mode === 'login' ? 'active' : 'hidden'}`}>
          <h2>登入帳號</h2>
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label htmlFor="login-email">電子郵件</label>
              <input
                id="login-email"
                type="email"
                placeholder="請輸入您的電子郵件"
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
                placeholder="請輸入您的密碼"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            {error && mode === 'login' && <div className="error-message">{error}</div>}

            <button type="submit" className="auth-button" disabled={loading}>
              {loading ? '登入中...' : '登入'}
            </button>
          </form>

          <div className="auth-toggle">
            <p>
              還沒有帳號？{' '}
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
                建立新帳號
              </button>
            </p>
          </div>
        </div>

        {/* Register Section */}
        <div className={`auth-section register-section ${mode === 'register' ? 'active' : 'hidden'}`}>
          <h2>建立新帳號</h2>
          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label htmlFor="register-name">姓名</label>
              <input
                id="register-name"
                type="text"
                placeholder="請輸入您的姓名"
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
                placeholder="請輸入您的電子郵件"
                value={registerEmail}
                onChange={(e) => setRegisterEmail(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="register-password">設定密碼</label>
              <input
                id="register-password"
                type="password"
                placeholder="請設定密碼（至少 6 個字符）"
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
              {loading ? '建立中...' : '建立帳號'}
            </button>
          </form>

          <div className="auth-toggle">
            <p>
              已有帳號？{' '}
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
