//import  React from "react";
import { useEffect, useState } from "react";
import "./App.css"
import Home from "./pages/Home.tsx";
import Video from "./pages/Video.tsx";
import Layout from "./component/Layout.tsx";
import Profile from "./pages/Profile.tsx"
import Quiz from "./pages/Quiz.tsx";
import AuthPage from "./pages/AuthPage.tsx";
import {Route,Routes, Navigate} from "react-router-dom";

function App (){
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [userInfo, setUserInfo] = useState<any>(null);

    useEffect(() => {
        // Check if user is already logged in
        const userId = localStorage.getItem('userId');
        const userData = localStorage.getItem('userData');
        
        if (userId && userData) {
            setIsAuthenticated(true);
            setUserInfo(JSON.parse(userData));
        }
    }, []);

    const handleLogout = () => {
        localStorage.removeItem('userId');
        localStorage.removeItem('userData');
        setIsAuthenticated(false);
        setUserInfo(null);
    };

    if (!isAuthenticated) {
        return <AuthPage />;
    }

    return(
        <>
            <Routes>
                <Route element={<Layout onLogout={handleLogout} />}>
                <Route path="/" element={<Home name={userInfo?.name}/>} />
                <Route path="/Video" element={<Video VideoName={"python"}/>} />
                <Route path="/Profile" element={<Profile />} />
                <Route path="/Quiz" element={<Quiz />} />
              </Route>
            </Routes>
        </>
    )
}
export default App