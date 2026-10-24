import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${
    isActive ? "bg-[#176b87] text-white" : "text-gray-600 hover:bg-gray-100"
  }`;

export default function Nav() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <nav className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold text-[#176b87]">MCQ Platform</span>
        <div className="ml-6 flex gap-1">
          {user.role === "student" ? (
            <>
              <NavLink to="/profile" className={linkClass}>
                Profile
              </NavLink>
              <NavLink to="/tests" className={linkClass}>
                Tests
              </NavLink>
            </>
          ) : (
            <NavLink to="/teacher/tests" className={linkClass}>
              Tests
            </NavLink>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3 text-sm text-gray-600">
        <span>{user.name}</span>
        <button onClick={() => logout()} className="rounded-md border border-gray-300 px-3 py-1 hover:bg-gray-50">
          Log out
        </button>
      </div>
    </nav>
  );
}
