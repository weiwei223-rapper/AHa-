import { useEffect, useState, useCallback } from "react";
import api, { API_BASE_URL, userAPI } from "../api";
import {
  buildAchievements,
  loadVideoCount,
  saveAchievementPoints,
  saveUnlockedAchievementKeys,
  type AchievementItem,
  type LoginMeta,
} from "../utils/achievement";
import "./PageIndex.css";

import { usePoints } from "../context/PointsContext";

type UserData = {
  id: number;
  name: string;
  email: string;
  uid: string;
  points: number;
  last_login_date?: string;
  consecutive_login_days: number;
  total_login_days: number;
  claimed_achievement_points?: number;
};

type RechargeRecord = {
  date: string;
  order_id: string;
  amount: number;
  points?: number;
  balance_after?: number;
  payment_method?: string;
  plan_content?: string;
  plan_id?: string;
};

const rechargePlans = [
  { title: "NT$ 299", points: 300, price: 299 },
  { title: "NT$ 599", points: 650, price: 599 },
  { title: "NT$ 999", points: 1100, price: 999 },
];

const Profile = () => {
  const { setPoints } = usePoints();
  const [activeTab, setActiveTab] = useState<"basic" | "records">("basic");
  const [showTopup, setShowTopup] = useState(false);
  const [user, setUser] = useState<UserData | null>(null);
  const [achievements, setAchievements] = useState<AchievementItem[]>([]);
  const [accumulatedPoints, setAccumulatedPoints] = useState(0); 
  const [videoCount, setVideoCount] = useState(0);
  const [totalVideoCount, setTotalVideoCount] = useState(0);
  const [questionCount, setQuestionCount] = useState(0);
  const [loginMeta, setLoginMeta] = useState<LoginMeta>({
    lastLoginDate: '',
    consecutiveLoginDays: 0,
    totalLoginDays: 0,
  });
  const [signinStatus, setSigninStatus] = useState<any>(null);
  const [formValues, setFormValues] = useState({
    name: "",
    password: "",
    email: "",
    uid: "",
  });
  const [history, setHistory] = useState<RechargeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const refreshAchievements = useCallback((userData?: UserData) => {
    const activeUser = userData || user;
    if (!activeUser) return;

    const currentLoginMeta = {
      lastLoginDate: activeUser.last_login_date || '',
      consecutiveLoginDays: activeUser.consecutive_login_days || 0,
      totalLoginDays: activeUser.total_login_days || 0,
    };
    setLoginMeta(currentLoginMeta);

    const allAchievements = buildAchievements({
      videoCount,
      questionCount,
      loginStreakDays: currentLoginMeta.consecutiveLoginDays,
      totalLoginDays: currentLoginMeta.totalLoginDays,
    });

    const totalUnlockedPoints = allAchievements
      .filter((item) => item.unlocked)
      .reduce((sum, item) => sum + item.points, 0);

    const claimable = Math.max(0, totalUnlockedPoints - (activeUser.claimed_achievement_points || 0));
    setAccumulatedPoints(claimable);
    
    setAchievements(allAchievements);
  }, [videoCount, questionCount, user]);

  const loadUser = async (id: number) => {
    try {
      setLoading(true);
      const userResp = await api.get(`/users/${id}`);
      const data: UserData = userResp.data;
      setUser(data);
      setPoints(data.points);
      setFormValues({
        name: data.name,
        password: "",
        email: data.email,
        uid: data.uid,
      });
      
      const historyResp = await api.get(`/users/${id}/recharge-records`);
      setHistory(historyResp.data);
      // load sign-in status
      try {
        const resp = await userAPI.getSigninStatus(id);
        setSigninStatus(resp.data);
      } catch (err) {
        console.error('Failed to load signin status', err);
      }
      refreshAchievements(data);
    } catch (error) {
      console.error(error);
      setMessage("無法讀取使用者資料，請稍後再試。");
    } finally {
      setLoading(false);
    }
  };

  const loadSigninStatus = async (id: number) => {
    try {
      const resp = await userAPI.getSigninStatus(id);
      setSigninStatus(resp.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSignin = async () => {
    if (!user) return;
    try {
      setSaving(true);
      const resp = await userAPI.signin(user.id);
      const data = resp.data;
      // update user points and streak
      const updatedUserResp = await api.get(`/users/${user.id}`);
      const updatedData = updatedUserResp.data;
      setUser(updatedData);
      setPoints(updatedData.points);
      await loadSigninStatus(user.id);
      setMessage(`已簽到 +${data.points_awarded} 點，連續第 ${data.consecutive_login_days} 天`);
      refreshAchievements(updatedData);
    } catch (err: any) {
      setMessage(err.response?.data?.detail || '簽到失敗，請稍後再試。');
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    const storedUserId = localStorage.getItem("userId");
    if (storedUserId) {
      const userId = Number(storedUserId);
      userAPI.getStats(userId)
        .then((response) => {
          const stats = response.data;
          setVideoCount(stats.analyzed_video_count);
          setTotalVideoCount(stats.video_count);
          setQuestionCount(stats.total_questions_count || 0);
        })
        .catch((err) => console.error(err));
      void loadUser(userId);
    }
  }, []);

  useEffect(() => {
    refreshAchievements();
  }, [videoCount, questionCount, refreshAchievements]);

  const handleClaimPoints = async () => {
    if (!user || accumulatedPoints <= 0) return;
    try {
      setSaving(true);
      const resp = await userAPI.claimAchievementPoints(user.id);
      const updated = resp.data as UserData;
      setUser(updated);
      setPoints(updated.points);
      setAccumulatedPoints(0);
      setMessage(`🎉 領取成功！已領取 ${accumulatedPoints} 點成就獎勵。`);
      refreshAchievements(updated);
    } catch (err: any) {
      alert(err.response?.data?.detail || "領取失敗，請稍後再試。");
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    try {
      setSaving(true);
      const payload: any = { name: formValues.name, email: formValues.email };
      if (formValues.password) payload.password = formValues.password;
      const resp = await api.put(`/users/${user.id}`, payload);
      setUser(resp.data as UserData);
      setMessage("個人資料已更新。");
    } catch (err) {
      setMessage("更新失敗，請檢查輸入內容。");
    } finally {
      setSaving(false);
    }
  };

  const submitEcpayCheckout = async (plan: { title: string; points: number; price: number }) => {
    if (!user) return;
    
    try {
      setSaving(true);
      setMessage("準備跳轉至綠界科技付款頁面...");
      
      // 1. 呼叫後端 API 取得 CheckMacValue 與訂單資訊
      // 測試提醒：若要測試真實回傳入帳，請將下方 ReturnURL 改為您的 ngrok 公開網址
      const NGROK_URL = "https://b247-120-113-180-156.ngrok-free.app"; 
      const currentReturnURL = `${NGROK_URL}/ecpay/return`;

      const response = await api.post("/api/ecpay/checkout", {
        user_id: user.id,
        TotalAmount: plan.price,
        ItemName: plan.title,
        ReturnURL: currentReturnURL,
        ClientBackURL: window.location.href,
        plan_id: plan.title
      });
      
      const { params } = response.data;
      
      // 2. 建立動態表單並自動提交至綠界測試環境 (Stage)
      const ecpayUrl = "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5";
      
      const form = document.createElement("form");
      form.method = "POST";
      form.action = ecpayUrl;
      form.style.display = "none";
      
      // 使用後端回傳的完整參數，避免前端硬編碼造成 CheckMacValue 錯誤
      Object.keys(params).forEach((key) => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = key;
        input.value = params[key].toString();
        form.appendChild(input);
      });
      
      document.body.appendChild(form);
      form.submit(); // 正式跳轉
      
    } catch (err: any) {
      console.error("ECPay Checkout Error:", err);
      setMessage("啟動支付失敗，請稍後再試。");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="page-loading">正在讀取個人帳戶資料...</div>;

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div className="profile-header-main">
          <div className="profile-avatar">
            {user?.name?.charAt(0).toUpperCase() || "U"}
          </div>
          <div>
            <div className="page-eyebrow">User Profile</div>
            <h1>{user?.name || "使用者"}</h1>
            <p className="profile-uid">UID: {user?.uid}</p>
          </div>
        </div>
        
        <div className="dashboard-highlight-card">
          <span>Current Points</span>
          <strong>{user?.points.toLocaleString() ?? 0}</strong>
          <button 
            onClick={() => setShowTopup(true)}
            className="page-primary-button"
            style={{ marginTop: '12px', width: '100%', justifyContent: 'center' }}
          >
            💎 點數儲值
          </button>
          {accumulatedPoints > 0 && (
            <button 
              onClick={handleClaimPoints} 
              disabled={saving}
              style={{ 
                marginTop: '8px',
                padding: '8px 16px', 
                fontSize: '0.9rem',
                fontWeight: '900',
                background: 'linear-gradient(135deg, #facc15, #eab308)',
                color: '#0f172a',
                border: 'none',
                borderRadius: '10px',
                boxShadow: '0 4px 12px rgba(234, 179, 8, 0.3)',
                cursor: 'pointer',
                width: '100%'
              }}
            >
              {saving ? '領取中...' : `領取獎勵 (${accumulatedPoints})`}
            </button>
          )}
        </div>
      </section>

      {message && <div className={`page-message ${message.includes("失敗") ? "error" : "success"}`}>{message}</div>}

      <div className="profile-tab-row">
        <button className={`profile-tab-btn ${activeTab === "basic" ? "active" : ""}`} onClick={() => setActiveTab("basic")}>基本資料</button>
        <button className={`profile-tab-btn ${activeTab === "records" ? "active" : ""}`} onClick={() => setActiveTab("records")}>儲值紀錄</button>
      </div>

      <section className="profile-content-layout">
        {activeTab === "basic" ? (
          <>
            <section className="panel-card">
              <div className="panel-header">
                <h2>個人資訊設定</h2>
                <button onClick={() => setShowTopup(true)} className="page-primary-button">點數儲值</button>
              </div>
              <form onSubmit={handleUpdate} className="profile-form">
                <div className="form-grid">
                  <div className="form-group">
                    <label>姓名</label>
                    <input type="text" value={formValues.name} onChange={(e) => setFormValues({ ...formValues, name: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>電子郵件</label>
                    <input type="email" value={formValues.email} onChange={(e) => setFormValues({ ...formValues, email: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>新密碼 (不更改請留空)</label>
                    <input type="password" placeholder="••••••••" value={formValues.password} onChange={(e) => setFormValues({ ...formValues, password: e.target.value })} />
                  </div>
                </div>
                <div className="profile-action-row">
                  <button type="submit" disabled={saving} className="page-primary-button">{saving ? "儲存中..." : "更新個人資料"}</button>
                </div>
              </form>
            </section>

            <section className="panel-card signin-panel">
              <div className="panel-header">
                <div>
                  <div className="page-eyebrow">Daily Check-in</div>
                  <h2>每日簽到</h2>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ fontSize: '0.9rem', color: '#64748b' }}>{signinStatus ? `連續 ${signinStatus.cycle_day || 0} 天` : ''}</div>
                  <button
                    onClick={handleSignin}
                    disabled={saving || (signinStatus && signinStatus.signed_today)}
                    className="page-primary-button"
                  >
                    {signinStatus && signinStatus.signed_today ? '已簽到' : '簽到'}
                  </button>
                </div>
              </div>
              <div style={{ padding: '12px 18px' }}>
                <div style={{ display: 'flex', gap: 10, justifyContent: 'center', alignItems: 'flex-end' }}>
                  {(signinStatus?.rewards || Array.from({ length: 7 }, (_, i) => ({ day: i + 1, points: [20,20,25,20,20,20,30][i], checked: false }))).map((d: any) => (
                    <div key={d.day} style={{ textAlign: 'center' }}>
                      <div style={{
                        width: 72,
                        height: 72,
                        borderRadius: 12,
                        background: d.checked ? 'linear-gradient(180deg,#facc15,#f59e0b)' : '#fff7ed',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: d.checked ? '0 6px 18px rgba(250, 204, 21, 0.18)' : '0 1px 3px rgba(15,23,42,0.06)'
                      }}>
                        <div style={{ textAlign: 'center' }}>
                          {d.checked ? <div style={{ fontSize: 18, fontWeight: 800 }}>✓</div> : <div style={{ fontSize: 14, color: '#92400e', fontWeight: 700 }}>Day{d.day}</div>}
                        </div>
                      </div>
                      <div style={{ marginTop: 6, fontSize: 12, color: '#92400e', fontWeight: 700 }}>{d.points} pts</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="panel-card achievement-panel">
              <div className="panel-header">
                <div>
                  <div className="page-eyebrow">Milestones</div>
                  <h2>成就與勳章</h2>
                </div>
              </div>
              <div className="achievement-grid">
                {achievements.map((item) => {
                  const parts = item.progress.split('/');
                  const current = Number(parts[0]);
                  const target = Number(parts[1]);
                  const progress = isNaN(current/target) ? 0 : Math.min(100, (current/target)*100);
                  
                  return (
                    <div key={item.key} className={`achievement-item ${item.unlocked ? "unlocked" : "locked"}`}>
                      <div className="achievement-badge">
                        <img 
                          src={item.badgeImage} 
                          alt={item.title}
                          title={item.title}
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                        {!item.unlocked && <div className="lock-overlay">🔒</div>}
                      </div>
                      <div className="achievement-info">
                        <h3>{item.title}</h3>
                        <p>{item.description}</p>
                        <div className="achievement-progress-bar">
                          <div 
                             className="progress-fill" 
                             style={{ width: `${progress}%` }} 
                          />
                        </div>
                        <span className="achievement-meta">{item.progress} | {item.points} pts</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </>
        ) : (
          <section className="panel-card">
            <div className="panel-header">
              <h2>儲值與點數歷史</h2>
              <button onClick={() => setShowTopup(true)} className="page-primary-button">點數儲值</button>
            </div>
            <table className="history-table">
              <thead>
                <tr><th>日期</th><th>訂單編號</th><th>金額</th><th>獲得點數</th><th>餘額</th><th>付款方式</th></tr>
              </thead>
              <tbody>
                {history.map((record) => (
                  <tr key={record.order_id}>
                    <td>{record.date}</td>
                    <td className="order-id">{record.order_id}</td>
                    <td>${record.amount}</td>
                    <td className="points-plus">+{record.points}</td>
                    <td className="balance">{record.balance_after ?? "-"}</td>
                    <td>{record.payment_method ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </section>

      {showTopup && (
        <div className="topup-modal-overlay" onClick={() => setShowTopup(false)}>
          <div className="topup-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>選擇儲值方案</h2>
              <button className="close-btn" onClick={() => setShowTopup(false)}>×</button>
            </div>
            <div className="topup-grid">
              {rechargePlans.map((plan) => (
                <div key={plan.price} className="topup-plan-card">
                  <h3>{plan.title}</h3>
                  <div className="plan-points">{plan.points} <span>Points</span></div>
                  <p>{plan.caption}</p>
                  <button onClick={() => submitEcpayCheckout(plan)} className="page-primary-button">立即前往付款</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;
