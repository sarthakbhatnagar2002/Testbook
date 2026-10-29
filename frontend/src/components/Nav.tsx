import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? "bg-[#176b87] text-white" : "text-gray-400 hover:bg-gray-800 hover:text-gray-100"
  }`;

export default function Nav() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <nav className="sticky top-0 z-20 flex items-center justify-between border-b border-gray-800 bg-gray-900/90 px-6 py-3 backdrop-blur">
      <div className="flex gap-1">
        <NavLink to="/subjects" className={linkClass}>
          Subjects
        </NavLink>
        <NavLink to="/profile" className={linkClass}>
          Profile
        </NavLink>
      </div>
      <div className="flex items-center gap-3 text-sm text-gray-400">
        <span>{user.name}</span>
        <button
          onClick={() => logout()}
          className="rounded-lg border border-gray-700 px-3 py-1 text-gray-300 transition-colors hover:bg-gray-800"
        >
          Log out
        </button>
      </div>
    </nav>
  );
}
