import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import api from "../api"
import "./PageIndex.css"

type UserData = {
  id: number
  name: string
  email: string
  uid: string
  points: number
}

type RechargeRecord = {
  date: string
  order_id: string
  amount: number
}

const rechargePlans = [
  { title: "NT$ 299", points: 300, price: 299, caption: "最受歡迎" },
  { title: "NT$ 599", points: 650, price: 599, caption: "超值加倍" },
  { title: "NT$ 999", points: 1100, price: 999, caption: "高額回饋" },
]

const Profile = () => {
  const [activeTab, setActiveTab] = useState<"basic" | "records">("basic")
  const [showTopup, setShowTopup] = useState(false)
  const [user, setUser] = useState<UserData | null>(null)
  const [formValues, setFormValues] = useState({
    name: "",
    password: "",
    email: "",
    uid: "",
  })
  const [history, setHistory] = useState<RechargeRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState("")

  const loadUser = async (id: number) => {
    try {
      setLoading(true)
      const userResp = await api.get(`/users/${id}`)
      const data: UserData = userResp.data
      setUser(data)
      setFormValues({
        name: data.name,
        password: "",
        email: data.email,
        uid: data.uid,
      })
      const historyResp = await api.get(`/users/${id}/recharge-records`)
      setHistory(historyResp.data)
      setMessage("")
    } catch (error) {
      setMessage("無法連線到使用者資料，請確認後端服務是否已啟動。")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const storedUserId = localStorage.getItem('userId');
    if (storedUserId) {
      const id = parseInt(storedUserId, 10);
      void loadUser(id);
    }
  }, [])

  const handleFieldChange = (field: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [field]: value }))
  }

  const resetForm = () => {
    if (user) {
      setFormValues({ name: user.name, password: "", email: user.email, uid: user.uid })
    }
  }

  const handleSave = async () => {
    if (!user) {
      return
    }

    try {
      setSaving(true)
      const payload: { name: string; email: string; password?: string } = {
        name: formValues.name,
        email: formValues.email,
      }
      if (formValues.password.trim()) {
        payload.password = formValues.password
      }
      const resp = await api.put(`/users/${user.id}`, payload)
      const updated = resp.data as UserData
      setUser(updated)
      setFormValues((prev) => ({ ...prev, password: "", name: updated.name, email: updated.email, uid: updated.uid }))
      setMessage("個人資料已儲存。")
    } catch (error) {
      setMessage("儲存失敗，請稍後再試。")
    } finally {
      setSaving(false)
    }
  }

  const handleRecharge = async (plan: { points: number; price: number }) => {
    if (!user) {
      return
    }
    try {
      await api.post(`/users/${user.id}/recharge`, {
        points: plan.points,
        price: plan.price,
      })
      await loadUser(user.id)
      setMessage(`已新增 ${plan.points} 點儲值紀錄。`)
    } catch (error) {
      setMessage("儲值失敗，請稍後重試。")
    }
  }

  const handleBack = () => {
    setShowTopup(false)
    setActiveTab("basic")
  }

  if (loading) {
    return (
      <div className="profile-page">
        <div className="profile-loading">載入中...</div>
      </div>
    )
  }

  return (
    <div className="profile-page">
      <div className="profile-header-row">
        <Link to="/" className="back-button">
          ◀ 返回首頁
        </Link>
        <div>
          <h2 className="profile-title">個人資料管理</h2>
          <div className="profile-tabs">
            <button
              type="button"
              className={`tab-button ${activeTab === "basic" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("basic")
                setShowTopup(false)
              }}
            >
              基本資料
            </button>
            <button
              type="button"
              className={`tab-button ${activeTab === "records" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("records")
                setShowTopup(false)
              }}
            >
              儲值紀錄
            </button>
          </div>
        </div>
      </div>

      {message ? <div className="message-bar">{message}</div> : null}

      {showTopup ? (
        <div className="topup-view">
          <div className="topup-banner">
            <div className="banner-label">目前點數餘額</div>
            <div className="banner-value">{user?.points ?? 0}</div>
          </div>

          <section className="topup-section">
            <h3>儲值方案</h3>
            <div className="plan-cards">
              {rechargePlans.map((plan) => (
                <div key={plan.title} className="plan-card">
                  <div className="plan-copy">
                    <strong>{plan.points} 點</strong>
                    <span>{plan.title}</span>
                    <small>{plan.caption}</small>
                  </div>
                  <button
                    type="button"
                    className="action-button blue"
                    onClick={() => handleRecharge(plan)}
                  >
                    立即儲值
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section className="history-section">
            <h3>儲值紀錄</h3>
            <div className="history-table-wrap">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>訂單編號</th>
                    <th>交易金額</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((record) => (
                    <tr key={record.order_id}>
                      <td>{record.date}</td>
                      <td>{record.order_id}</td>
                      <td>{record.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="bottom-actions">
            <button type="button" className="secondary-btn" onClick={handleBack}>
              返回基本資料
            </button>
          </div>
        </div>
      ) : activeTab === "basic" ? (
        <div className="basic-section">
          <div className="profile-card">
            <div className="profile-summary">
              <div className="avatar">{user?.name.charAt(0).toUpperCase()}</div>
              <div className="account-info">
                <div className="account-name">{user?.name}</div>
                <div className="account-email">{user?.email}</div>
              </div>
            </div>

            <div className="profile-form">
              <label>
                姓名
                <input
                  value={formValues.name}
                  onChange={(e) => handleFieldChange("name", e.target.value)}
                />
              </label>
              <label>
                密碼
                <input
                  type="password"
                  value={formValues.password}
                  onChange={(e) => handleFieldChange("password", e.target.value)}
                  placeholder="留空則維持原密碼"
                />
              </label>
              <label>
                電子郵件
                <input
                  type="email"
                  value={formValues.email}
                  onChange={(e) => handleFieldChange("email", e.target.value)}
                />
              </label>
              <label>
                UID
                <input value={formValues.uid} readOnly />
              </label>
              <div className="points-row">
                <div>
                  <span className="field-label">目前點數</span>
                  <div className="points-value-small">{user?.points ?? 0}</div>
                </div>
                <button type="button" className="topup-button" onClick={() => setShowTopup(true)}>
                  儲值點數
                </button>
              </div>
            </div>
          </div>

          <div className="action-row">
            <button type="button" className="primary-btn" onClick={handleSave} disabled={saving}>
              {saving ? "儲存中..." : "儲存變更"}
            </button>
            <button type="button" className="secondary-btn" onClick={resetForm}>
              取消
            </button>
          </div>
        </div>
      ) : (
        <div className="record-section">
          <h3>儲值紀錄</h3>
          <div className="history-table-wrap">
            <table className="history-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>訂單編號</th>
                  <th>交易金額</th>
                </tr>
              </thead>
              <tbody>
                {history.map((record) => (
                  <tr key={record.order_id}>
                    <td>{record.date}</td>
                    <td>{record.order_id}</td>
                    <td>{record.amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default Profile
