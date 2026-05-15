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
  { title: "NT$ 299", points: 300, price: 299, caption: "適合短期密集練習" },
  { title: "NT$ 599", points: 650, price: 599, caption: "常用方案，額外多送一些" },
  { title: "NT$ 999", points: 1100, price: 999, caption: "給長期學習與大量生成使用" },
];

const Profile = () => {
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

    const unlockedKeys = allAchievements.filter((item) => item.unlocked).map((item) => item.key);
    const totalUnlockedPoints = allAchievements
      .filter((item) => item.unlocked)
      .reduce((sum, item) => sum + item.points, 0);

    const claimable = Math.max(0, totalUnlockedPoints - (activeUser.claimed_achievement_points || 0));
    setAccumulatedPoints(claimable);
    
    saveAchievementPoints(totalUnlockedPoints);
    saveUnlockedAchievementKeys(unlockedKeys);
    setAchievements(allAchievements);
  }, [videoCount, totalVideoCount, questionCount, user]);

  const loadUser = async (id: number) => {
    try {
      setLoading(true);
      const expectedPoints = sessionStorage.getItem("pending_points");
      if (expectedPoints) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }

      const userResp = await api.get(`/users/${id}`);
      const data: UserData = userResp.data;
      setUser(data);
      setFormValues({
        name: data.name,
        password: "",
        email: data.email,
        uid: data.uid,
      });
      
      const historyResp = await api.get(`/users/${id}/recharge-records`);
      setHistory(historyResp.data);

      if (expectedPoints) {
        setMessage(`🎉 付款成功！已成功儲值 ${expectedPoints} 點。`);
        setActiveTab("records");
        setShowTopup(false);
        sessionStorage.removeItem("pending_points");
      } else {
        setMessage("");
      }
      refreshAchievements(data);
    } catch (error) {
      console.error(error);
      setMessage("無法讀取使用者資料，請稍後再試。");
    } finally {
      setLoading(false);
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
        .catch((error) => {
          console.error("Failed to fetch initial stats:", error);
          const currentVideoCount = loadVideoCount();
          setVideoCount(currentVideoCount);
        });
      void loadUser(userId);
    }
  }, []);

  useEffect(() => {
    refreshAchievements();
  }, [videoCount, questionCount, refreshAchievements]);

  useEffect(() => {
    const handleVideoUpdated = () => {
      if (user?.id) {
        userAPI.getStats(user.id).then((response) => {
          const stats = response.data;
          setVideoCount(stats.analyzed_video_count);
          setTotalVideoCount(stats.video_count);
          setQuestionCount(stats.total_questions_count || 0);
          refreshAchievements();
        }).catch(err => console.error(err));
      }
    };
    window.addEventListener('video-updated', handleVideoUpdated);
    window.addEventListener('points-updated', handleVideoUpdated);
    return () => {
      window.removeEventListener('video-updated', handleVideoUpdated);
      window.removeEventListener('points-updated', handleVideoUpdated);
    };
  }, [user, refreshAchievements]);

  const handleClaimPoints = async () => {
    if (!user || accumulatedPoints <= 0) return;
    try {
      setSaving(true);
      const resp = await userAPI.claimAchievementPoints(user.id);
      const updated = resp.data as UserData;
      setUser(updated);
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

  const submitEcpayCheckout = (plan: { title: string; points: number; price: number }) => {
    if (!user) return;
    const merchantTradeNo = `AHA${user.id}${Date.now().toString().slice(-10)}`;
    const checkoutParams = {
      MerchantTradeNo: merchantTradeNo,
      MerchantTradeDate: new Date().toLocaleString("zh-TW", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).replace(/\//g, "/"),
      TotalAmount: plan.price,
      TradeDesc: "AHa AI 點數儲值",
      ItemName: `${plan.points} 點`,
      ReturnURL: `${API_BASE_URL}/ecpay/return`,
      ClientBackURL: window.location.href,
      ChoosePayment: "ALL",
      EncryptType: 1,
    };
    const form = document.createElement("form");
    form.method = "post";
    form.action = `${API_BASE_URL}/ecpay/checkout`;
    form.style.display = "none";
    sessionStorage.setItem("pending_points", plan.points.toString());
    Object.entries(checkoutParams).forEach(([name, value]) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = String(value);
      form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
  };

  if (loading) return <div className="page-loading">正在讀取個人帳戶資料...</div>;

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Account Center</div>
          <h1>個人資料與帳戶中心</h1>
          <p>管理您的個人資訊與查看累積的成就與勳章。您可以在此處查看目前的 Chat 點數餘額與加值紀錄。</p>
        </div>
        <div className="page-hero-metric">
          <span>Current Points</span>
          <strong>{user?.points.toLocaleString() ?? 0}</strong>
          <p>可用於 AI 聊天與教學生成服務</p>
        </div>
      </section>

      {message && <div className={`page-message ${message.includes("失敗") ? "error" : "success"}`}>{message}</div>}

      <section className="panel-card achievement-overview">
        <div className="achievement-summary-row">
          <div>
            <span>累計成就獎勵</span>
            <strong>{accumulatedPoints}</strong>
            {accumulatedPoints > 0 ? (
              <button onClick={handleClaimPoints} disabled={saving} className="claim-button">領取獎勵</button>
            ) : (
              <p>所有獎勵已領取</p>
            )}
          </div>
          <div>
            <span>已完成題數</span>
            <strong>{questionCount} 題</strong>
            <p>完成 AI 測驗累計的題目數量</p>
          </div>
          <div>
            <span>連續登入</span>
            <strong>{loginMeta.consecutiveLoginDays} 天</strong>
            <p>維持學習節奏，養成好習慣</p>
          </div>
          <div>
            <span>影片完成度</span>
            <strong>{videoCount} / {totalVideoCount}</strong>
            <p>已分析影片與上傳總數比例</p>
          </div>
          <div>
            <span>累計登入</span>
            <strong>{loginMeta.totalLoginDays} 天</strong>
            <p>長期穩定學習的里程碑紀錄</p>
          </div>
        </div>
      </section>

      <section className="panel-card achievement-list-card">
        <div className="achievement-list-header">
          <h2>成就獎章</h2>
          <p>根據您的學習進度，獲得對應的成就獎勵與點數</p>
        </div>
        <div className="achievement-grid">
          {achievements.map((item) => {
            const [current, target] = item.progress.split('/').map((value) => Number(value));
            const currentProgress = Number.isFinite(current) && Number.isFinite(target) ? Math.min(current, target) : 0;
            const progressPercentage = target > 0 ? (currentProgress / target) * 100 : 0;
            const isCompleted = currentProgress >= target;

            return (
              <article key={item.key} className={`achievement-card ${isCompleted ? 'unlocked' : 'locked'}`}>   
                <div className="achievement-card-header">
                  <div className="achievement-badge">
                    <img
                      src={item.badgeImage}
                      alt={`${item.title} 勳章`}
                      onError={(event) => {
                        const img = event.currentTarget;
                        img.style.display = 'none';
                      }}
                    />
                  </div>
                  <div>
                    <strong>{item.title}</strong>
                    <span>{item.points} 點</span>
                  </div>
                </div>
                <p>{item.description}</p>
                <div className="achievement-progress-wrapper">
                  <div className="achievement-progress-text">
                    <span>{isCompleted ? '已完成' : '進度'}</span>
                    <span>{currentProgress}/{target}</span>
                  </div>
                  <div className="progress-bar-bg">
                    <div
                      className="progress-bar-fill"
                      style={{ width: `${progressPercentage}%` }}
                    ></div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="panel-card">
        <div className="profile-toolbar">
          <div className="profile-tab-row">
            <button
              type="button"
              className={`profile-tab-button ${activeTab === "basic" && !showTopup ? "active" : ""}`}
              onClick={() => {
                setActiveTab("basic");
                setShowTopup(false);
              }}
            >
              基本資訊
            </button>
            <button
              type="button"
              className={`profile-tab-button ${activeTab === "records" && !showTopup ? "active" : ""}`}        
              onClick={() => {
                setActiveTab("records");
                setShowTopup(false);
              }}
            >
              儲值紀錄
            </button>
            <button
              type="button"
              className={`profile-tab-button ${showTopup ? "active" : ""}`}
              onClick={() => setShowTopup(true)}
            >
              點數加值
            </button>
          </div>
        </div>

        {showTopup ? (
          <div className="profile-topup-layout">
            <div className="profile-balance-card">
              <span>可用點數餘額</span>
              <strong>{user?.points ?? 0}</strong>
              <p>選定欲購買的方案後，將導向藍新金流進行安全付款。</p>
              <p style={{ color: '#10b981', marginTop: '8px' }}>
                請在付款頁面完成所有步驟後，系統將自動導回此頁面。
              </p>
            </div>

            <div className="profile-plan-grid">
              {rechargePlans.map((plan) => (
                <article key={plan.title} className="profile-plan-card">
                  <div>
                    <div className="profile-plan-points">{plan.points} 點</div>
                    <h3>{plan.title}</h3>
                    <p>{plan.caption}</p>
                  </div>
                  <button
                    type="button"
                    className="page-primary-button"
                    onClick={() => submitEcpayCheckout(plan)}
                  >
                    立即儲值
                  </button>
                </article>
              ))}
            </div>
          </div>
        ) : activeTab === "basic" ? (
          <div className="profile-content-grid">
            <div className="profile-summary-card">
              <div className="profile-avatar">{user?.name?.charAt(0).toUpperCase() || "U"}</div>
              <div>
                <h2>{user?.name}</h2>
                <p>{user?.email}</p>
                <span>UID: {user?.uid}</span>
              </div>
            </div>

            <form onSubmit={handleUpdate} className="profile-form-grid">
              <label>
                姓名
                <input value={formValues.name} onChange={(e) => setFormValues({ ...formValues, name: e.target.value })} />  
              </label>
              <label>
                電子郵件
                <input type="email" value={formValues.email} onChange={(e) => setFormValues({ ...formValues, email: e.target.value })} />
              </label>
              <label>
                新密碼
                <input
                  type="password"
                  value={formValues.password}
                  onChange={(e) => setFormValues({ ...formValues, password: e.target.value })}
                  placeholder="留空則不更改密碼"
                />
              </label>
              <label>
                UID
                <input value={formValues.uid} readOnly />
              </label>
              <div className="profile-action-row">
                <button type="submit" className="page-primary-button" disabled={saving}>
                  {saving ? "儲存中..." : "儲存變更"}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div className="profile-record-table-wrap">
            <table className="profile-record-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>訂單編號</th>
                  <th>金額</th>
                  <th>獲得點數</th>
                  <th>餘額</th>
                  <th>付款方式</th>
                </tr>
              </thead>
              <tbody>
                {history.map((record) => (
                  <tr key={record.order_id}>
                    <td>{record.date}</td>
                    <td>{record.order_id}</td>
                    <td>NT$ {record.amount}</td>
                    <td className="points-plus">+{record.points ?? 0}</td>
                    <td>{record.balance_after ?? "-"}</td>
                    <td>{record.payment_method ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default Profile;
