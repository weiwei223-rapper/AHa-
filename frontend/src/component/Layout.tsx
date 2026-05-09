import { NavLink, Outlet, useNavigate } from "react-router-dom";
import logoIcon from "../assets/logo_v3.jpg";

interface LayoutProps {
  onLogout?: () => void;
}

const navClassName = ({ isActive }: { isActive: boolean }) =>
  `workspace-nav-link ${isActive ? "active" : ""}`;

const Layout = ({ onLogout }: LayoutProps) => {
  const navigate = useNavigate();

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

        <div className="workspace-nav-group">
          <NavLink to="/" className={navClassName}>Home</NavLink>
          <NavLink to="/Video" className={navClassName}>Video</NavLink>
          <NavLink to="/Profile" className={navClassName}>Profile</NavLink>
          <NavLink to="/Quiz" className={navClassName}>Quiz</NavLink>
          <NavLink to="/Review" className={navClassName}>Review</NavLink>
        </div>

        <button onClick={handleLogout} className="workspace-logout-button">
          Logout
        </button>
      </nav>

      <main className="workspace-main">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
