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

  // OTP Forgot Password State
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotStep, setForgotStep] = useState<'request' | 'verify' | 'reset' | 'success'>('request');
  const [forgotEmail, setForgotEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [otpToken, setOtpToken] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState('');

  const handleSkipLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await authAPI.guest();
      const { user, access_token } = response.data;
      localStorage.setItem('userId', user.id.toString());
      localStorage.setItem('userData', JSON.stringify(user));
      localStorage.setItem('access_token', access_token);
      window.location.href = '/';
    } catch (err: any) {
      setError('訪客模式目前無法使用，請稍後再試。');
      setLoading(false);
    }
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

      const { user, access_token } = response.data;
      localStorage.setItem('userId', user.id.toString());
      localStorage.setItem('userData', JSON.stringify(user));
      localStorage.setItem('access_token', access_token);
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
    if (!registerOTP) {
      setError('請輸入驗證碼。');
      return;
    }

    setLoading(true);

    try {
      const response = await authAPI.register({
        name: registerName,
        email: registerEmail,
        password: registerPassword,
      });

      const { user, access_token } = response.data;
      localStorage.setItem('userId', user.id.toString());
      localStorage.setItem('userData', JSON.stringify(user));
      localStorage.setItem('access_token', access_token);
      window.location.href = '/';
    } catch (err: any) {
      setError(err.response?.data?.detail || '註冊失敗，請稍後再試。');
      setLoading(false);
    }
  };

  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotError('');
    if (!forgotEmail) {
      setForgotError('請輸入電子郵件。');
      return;
    }
    setForgotLoading(true);
    try {
      const response = await authAPI.requestOTP(forgotEmail);
      if (response.data.otp_token) {
        setOtpToken(response.data.otp_token);
      }
      setForgotStep('verify');
    } catch (err: any) {
      setForgotError(err.response?.data?.detail || '發送失敗，請確認信箱是否正確。');
    } finally {
      setForgotLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotError('');
    if (otpCode.length !== 6) {
      setForgotError('請輸入 6 位數驗證碼。');
      return;
    }
    setForgotLoading(true);
    try {
      const response = await authAPI.verifyOTP({ otp_token: otpToken, otp: otpCode });
      setResetToken(response.data.reset_token);
      setForgotStep('reset');
    } catch (err: any) {
      setForgotError(err.response?.data?.detail || '驗證碼錯誤或已過期。');
    } finally {
      setForgotLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotError('');
    if (newPassword.length < 6) {
      setForgotError('密碼長度至少要 6 碼。');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setForgotError('兩次輸入的密碼不一致。');
      return;
    }
    setForgotLoading(true);
    try {
      await authAPI.resetPasswordWithOTP({ reset_token: resetToken, new_password: newPassword });
      setForgotStep('success');
    } catch (err: any) {
      setForgotError(err.response?.data?.detail || '重設失敗，請稍後再試。');
    } finally {
      setForgotLoading(false);
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

            <div className="forgot-password-link-container" style={{ textAlign: 'right', marginTop: '-15px', marginBottom: '20px' }}>
              <button
                type="button"
                className="toggle-link"
                style={{ fontSize: '13px', color: '#94a3b8' }}
                onClick={() => {
                  setShowForgotModal(true);
                  setForgotStep('request');
                  setForgotError('');
                }}
              >
                忘記密碼？
              </button>
            </div>

            {error && mode === 'login' && <div className="error-message">{error}</div>}

            <button type="submit" className="auth-button" disabled={loading}>
              {loading ? '驗證中...' : '進入工作台'}
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

      {showForgotModal && (
        <div className="modal-overlay" onClick={() => !forgotLoading && setShowForgotModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ background: '#0d1725', border: '1px solid rgba(43, 193, 241, 0.3)', borderRadius: '20px', padding: '24px', maxWidth: '400px' }}>
            <div className="modal-header" style={{ textAlign: 'center', marginBottom: '20px' }}>
              <h2 className="modal-title" style={{ color: '#2bc1f1', margin: 0 }}>忘記密碼</h2>
              {forgotStep === 'request' && <p className="modal-subtitle" style={{ color: '#94a3b8', fontSize: '14px', marginTop: '4px' }}>請輸入 Email 以發送驗證碼</p>}
              {forgotStep === 'verify' && <p className="modal-subtitle" style={{ color: '#94a3b8', fontSize: '14px', marginTop: '4px' }}>驗證碼已發送至您的信箱</p>}
              {forgotStep === 'reset' && <p className="modal-subtitle" style={{ color: '#94a3b8', fontSize: '14px', marginTop: '4px' }}>驗證成功！請設定新密碼</p>}
              {forgotStep === 'success' && <p className="modal-subtitle" style={{ color: '#94a3b8', fontSize: '14px', marginTop: '4px' }}>密碼已成功重設</p>}
            </div>

            <div className="modal-body">
              {forgotStep === 'request' && (
                <form onSubmit={handleRequestOTP}>
                  <div className="form-group">
                    <label style={{ color: '#94a3b8', fontSize: '14px' }}>電子郵件</label>
                    <input type="email" value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} placeholder="請輸入 Email" style={{ width: '100%', padding: '12px', background: '#08111f', border: '1px solid rgba(43, 193, 241, 0.2)', borderRadius: '10px', color: 'white' }} required />
                  </div>
                  {forgotError && <div className="error-message">{forgotError}</div>}
                  <button type="submit" className="auth-button" disabled={forgotLoading}>{forgotLoading ? '發送中...' : '發送驗證碼'}</button>
                </form>
              )}

              {forgotStep === 'verify' && (
                <form onSubmit={handleVerifyOTP}>
                  <div className="form-group">
                    <label style={{ color: '#94a3b8', fontSize: '14px' }}>驗證碼</label>
                    <input type="text" maxLength={6} value={otpCode} onChange={(e) => setOtpCode(e.target.value)} placeholder="請輸入 6 位驗證碼" style={{ width: '100%', padding: '12px', background: '#08111f', border: '1px solid rgba(43, 193, 241, 0.2)', borderRadius: '10px', color: 'white', letterSpacing: '8px', textAlign: 'center', fontSize: '20px' }} required />
                  </div>
                  {forgotError && <div className="error-message">{forgotError}</div>}
                  <button type="submit" className="auth-button" disabled={forgotLoading}>{forgotLoading ? '驗證中...' : '驗證代碼'}</button>
                  <button type="button" onClick={() => setForgotStep('request')} style={{ background: 'none', border: 'none', color: '#94a3b8', width: '100%', marginTop: '10px', cursor: 'pointer', fontSize: '14px' }}>重新發送</button>
                </form>
              )}

              {forgotStep === 'reset' && (
                <form onSubmit={handleResetPassword}>
                  <div className="form-group">
                    <label style={{ color: '#94a3b8', fontSize: '14px' }}>新密碼</label>
                    <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="至少 6 碼" style={{ width: '100%', padding: '12px', background: '#08111f', border: '1px solid rgba(43, 193, 241, 0.2)', borderRadius: '10px', color: 'white' }} required />
                  </div>
                  <div className="form-group">
                    <label style={{ color: '#94a3b8', fontSize: '14px' }}>確認新密碼</label>
                    <input type="password" value={confirmNewPassword} onChange={(e) => setConfirmNewPassword(e.target.value)} placeholder="請再次輸入" style={{ width: '100%', padding: '12px', background: '#08111f', border: '1px solid rgba(43, 193, 241, 0.2)', borderRadius: '10px', color: 'white' }} required />
                  </div>
                  {forgotError && <div className="error-message">{forgotError}</div>}
                  <button type="submit" className="auth-button" disabled={forgotLoading}>{forgotLoading ? '重設中...' : '確認重設'}</button>
                </form>
              )}

              {forgotStep === 'success' && (
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '48px', color: '#4ade80', marginBottom: '20px' }}>✓</div>
                  <p style={{ color: 'white', marginBottom: '20px' }}>您的密碼已重設，請使用新密碼登入。</p>
                  <button onClick={() => setShowForgotModal(false)} className="auth-button">返回登入</button>
                </div>
              )}
            </div>

            {forgotStep !== 'success' && (
              <div className="modal-footer" style={{ marginTop: '20px', textAlign: 'center' }}>
                <button 
                  type="button" 
                  onClick={() => setShowForgotModal(false)}
                  style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
                  disabled={forgotLoading}
                >
                  取消
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
