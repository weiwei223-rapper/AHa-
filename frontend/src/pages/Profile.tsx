import { useEffect, useState } from "react";
import api, { userAPI } from "../api";
import {
  addAchievementPoints,
  buildAchievements,
  loadAchievementPoints,
  loadLoginMeta,
  loadUnlockedAchievementKeys,
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
};

type RechargeRecord = {
  date: string;
  order_id: string;
  amount: number;
  points?: number;
  payment_method?: string;
  plan_id?: string;
};

type UserStats = {
  video_count: number;
  remaining_points: number;
  completed_quizzes: number;
  average_accuracy: number;
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
  const [stats, setStats] = useState<UserStats>({
    video_count: 0,
    remaining_points: 0,
    completed_quizzes: 0,
    average_accuracy: 0,
  });
  const [achievements, setAchievements] = useState<AchievementItem[]>([]);
  const [achievementPoints, setAchievementPoints] = useState(0);
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
      setMessage("");
      await loadUserStats(id);
      refreshAchievements();
    } catch (error) {
      console.error(error);
      setMessage("無法讀取使用者資料，請稍後再試。");
    } finally {
      setLoading(false);
    }
  };

  const loadUserStats = async (id: number) => {
    try {
      const statsResp = await userAPI.getStats(id);
      setStats(statsResp.data);
    } catch (error) {
      console.error("Failed to load user stats:", error);
    }
  };

  const refreshAchievements = () => {
    const quizResultsRaw = localStorage.getItem("quizResults");
    let quizResults: unknown = [];
    try {
      quizResults = quizResultsRaw ? JSON.parse(quizResultsRaw) : [];
    } catch {
      quizResults = [];
    }

    const questionCount = Array.isArray(quizResults)
      ? quizResults.reduce((sum: number, item: { totalQuestions: number }) => sum + (item.totalQuestions || 0), 0)
      : 0;

    const currentLoginMeta = loadLoginMeta();
    setLoginMeta(currentLoginMeta);

    const allAchievements = buildAchievements({
      videoCount: stats.video_count,
      questionCount,
      loginStreakDays: currentLoginMeta.consecutiveLoginDays,
      totalLoginDays: currentLoginMeta.totalLoginDays,
    });

    const storedKeys = loadUnlockedAchievementKeys();
    const unlockedKeys = allAchievements.filter((item) => item.unlocked).map((item) => item.key);
    const newlyUnlockedKeys = unlockedKeys.filter((key) => !storedKeys.includes(key));

    if (newlyUnlockedKeys.length > 0) {
      const newPoints = allAchievements
        .filter((item) => newlyUnlockedKeys.includes(item.key))
        .reduce((sum, item) => sum + item.points, 0);
      const nextPoints = addAchievementPoints(newPoints);
      setAchievementPoints(nextPoints);
      saveUnlockedAchievementKeys([...storedKeys, ...newlyUnlockedKeys]);
    } else {
      setAchievementPoints(loadAchievementPoints());
    }

    setAchievements(allAchievements);
  };

  useEffect(() => {
    const storedUserId = localStorage.getItem("userId");
    if (storedUserId) {
      void loadUser(Number(storedUserId));
    }
  }, []);

  const handleFieldChange = (field: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [field]: value }));
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

  const handleRecharge = async (plan: { points: number; price: number }) => {
    if (!user) {
      return;
    }

    try {
      await api.post(`/users/${user.id}/recharge`, {
        points: plan.points,
        price: plan.price,
      });
      await loadUser(user.id);
      setMessage(`已完成 ${plan.points} 點充值。`);
    } catch (error) {
      console.error(error);
      setMessage("充值失敗，請稍後再試。");
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
            <span>連續登入</span>
            <strong>{loginMeta.consecutiveLoginDays} 天</strong>
            <p>維持習慣，連續登入 7 天即可獲得《學習堅持者》。</p>
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
          <p>依據影片上傳、Quiz 完成題數與登入天數，自動解鎖成就徽章。</p>
        </div>
        <div className="achievement-grid">
          {achievements.map((item) => (
            <article key={item.key} className={`achievement-card ${item.unlocked ? 'unlocked' : 'locked'}`}>
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
              <div className="achievement-progress">
                <span>{item.unlocked ? '已解鎖' : '進度'}</span>
                <strong>{item.progress}</strong>
              </div>
            </article>
          ))}
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
              <p>選擇方案後會立即更新到帳戶。</p>
            </div>

            <div className="profile-plan-grid">
              {rechargePlans.map((plan) => (
                <article key={plan.title} className="profile-plan-card">
                  <div>
                    <div className="profile-plan-points">{plan.points} points</div>
                    <h3>{plan.title}</h3>
                    <p>{plan.caption}</p>
                  </div>
                  <button className="page-primary-button" onClick={() => void handleRecharge(plan)}>
                    Recharge
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
                <button className="page-primary-button" onClick={() => void handleSave()} disabled={saving}>
                  {saving ? "Saving..." : "Save Changes"}
                </button>
                <button className="page-secondary-button" onClick={resetForm}>Reset</button>
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
                  <th>Amount</th>
                  <th>Points</th>
                  <th>Payment</th>
                </tr>
              </thead>
              <tbody>
                {history.map((record) => (
                  <tr key={record.order_id}>
                    <td>{record.date}</td>
                    <td>{record.order_id}</td>
                    <td>{record.amount}</td>
                    <td>{record.points ?? "-"}</td>
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
