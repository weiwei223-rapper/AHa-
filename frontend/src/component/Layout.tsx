import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate, Link } from "react-router-dom";
import logoIcon from "../assets/logo_v3.jpg";
import { usePoints } from "../context/PointsContext";

interface LayoutProps {
  onLogout?: () => void;
}

const navClassName = ({ isActive }: { isActive: boolean }) =>
  `workspace-nav-link ${isActive ? "active" : ""}`;

const Layout = ({ onLogout }: LayoutProps) => {
  const navigate = useNavigate();
  const { availablePoints } = usePoints();

  const handleLogout = () => {
    onLogout?.();
    navigate("/");
    window.location.reload();
  };

  return (
    <div className="workspace-shell">
      <nav className="workspace-sidebar">
        <div className="workspace-brand">
          <img src={logoIcon} alt="Logo" className="workspace-brand-logo" />
          <div>
            <strong>AHa</strong>
            <span>AI Learning Hub</span>
          </div>
        </div>

        <div className="workspace-points-info" style={{ padding: '15px', borderBottom: '1px solid #ffffff11', marginBottom: '10px' }}>
          <div style={{ color: '#8da3bd', fontSize: '12px' }}>Available Points</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: availablePoints === 0 ? '#fb7185' : '#4ade80' }}>
            {availablePoints}
          </div>
          {availablePoints === 0 && (
            <div style={{ color: '#fb7185', fontSize: '11px', marginTop: '5px' }}>
              ⚠️ 點數為 0，請記得儲值以使用 AI 功能
            </div>
          )}
        </div>

        <div className="workspace-nav-group">
          <NavLink to="/" className={navClassName}>Home</NavLink>
          <NavLink to="/Tutorial" className={navClassName}>Tutorial</NavLink>
          <NavLink to="/Video" className={navClassName}>Video</NavLink>
          <NavLink to="/Quiz" className={navClassName}>Quiz</NavLink>
          <NavLink to="/Chat" className={navClassName}>Chat</NavLink>
          <NavLink to="/UnfinishedTest" className={navClassName}>Unfinished Test</NavLink>
          <NavLink to="/Review" className={navClassName}>Review</NavLink>
          <NavLink to="/Profile" className={navClassName}>Profile</NavLink>
        </div>

        <div className="workspace-sidebar-footer">
          <button onClick={handleLogout} className="workspace-logout-button">
            Logout
          </button>
        </div>
      </nav>

      <main className="workspace-main">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
