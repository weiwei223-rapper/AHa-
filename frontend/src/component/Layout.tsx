import { Outlet, NavLink } from 'react-router-dom'

const Layout = () => {
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

        </nav>
            <main className="flex-1 ml-64 p-8 overflow-auto">
                <Outlet />
            </main>
        </div>

    )
}
export default Layout