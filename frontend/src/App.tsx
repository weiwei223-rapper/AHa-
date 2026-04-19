//import  React from "react";
import "./App.css"
import Home from "./pages/Home.tsx";
import Video from "./pages/Video.tsx";
import Layout from "./component/Layout.tsx";
import Profile from "./pages/Profile.tsx"
import Quiz from "./pages/Quiz.tsx";
import {Route,Routes} from "react-router-dom";

function App (){
    return(
        <>
            <Routes>
                <Route element={<Layout />}>
                <Route path="/" element={<Home name={"wei"}/>} />
                <Route path="/Video" element={<Video VideoName={"python"}/>} />
                <Route path="/Profile" element={<Profile name={"wei"} email={"...@gmail.com"} point={10000}/>} />
                <Route path="/Quiz" element={<Quiz />} />
              </Route>
            </Routes>
        </>
    )
}
export default App