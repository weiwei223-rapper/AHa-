//import  React from "react";
import { useEffect, useState } from "react";
import "./App.css"
import Home from "./pages/Home.tsx";
import Video from "./pages/Video.tsx";
import Layout from "./component/Layout.tsx";
import ChatFloatingWidget from "./component/ChatFloatingWidget.tsx";
import Profile from "./pages/Profile.tsx"
import Quiz from "./pages/Quiz.tsx";
import Review from "./pages/Review.tsx";
import AuthPage from "./pages/AuthPage.tsx";
import Chat from "./pages/Chat.tsx";
import {Route,Routes} from "react-router-dom";
import { updateLoginMetaForToday } from "./utils/achievement";
import { ChatProvider } from "./context/ChatContext.tsx";

function App (){
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [userInfo, setUserInfo] = useState<any>(null);

    useEffect(() => {
        // Check if user is already logged in
        const userId = localStorage.getItem('userId');
        const userData = localStorage.getItem('userData');
        
        if (userId && userData) {
            updateLoginMetaForToday();
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
        <ChatProvider>
            <Routes>
                <Route element={<Layout onLogout={handleLogout} />}>
                <Route path="/" element={<Home name={userInfo?.name}/>} />
                <Route path="/Video" element={<Video VideoName={"python"}/>} />
                <Route path="/Profile" element={<Profile />} />
                <Route path="/Quiz" element={<Quiz />} />
                <Route path="/Review" element={<Review />} />
                <Route path="/Chat" element={<Chat />} />
              </Route>
            </Routes>
            <ChatFloatingWidget />
        </ChatProvider>
    )
}
export default App
