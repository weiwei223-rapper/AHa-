import "./PageIndex.css";
import { useState, useEffect } from "react";

type UserStausProps = {
    name: string
}

type UserStats = {
    video_count: number;
    remaining_points: number;
    completed_quizzes: number;
    average_accuracy: number;
}

const Home = (props: UserStausProps) => {
    const [stats, setStats] = useState<UserStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        fetchUserStats();
    }, []);

    const fetchUserStats = async () => {
        try {
            // Assume user ID is 1 for now
            const res = await fetch("http://localhost:8000/users/1/stats");
            if (!res.ok) throw new Error("無法取得用戶統計");
            const data: UserStats = await res.json();
            setStats(data);
        } catch (err: any) {
            console.error(err);
            setError("載入統計資料失敗");
        } finally {
            setLoading(false);
        }
    };

    return(
        <div className="main">
            <div className="Welcome">
                <h1>
                    Welcome Back, {props.name}!
                </h1>
            </div>
            <div className="container">
                <div className="box">
                    <h3>學習影片</h3>
                    {loading ? (
                        <p>載入中...</p>
                    ) : error ? (
                        <p className="error">{error}</p>
                    ) : (
                        <p className="stat-value">{stats?.video_count || 0}</p>
                    )}
                </div>
                <div className="box">
                    <h3>剩餘點數</h3>
                    {loading ? (
                        <p>載入中...</p>
                    ) : error ? (
                        <p className="error">{error}</p>
                    ) : (
                        <p className="stat-value">{stats?.remaining_points || 0}</p>
                    )}
                </div>
                <div className="box">
                    <h3>完成測驗</h3>
                    {loading ? (
                        <p>載入中...</p>
                    ) : error ? (
                        <p className="error">{error}</p>
                    ) : (
                        <p className="stat-value">{stats?.completed_quizzes || 0}</p>
                    )}
                </div>
                <div className="box">
                    <h3>平均正確率</h3>
                    {loading ? (
                        <p>載入中...</p>
                    ) : error ? (
                        <p className="error">{error}</p>
                    ) : (
                        <p className="stat-value">{stats?.average_accuracy || 0}%</p>
                    )}
                </div>
            </div>
        </div>
    )
}
export default Home