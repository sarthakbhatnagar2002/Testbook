import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../../lib/api";
import type { AttemptState, PreviousAttempt, StudentTest } from "../../lib/types";

export default function TestsPage() {
  const navigate = useNavigate();
  const [tests, setTests] = useState<StudentTest[] | null>(null);
  const [history, setHistory] = useState<PreviousAttempt[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const [roomKey, setRoomKey] = useState("");
  const [joinError, setJoinError] = useState<string | null>(null);
  const [joinMessage, setJoinMessage] = useState<string | null>(null);
  const [joining, setJoining] = useState(false);

  function load() {
    api
      .get<StudentTest[]>("/student/tests")
      .then(setTests)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load tests"));
    api
      .get<PreviousAttempt[]>("/student/tests/history")
      .then(setHistory)
      .catch(() => setHistory([]));
  }

  useEffect(load, []);

  async function startOrResume(testId: string) {
    setStarting(testId);
    try {
      const state = await api.post<AttemptState>("/student/attempts/start", { test_id: testId });
      navigate(`/tests/attempt/${state.attempt_id}`);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Could not start the test");
      setStarting(null);
    }
  }

  async function joinWithKey(e: FormEvent) {
    e.preventDefault();
    setJoinError(null);
    setJoinMessage(null);
    setJoining(true);
    try {
      const joined = await api.post<StudentTest>("/student/tests/join", { room_key: roomKey });
      setRoomKey("");
      if (joined.availability === "closed") {
        setJoinMessage(`"${joined.title}" was found, but its time window has already closed.`);
      } else {
        setJoinMessage(`Joined "${joined.title}".`);
      }
      load();
    } catch (err) {
      setJoinError(err instanceof ApiError ? err.message : "Could not find a test with that key");
    } finally {
      setJoining(false);
    }
  }

  const upcoming = tests?.filter((t) => t.availability === "upcoming") ?? [];
  const open = tests?.filter((t) => t.availability === "open") ?? [];

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-6 text-xl font-semibold text-gray-900">Tests</h1>
      {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <form
        onSubmit={joinWithKey}
        className="mb-8 flex items-end gap-3 rounded-lg border border-gray-200 bg-white p-4"
      >
        <label className="flex-1 text-sm">
          Join a test with its room key
          <input
            required
            value={roomKey}
            onChange={(e) => setRoomKey(e.target.value)}
            placeholder="e.g. A1B2C3"
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2 font-mono uppercase tracking-wider"
          />
        </label>
        <button
          type="submit"
          disabled={joining}
          className="rounded bg-[#20bcd8] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {joining ? "Joining…" : "Join"}
        </button>
      </form>
      {joinError && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{joinError}</p>}
      {joinMessage && <p className="mb-4 rounded bg-green-50 px-3 py-2 text-sm text-green-700">{joinMessage}</p>}

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Upcoming</h2>
        {!tests ? (
          <p className="text-gray-500">Loading…</p>
        ) : upcoming.length === 0 && open.length === 0 ? (
          <p className="text-gray-500">
            No tests joined yet — ask your teacher for a test's room key and enter it above.
          </p>
        ) : (
          <ul className="space-y-3">
            {open.map((t) => (
              <li
                key={t.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
              >
                <div>
                  <p className="font-medium text-gray-900">{t.title}</p>
                  <p className="text-sm text-gray-500">{t.total_duration_mins} min · open now</p>
                </div>
                <button
                  onClick={() => startOrResume(t.id)}
                  disabled={starting === t.id}
                  className="rounded bg-[#20bcd8] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {t.attempt_status === "in_progress" ? "Resume" : "Start"}
                </button>
              </li>
            ))}
            {upcoming.map((t) => (
              <li
                key={t.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4"
              >
                <div>
                  <p className="font-medium text-gray-900">{t.title}</p>
                  <p className="text-sm text-gray-500">
                    {t.total_duration_mins} min · opens {t.start_time ? new Date(t.start_time).toLocaleString() : "—"}
                  </p>
                </div>
                <span className="rounded bg-gray-100 px-3 py-1 text-sm text-gray-500">Not yet open</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Previous</h2>
        {!history ? (
          <p className="text-gray-500">Loading…</p>
        ) : history.length === 0 ? (
          <p className="text-gray-500">No submitted tests yet.</p>
        ) : (
          <ul className="space-y-2">
            {history.map((a) => (
              <li key={a.attempt_id}>
                <Link
                  to={`/tests/results/${a.attempt_id}`}
                  className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 hover:border-[#176b87]"
                >
                  <div>
                    <p className="font-medium text-gray-900">{a.test_title}</p>
                    <p className="text-sm text-gray-500">
                      {a.correct_count} correct · {a.wrong_count} wrong · {a.skipped_count} skipped ·{" "}
                      {a.submitted_at ? new Date(a.submitted_at).toLocaleString() : ""}
                    </p>
                  </div>
                  <span className="text-lg font-semibold text-[#176b87]">{a.score}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
