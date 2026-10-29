import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      navigate("/subjects");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0b0f14] px-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-2xl border border-gray-800 bg-gray-900 p-8">
        <p className="mb-6 text-sm text-gray-400">Log in to keep practicing.</p>
        {error && <p className="mb-4 rounded-lg bg-red-950/40 px-4 py-2.5 text-sm text-red-300">{error}</p>}
        <label className="mb-3 block text-sm text-gray-300">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 outline-none transition-colors focus:border-[#20bcd8]"
          />
        </label>
        <label className="mb-4 block text-sm text-gray-300">
          Password
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 outline-none transition-colors focus:border-[#20bcd8]"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-[#20bcd8] py-2 font-semibold text-white transition-colors hover:bg-[#1ba8c2] disabled:opacity-60"
        >
          {busy ? "Logging in…" : "Log in"}
        </button>
        <p className="mt-4 text-center text-sm text-gray-400">
          No account?{" "}
          <Link to="/register" className="font-medium text-[#20bcd8] hover:underline">
            Register
          </Link>
        </p>
      </form>
    </div>
  );
}
