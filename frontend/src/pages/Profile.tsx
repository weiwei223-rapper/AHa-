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
  const [achievementPoints, setAchievementPoints] = useState(0);
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

  const loadUser = async (id: number) => {
    try {
      setLoading(true);
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

      // Check for payment success in URL

      // ✅ 改用 sessionStorage 來檢查付款狀態
      const expectedPoints = sessionStorage.getItem("pending_points");

      if (expectedPoints) {
        setMessage(`🎉 付款成功！已成功儲值 ${expectedPoints} 點。`);
        setActiveTab("records");
        setShowTopup(false);

        // 清除暫存，避免使用者按 F5 重新整理時又重複跳出訊息
        sessionStorage.removeItem("pending_points");
      } else {
        setMessage("");
      }

      refreshAchievements();
    } catch (error) {
      console.error(error);
      setMessage("無法讀取使用者資料，請稍後再試。");
    } finally {
      setLoading(false);
    }
  };

  const refreshAchievements = useCallback(() => {
    if (!user) return;

    const currentLoginMeta = {
      lastLoginDate: user.last_login_date || '',
      consecutiveLoginDays: user.consecutive_login_days || 0,
      totalLoginDays: user.total_login_days || 0,
    };
    setLoginMeta(currentLoginMeta);

    const allAchievements = buildAchievements({
      videoCount,
      questionCount,
      loginStreakDays: currentLoginMeta.consecutiveLoginDays,
      totalLoginDays: currentLoginMeta.totalLoginDays,
    });

    const unlockedKeys = allAchievements.filter((item) => item.unlocked).map((item) => item.key);
    const totalPoints = allAchievements
      .filter((item) => item.unlocked)
      .reduce((sum, item) => sum + item.points, 0);

    setAchievementPoints(totalPoints);
    saveAchievementPoints(totalPoints);
    saveUnlockedAchievementKeys(unlockedKeys);
    setAchievements(allAchievements);
  }, [videoCount, totalVideoCount, questionCount, user]);

  useEffect(() => {
    const storedUserId = localStorage.getItem("userId");
    if (storedUserId) {
      const userId = Number(storedUserId);
      // 初始化時從後端 API 獲取最新的影片與題數計數
      userAPI.getStats(userId)
        .then((response) => {
          const stats = response.data;
          // 使用已分析影片數量作為成就進度
          setVideoCount(stats.analyzed_video_count);
          setTotalVideoCount(stats.video_count);
          setQuestionCount(stats.total_questions_count || 0);
        })
        .catch((error) => {
          console.error("Failed to fetch initial stats:", error);
          // 降級方案：使用 localStorage 中的值
          const currentVideoCount = loadVideoCount();
          setVideoCount(currentVideoCount);
        });

      // 初始化時載入使用者詳細資料
      void loadUser(userId);
    }
  }, []);

  useEffect(() => {
    refreshAchievements();
  }, [videoCount, questionCount, refreshAchievements]);

  useEffect(() => {
    // 監聽影片變更事件，當影片數量變化時重新載入成就
    const handleVideoUpdated = () => {
      if (user?.id) {
        // 從後端 API 獲取最新的統計資訊，包括真實的影片數量
        userAPI.getStats(user.id).then((response) => {
          const stats = response.data;
          // 使用已分析影片數量作為成就進度
          setVideoCount(stats.analyzed_video_count);
          setTotalVideoCount(stats.video_count);
          setQuestionCount(stats.total_questions_count || 0);
          refreshAchievements();
        }).catch((error) => {
          console.error("Failed to fetch user stats:", error);
          // 降級方案：從 localStorage 讀取
          const currentVideoCount = loadVideoCount();
          setVideoCount(currentVideoCount);
          refreshAchievements();
        });
      }
    };

    // 監聽測驗完成事件，當測驗完成時重新計算成就
    const handleQuizCompleted = () => {
      if (user?.id) {
        userAPI.getStats(user.id).then((response) => {
          const stats = response.data;
          setQuestionCount(stats.total_questions_count || 0);
          setTotalVideoCount(stats.video_count);
          refreshAchievements();
        });
      } else {
        refreshAchievements();
      }
    };

    window.addEventListener('video-updated', handleVideoUpdated);
    window.addEventListener('points-updated', handleVideoUpdated);
    window.addEventListener('quizCompleted', handleQuizCompleted);

    return () => {
      window.removeEventListener('video-updated', handleVideoUpdated);
      window.removeEventListener('points-updated', handleVideoUpdated);
      window.removeEventListener('quizCompleted', handleQuizCompleted);
    };
  }, [user?.id, refreshAchievements]);

  const handleFieldChange = (field: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [field]: value }));
  };

  const formatTradeDate = (date: Date) => {
    const pad = (value: number) => String(value).padStart(2, "0");
    return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(
      date.getHours(),
    )}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  };

  const submitEcpayCheckout = (plan: { title: string; points: number; price: number }) => {
    if (!user) {
      setMessage("請先登入後再進行付款。");
      return;
    }

    const merchantTradeNo = `AHA${user.id}${Date.now().toString().slice(-10)}`;
    const checkoutParams = {
      MerchantTradeNo: merchantTradeNo,
      MerchantTradeDate: formatTradeDate(new Date()),
      PaymentType: "aio",
      TotalAmount: plan.price,
      TradeDesc: "AHA 點數充值",
      ItemName: `${plan.points} 點`,
      ReturnURL: `${API_BASE_URL}/ecpay/return`,
      ClientBackURL: `${window.location.origin}/profile?payment_status=success&points=${plan.points}`,
      ChoosePayment: "ALL",
      EncryptType: 1,
    };

    const form = document.createElement("form");
    form.method = "post";
    form.action = `${API_BASE_URL}/ecpay/checkout`;
    form.style.display = "none";

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

  const resetForm = () => {
    if (!user) {
      return;
    }

    setFormValues({
      name: user.name,
      password: "",
      email: user.email,
      uid: user.uid,
    });
  };

  const handleSave = async () => {
    if (!user) {
      return;
    }

    try {
      setSaving(true);
      const payload: { name: string; email: string; password?: string } = {
        name: formValues.name,
        email: formValues.email,
      };

      if (formValues.password.trim()) {
        payload.password = formValues.password;
      }

      const resp = await api.put(`/users/${user.id}`, payload);
      const updated = resp.data as UserData;
      setUser(updated);
      setFormValues({
        name: updated.name,
        password: "",
        email: updated.email,
        uid: updated.uid,
      });
      setMessage("個人資料已更新。");
    } catch (error) {
      console.error(error);
      setMessage("儲存失敗，請稍後再試。");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="page-loading">正在讀取個人資料...</div>;
  }

  return (
    <div className="page-shell">
      <section className="page-hero">
        <div>
          <div className="page-eyebrow">Account Center</div>
          <h1>個人資料與點數中心</h1>
          <p>管理帳戶資訊、可用點數與充值紀錄。整體介面已與 Chat 工作台使用同一套視覺語言。</p>
        </div>
        <div className="page-hero-metric">
          <span>Current Points</span>
          <strong>{user?.points ?? 0}</strong>
          <p>可用於 AI 聊天與學習流程</p>
        </div>
      </section>

      {message ? <div className="page-info-banner">{message}</div> : null}

      <section className="panel-card achievement-overview">
        <div className="achievement-summary-row">
          <div>
            <span>累積成就點數</span>
            <strong>{achievementPoints}</strong>
            <p>達成成就後即可獲得對應點數，將在本地儲存並顯示於此。</p>
          </div>
          <div>
            <span>已回答題數</span>
            <strong>{questionCount} 題</strong>
            <p>參與 AI 測驗累積的答題數量，作為測驗成就進度依據。</p>
          </div>
          <div>
            <span>連續登入</span>
            <strong>{loginMeta.consecutiveLoginDays} 天</strong>
            <p>維持習慣，連續登入 7 天即可獲得《學習堅持者》。</p>
          </div>
          <div>
            <span>影片分析完成度</span>
            <strong>{videoCount} / {totalVideoCount}</strong>
            <p>已完成分析的影片數量，相對於總上傳數。</p>
          </div>
          <div>
            <span>累計登入</span>
            <strong>{loginMeta.totalLoginDays} 天</strong>
            <p>累計登入可解鎖長期學習成就。</p>
          </div>
        </div>
      </section>

      <section className="panel-card achievement-list-card">
        <div className="achievement-list-header">
          <h2>成就總覽</h2>
          <p>依據已分析影片數量，自動解鎖成就徽章。</p>
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
                      alt={`${item.title} 徽章`}
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
              Basic Info
            </button>
            <button
              type="button"
              className={`profile-tab-button ${activeTab === "records" && !showTopup ? "active" : ""}`}
              onClick={() => {
                setActiveTab("records");
                setShowTopup(false);
              }}
            >
              Recharge Records
            </button>
            <button
              type="button"
              className={`profile-tab-button ${showTopup ? "active" : ""}`}
              onClick={() => setShowTopup(true)}
            >
              Top Up
            </button>
          </div>
        </div>

        {showTopup ? (
          <div className="profile-topup-layout">
            <div className="profile-balance-card">
              <span>Available Balance</span>
              <strong>{user?.points ?? 0}</strong>
              <p>按下綠界付款後會導向結帳頁面，可選擇刷卡、超商付款或其他綠界支援的付款方式。</p>
              <p style={{ color: '#10b981', marginTop: '8px' }}>
                請在綠界結帳頁面完成付款，付款結果將回傳至後端。
              </p>
              <p style={{ color: '#6b7280', marginTop: '8px' }}>
                付款成功後，充值紀錄會顯示在 Recharge Records 頁籤中。
              </p>
            </div>

            <div className="profile-plan-grid">
              {rechargePlans.map((plan) => (
                <article key={plan.title} className="profile-plan-card">
                  <div>
                    <div className="profile-plan-points">{plan.points} points</div>
                    <h3>{plan.title}</h3>
                    <p>{plan.caption}</p>
                  </div>
                  <button
                    type="button"
                    className="page-primary-button"
                    onClick={() => submitEcpayCheckout(plan)}
                  >
                    綠界付款
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

            <div className="profile-form-grid">
              <label>
                Name
                <input value={formValues.name} onChange={(e) => handleFieldChange("name", e.target.value)} />
              </label>
              <label>
                Email
                <input type="email" value={formValues.email} onChange={(e) => handleFieldChange("email", e.target.value)} />
              </label>
              <label>
                New Password
                <input
                  type="password"
                  value={formValues.password}
                  onChange={(e) => handleFieldChange("password", e.target.value)}
                  placeholder="留空則不更新密碼"
                />
              </label>
              <label>
                UID
                <input value={formValues.uid} readOnly />
              </label>
              <div className="profile-action-row">
                <button type="button" className="page-primary-button" onClick={() => void handleSave()} disabled={saving}>
                  {saving ? "Saving..." : "Save Changes"}
                </button>
                <button type="button" className="page-secondary-button" onClick={resetForm}>Reset</button>
              </div>
            </div>
          </div>
        ) : (
          <div className="profile-record-table-wrap">
            <table className="profile-record-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Order ID</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Added</th>
                  <th>Balance</th>
                  <th>Method</th>
                </tr>
              </thead>
              <tbody>
                {history.map((record) => (
                  <tr key={record.order_id}>
                    <td>{record.date}</td>
                    <td>{record.order_id}</td>
                    <td>{record.plan_content ?? "-"}</td>
                    <td>NT$ {record.amount}</td>
                    <td>+{record.points ?? 0}</td>
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
