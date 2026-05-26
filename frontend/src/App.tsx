//import  React from "react";
import { useEffect, useState } from "react";
import "./App.css"
import Home from "./pages/Home.tsx";
import Video from "./pages/Video.tsx";
import Layout from "./component/Layout.tsx";
import AuthPage from "./pages/AuthPage.tsx";
import Quiz from "./pages/Quiz.tsx";
import Profile from "./pages/Profile.tsx";
import Review from "./pages/Review.tsx";
import Chat from "./pages/Chat.tsx";
import Tutorial from "./pages/Tutorial.tsx";
import UnfinishedTest from "./pages/UnfinishedTest.tsx";

import { Routes, Route, Navigate } from "react-router-dom";
import { ChatProvider } from "./context/ChatContext";
import { PointsProvider } from "./context/PointsContext";
import ChatFloatingWidget from "./component/ChatFloatingWidget";

function App() {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
        return !!localStorage.getItem('userId');
    });

    const handleLogout = () => {
        localStorage.removeItem('userId');
        localStorage.removeItem('userData');
        localStorage.removeItem('access_token');
        setIsAuthenticated(false);
    };

    if (!isAuthenticated) {
        return <AuthPage />;
    }

    return (
        <PointsProvider>
            <ChatProvider>
                <Routes>
                    <Route element={<Layout onLogout={handleLogout} />}>
                        <Route path="/" element={<Home />} />
                        <Route path="/Video" element={<Video />} />
                        <Route path="/Quiz" element={<Quiz />} />
                        <Route path="/Profile" element={<Profile />} />
                        <Route path="/Review" element={<Review />} />
                        <Route path="/Chat" element={<Chat />} />
                        <Route path="/Tutorial" element={<Tutorial />} />
                        <Route path="/UnfinishedTest" element={<UnfinishedTest />} />
                    </Route>
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
                <ChatFloatingWidget />
            </ChatProvider>
        </PointsProvider>
    )
}
export default App
