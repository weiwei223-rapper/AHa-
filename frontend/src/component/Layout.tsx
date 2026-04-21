import { Outlet, NavLink, useNavigate } from 'react-router-dom'

interface LayoutProps {
    onLogout?: () => void;
}

const Layout = ({ onLogout }: LayoutProps) => {
    const navigate = useNavigate();

    const handleLogout = () => {
        onLogout?.();
        navigate('/');
        window.location.reload();
    };

    return(
        <div>
            <nav className="sidenav">
            <NavLink
                to="./"
                className={({ isActive }) =>
                `block px-4 py-3 rounded-lg hover:bg-gray-800 transition-colors ${
                    isActive ? 'bg-gray-800 font-semibold' : ''
                }`
                }
            >Home</NavLink>
            <NavLink
                to="./Video"
                className={({ isActive }) =>
                `block px-4 py-3 rounded-lg hover:bg-gray-800 transition-colors ${
                    isActive ? 'bg-gray-800 font-semibold' : ''
                }`
                }
            >Video</NavLink>

            <NavLink
                to="./Profile"
                className={({ isActive }) =>
                `block px-4 py-3 rounded-lg hover:bg-gray-800 transition-colors ${
                    isActive ? 'bg-gray-800 font-semibold' : ''
                }`
                }
            >Profile</NavLink>
            <NavLink
                to="./Quiz"
                className={({ isActive }) =>
                `block px-4 py-3 rounded-lg hover:bg-gray-800 transition-colors ${
                    isActive ? 'bg-gray-800 font-semibold' : ''
                }`
                }
            >Quiz</NavLink>

            <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-red-600 transition-colors text-red-400 hover:text-white font-semibold mt-4"
            >
                登出
            </button>
        </nav>
            <main className="flex-1 ml-64 p-8 overflow-auto">
                <Outlet />
            </main>
        </div>

    )
}
export default Layout