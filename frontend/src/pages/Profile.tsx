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

const ECPAY_MERCHANT_ID = "2000132";
const ECPAY_HASH_KEY = "5294y06JbISpM5x9";
const ECPAY_HASH_IV = "v77hoKGq4kWxNNIS";

const md5 = (message: string): string => {
  const rotateLeft = (x: number, c: number) => (x << c) | (x >>> (32 - c));
  const addUnsigned = (x: number, y: number) => {
    const x4 = x & 0x40000000;
    const y4 = y & 0x40000000;
    const x8 = x & 0x80000000;
    const y8 = y & 0x80000000;
    const result = (x & 0x3FFFFFFF) + (y & 0x3FFFFFFF);
    if (x4 & y4) return result ^ 0x80000000 ^ x8 ^ y8;
    if (x4 | y4) {
      if (result & 0x40000000) return result ^ 0xC0000000 ^ x8 ^ y8;
      return result ^ 0x40000000 ^ x8 ^ y8;
    }
    return result ^ x8 ^ y8;
  };

  const F = (x: number, y: number, z: number) => (x & y) | (~x & z);
  const G = (x: number, y: number, z: number) => (x & z) | (y & ~z);
  const H = (x: number, y: number, z: number) => x ^ y ^ z;
  const I = (x: number, y: number, z: number) => y ^ (x | ~z);

  const FF = (a: number, b: number, c: number, d: number, x: number, s: number, ac: number) =>
    addUnsigned(rotateLeft(addUnsigned(addUnsigned(a, F(b, c, d)), addUnsigned(x, ac)), s), b);
  const GG = (a: number, b: number, c: number, d: number, x: number, s: number, ac: number) =>
    addUnsigned(rotateLeft(addUnsigned(addUnsigned(a, G(b, c, d)), addUnsigned(x, ac)), s), b);
  const HH = (a: number, b: number, c: number, d: number, x: number, s: number, ac: number) =>
    addUnsigned(rotateLeft(addUnsigned(addUnsigned(a, H(b, c, d)), addUnsigned(x, ac)), s), b);
  const II = (a: number, b: number, c: number, d: number, x: number, s: number, ac: number) =>
    addUnsigned(rotateLeft(addUnsigned(addUnsigned(a, I(b, c, d)), addUnsigned(x, ac)), s), b);

  const convertToWordArray = (str: string) => {
    const lMessageLength = str.length;
    let lNumberOfWords = ((lMessageLength + 8) >>> 6) + 1;
    const lWordArray = new Array<number>(lNumberOfWords * 16).fill(0);
    let bytePosition = 0;
    for (let i = 0; i < lMessageLength; i++) {
      const code = str.charCodeAt(i);
      lWordArray[bytePosition >>> 2] |= (code & 0xFF) << ((bytePosition % 4) * 8);
      bytePosition++;
    }
    lWordArray[bytePosition >>> 2] |= 0x80 << ((bytePosition % 4) * 8);
    lWordArray[lNumberOfWords * 16 - 2] = lMessageLength * 8;
    return lWordArray;
  };

  const wordToHex = (lValue: number) => {
    let wordToHexValue = "";
    for (let i = 0; i <= 3; i++) {
      const byte = (lValue >>> (i * 8)) & 255;
      let hex = byte.toString(16);
      if (hex.length < 2) hex = "0" + hex;
      wordToHexValue += hex;
    }
    return wordToHexValue;
  };

  const utf8Encode = (str: string) =>
    unescape(encodeURIComponent(str));

  const x = convertToWordArray(utf8Encode(message));
  let a = 0x67452301;
  let b = 0xEFCDAB89;
  let c = 0x98BADCFE;
  let d = 0x10325476;

  for (let k = 0; k < x.length; k += 16) {
    const AA = a;
    const BB = b;
    const CC = c;
    const DD = d;

    a = FF(a, b, c, d, x[k + 0], 7, 0xD76AA478);
    d = FF(d, a, b, c, x[k + 1], 12, 0xE8C7B756);
    c = FF(c, d, a, b, x[k + 2], 17, 0x242070DB);
    b = FF(b, c, d, a, x[k + 3], 22, 0xC1BDCEEE);
    a = FF(a, b, c, d, x[k + 4], 7, 0xF57C0FAF);
    d = FF(d, a, b, c, x[k + 5], 12, 0x4787C62A);
    c = FF(c, d, a, b, x[k + 6], 17, 0xA8304613);
    b = FF(b, c, d, a, x[k + 7], 22, 0xFD469501);
    a = FF(a, b, c, d, x[k + 8], 7, 0x698098D8);
    d = FF(d, a, b, c, x[k + 9], 12, 0x8B44F7AF);
    c = FF(c, d, a, b, x[k + 10], 17, 0xFFFF5BB1);
    b = FF(b, c, d, a, x[k + 11], 22, 0x895CD7BE);
    a = FF(a, b, c, d, x[k + 12], 7, 0x6B901122);
    d = FF(d, a, b, c, x[k + 13], 12, 0xFD987193);
    c = FF(c, d, a, b, x[k + 14], 17, 0xA679438E);
    b = FF(b, c, d, a, x[k + 15], 22, 0x49B40821);

    a = GG(a, b, c, d, x[k + 1], 5, 0xF61E2562);
    d = GG(d, a, b, c, x[k + 6], 9, 0xC040B340);
    c = GG(c, d, a, b, x[k + 11], 14, 0x265E5A51);
    b = GG(b, c, d, a, x[k + 0], 20, 0xE9B6C7AA);
    a = GG(a, b, c, d, x[k + 5], 5, 0xD62F105D);
    d = GG(d, a, b, c, x[k + 10], 9, 0x02441453);
    c = GG(c, d, a, b, x[k + 15], 14, 0xD8A1E681);
    b = GG(b, c, d, a, x[k + 4], 20, 0xE7D3FBC8);
    a = GG(a, b, c, d, x[k + 9], 5, 0x21E1CDE6);
    d = GG(d, a, b, c, x[k + 14], 9, 0xC33707D6);
    c = GG(c, d, a, b, x[k + 3], 14, 0xF4D50D87);
    b = GG(b, c, d, a, x[k + 8], 20, 0x455A14ED);
    a = GG(a, b, c, d, x[k + 13], 5, 0xA9E3E905);
    d = GG(d, a, b, c, x[k + 2], 9, 0xFCEFA3F8);
    c = GG(c, d, a, b, x[k + 7], 14, 0x676F02D9);
    b = GG(b, c, d, a, x[k + 12], 20, 0x8D2A4C8A);

    a = HH(a, b, c, d, x[k + 5], 4, 0xFFFA3942);
    d = HH(d, a, b, c, x[k + 8], 11, 0x8771F681);
    c = HH(c, d, a, b, x[k + 11], 16, 0x6D9D6122);
    b = HH(b, c, d, a, x[k + 14], 23, 0xFDE5380C);
    a = HH(a, b, c, d, x[k + 1], 4, 0xA4BEEA44);
    d = HH(d, a, b, c, x[k + 4], 11, 0x4BDECFA9);
    c = HH(c, d, a, b, x[k + 7], 16, 0xF6BB4B60);
    b = HH(b, c, d, a, x[k + 10], 23, 0xBEBFBC70);
    a = HH(a, b, c, d, x[k + 13], 4, 0x289B7EC6);
    d = HH(d, a, b, c, x[k + 0], 11, 0xEAA127FA);
    c = HH(c, d, a, b, x[k + 3], 16, 0xD4EF3085);
    b = HH(b, c, d, a, x[k + 6], 23, 0x04881D05);
    a = HH(a, b, c, d, x[k + 9], 4, 0xD9D4D039);
    d = HH(d, a, b, c, x[k + 12], 11, 0xE6DB99E5);
    c = HH(c, d, a, b, x[k + 15], 16, 0x1FA27CF8);
    b = HH(b, c, d, a, x[k + 2], 23, 0xC4AC5665);

    a = II(a, b, c, d, x[k + 0], 6, 0xF4292244);
    d = II(d, a, b, c, x[k + 7], 10, 0x432AFF97);
    c = II(c, d, a, b, x[k + 14], 15, 0xAB9423A7);
    b = II(b, c, d, a, x[k + 5], 21, 0xFC93A039);
    a = II(a, b, c, d, x[k + 12], 6, 0x655B59C3);
    d = II(d, a, b, c, x[k + 3], 10, 0x8F0CCC92);
    c = II(c, d, a, b, x[k + 10], 15, 0xFFEFF47D);
    b = II(b, c, d, a, x[k + 1], 21, 0x85845DD1);
    a = II(a, b, c, d, x[k + 8], 6, 0x6FA87E4F);
    d = II(d, a, b, c, x[k + 15], 10, 0xFE2CE6E0);
    c = II(c, d, a, b, x[k + 6], 15, 0xA3014314);
    b = II(b, c, d, a, x[k + 13], 21, 0x4E0811A1);
    a = II(a, b, c, d, x[k + 4], 6, 0xF7537E82);
    d = II(d, a, b, c, x[k + 11], 10, 0xBD3AF235);
    c = II(c, d, a, b, x[k + 2], 15, 0x2AD7D2BB);
    b = II(b, c, d, a, x[k + 9], 21, 0xEB86D391);

    a = addUnsigned(a, AA);
    b = addUnsigned(b, BB);
    c = addUnsigned(c, CC);
    d = addUnsigned(d, DD);
  }

  return (wordToHex(a) + wordToHex(b) + wordToHex(c) + wordToHex(d)).toLowerCase();
};

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

  const generateCheckMacValue = (params: Record<string, string | number>) => {
    const urlEncoded = Object.keys(params)
      .sort()
      .map((key) => `${key}=${params[key]}`)
      .join("&");

    const raw = `HashKey=${ECPAY_HASH_KEY}&${urlEncoded}&HashIV=${ECPAY_HASH_IV}`;
    const encoded = encodeURIComponent(raw)
      .toLowerCase()
      .replace(/%20/g, "+")
      .replace(/%21/g, "!")
      .replace(/%28/g, "(")
      .replace(/%29/g, ")")
      .replace(/%2a/g, "*")
      .replace(/%2d/g, "-")
      .replace(/%2e/g, ".")
      .replace(/%5f/g, "_")
      .replace(/%7e/g, "~");

    return md5(encoded).toUpperCase();
  };

  const submitEcpay = async (params: Record<string, string | number>) => {
    const checkMacValue = generateCheckMacValue(params);
    const form = document.createElement("form");
    form.method = "POST";
    form.action = "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5";
    form.style.display = "none";

    Object.entries({ ...params, CheckMacValue: checkMacValue }).forEach(([key, value]) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = key;
      input.value = String(value);
      form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
  };

  const handleRecharge = async (plan: { points: number; price: number }) => {
    if (!user) {
      return;
    }

    const now = new Date();
    const tradeDate = `${now.getFullYear()}/${String(now.getMonth() + 1).padStart(2, "0")}/${String(now.getDate()).padStart(2, "0")} ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;
    const merchantTradeNo = `TOPUP${Date.now()}`;

    await submitEcpay({
      MerchantID: ECPAY_MERCHANT_ID,
      MerchantTradeNo: merchantTradeNo,
      MerchantTradeDate: tradeDate,
      PaymentType: "aio",
      TotalAmount: plan.price,
      TradeDesc: "AHA 點數充值",
      ItemName: `${plan.points} 點`,
      ReturnURL: `${window.location.origin}/profile`,
      ClientBackURL: `${window.location.origin}/profile`,
      ChoosePayment: "ALL",
      EncryptType: 1,
    });
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
              <p>按下方案後，系統會導向綠界科技付款頁面進行儲值。</p>
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
                    前往綠界付款
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
