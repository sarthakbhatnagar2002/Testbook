import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../lib/api";
import type { Test } from "../../lib/types";

function toLocalInputValue(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function TeacherTestsPage() {
  const [tests, setTests] = useState<Test[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);

  function load() {
    api
      .get<Test[]>("/tests")
      .then(setTests)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load tests"));
  }

  useEffect(load, []);

  async function update(id: string, patch: Record<string, unknown>) {
    try {
      await api.patch(`/tests/${id}`, patch);
      load();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Could not update the test");
    }
  }

  function copyKey(key: string) {
    navigator.clipboard?.writeText(key).catch(() => void 0);
  }

  const visible = (tests ?? []).filter((t) => showArchived || !t.archived);

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Tests</h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-1 text-sm text-gray-600">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
            Show archived
          </label>
          <Link to="/teacher/tests/new" className="rounded bg-[#20bcd8] px-4 py-2 font-medium text-white">
            New test
          </Link>
        </div>
      </div>
      {error && <p className="mb-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {!tests ? (
        <p className="text-gray-500">Loading…</p>
      ) : visible.length === 0 ? (
        <p className="text-gray-500">No tests yet.</p>
      ) : (
        <ul className="space-y-4">
          {visible.map((t) => (
            <li
              key={t.id}
              className={`rounded-lg border bg-white p-4 ${t.archived ? "border-gray-200 opacity-60" : "border-gray-200"}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900">{t.title}</p>
                    {t.archived && (
                      <span className="rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-600">
                        Archived
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-gray-500">
                    {t.sections.length} section{t.sections.length === 1 ? "" : "s"} ·{" "}
                    {t.sections.reduce((sum, s) => sum + s.question_count, 0)} questions ·{" "}
                    {t.total_duration_mins} min total · +{t.marks_correct} / {t.marks_wrong} marking
                  </p>
                  <p className="mt-1 text-xs text-gray-400">
                    {t.sections.map((s) => `${s.title} (${s.duration_mins}m)`).join(" · ")}
                  </p>
                  <button
                    onClick={() => copyKey(t.room_key)}
                    title="Click to copy"
                    className="mt-2 inline-flex items-center gap-1.5 rounded border border-gray-300 px-2 py-1 text-xs font-mono text-gray-700 hover:border-[#176b87]"
                  >
                    Room key: <span className="font-bold tracking-wider">{t.room_key}</span>
                  </button>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <Link to={`/teacher/tests/${t.id}/results`} className="text-sm text-[#176b87] underline">
                    Results
                  </Link>
                  <label className="flex items-center gap-1 text-sm">
                    <input
                      type="checkbox"
                      checked={t.published}
                      onChange={(e) => update(t.id, { published: e.target.checked })}
                    />
                    Published
                  </label>
                  <button
                    onClick={() => update(t.id, { archived: !t.archived })}
                    className="text-sm text-gray-500 underline hover:text-gray-700"
                  >
                    {t.archived ? "Unarchive" : "Archive"}
                  </button>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-end gap-4 border-t border-gray-100 pt-3 text-sm">
                <label className="flex flex-col">
                  Start time
                  <input
                    type="datetime-local"
                    defaultValue={toLocalInputValue(t.start_time)}
                    onBlur={(e) =>
                      e.target.value && update(t.id, { start_time: new Date(e.target.value).toISOString() })
                    }
                    className="mt-1 rounded border border-gray-300 px-2 py-1"
                  />
                </label>
                <label className="flex flex-col">
                  End time (optional)
                  <input
                    type="datetime-local"
                    defaultValue={toLocalInputValue(t.end_time)}
                    onBlur={(e) =>
                      e.target.value && update(t.id, { end_time: new Date(e.target.value).toISOString() })
                    }
                    className="mt-1 rounded border border-gray-300 px-2 py-1"
                  />
                </label>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
