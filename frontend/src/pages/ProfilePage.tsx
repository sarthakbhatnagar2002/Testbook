import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ActivityHeatmap from "../components/ActivityHeatmap";
import { api, ApiError } from "../lib/api";
import { colorForSubject, initialsForSubject } from "../lib/subjectColors";
import { timeAgo } from "../lib/timeAgo";
import type { Profile } from "../lib/types";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [activity, setActivity] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Profile>("/profile")
      .then(setProfile)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load profile"));
    api
      .get<Record<string, number>>("/profile/activity")
      .then(setActivity)
      .catch(() => setActivity({}));
  }, []);

  if (error) return <p className="m-6 rounded-lg bg-red-950/40 px-4 py-2.5 text-sm text-red-300">{error}</p>;
  if (!profile) return <ProfileSkeleton />;

  const current = profile.currently_solving;
  const currentColor = current ? colorForSubject(current.subject_name) : null;
  const currentProgress =
    current && current.total_questions > 0
      ? Math.round((current.solved_count / current.total_questions) * 100)
      : 0;

  return (
    <div className="mx-auto max-w-4xl p-6 sm:p-8">
      <div className="mb-8 flex items-center gap-4">
        <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-[#176b87] text-xl font-bold text-white">
          {profile.name.slice(0, 1).toUpperCase()}
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-100">{profile.name}</h1>
          <p className="text-sm text-gray-400">{profile.email}</p>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Solved" value={profile.total_questions_solved} />
        <Stat label="Attempted" value={profile.total_questions_attempted} />
        <Stat label="Accuracy" value={`${profile.overall_accuracy}%`} />
        <Stat label="Subjects" value={profile.subjects.length} />
      </div>

      {activity && (
        <div className="mb-8">
          <ActivityHeatmap counts={activity} />
        </div>
      )}

      {current && currentColor && (
        <section className="mb-8">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">Currently solving</h2>
          <Link
            to={`/subjects/${current.subject_id}`}
            className={`block rounded-2xl border-2 ${currentColor.ring} ${currentColor.bg} p-5 transition-colors`}
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div
                  className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gray-950 text-lg font-bold ${currentColor.text}`}
                >
                  {initialsForSubject(current.subject_name)}
                </div>
                <div>
                  <p className={`text-lg font-semibold ${currentColor.text}`}>{current.subject_name}</p>
                  <p className="text-sm text-gray-300">
                    {current.solved_count}/{current.total_questions} solved · {current.accuracy}% accuracy
                  </p>
                  <p className="text-xs text-gray-400">
                    Last practiced {current.last_practiced_at ? timeAgo(current.last_practiced_at) : ""}
                  </p>
                </div>
              </div>
              <span
                className={`shrink-0 rounded-full bg-gray-950 px-4 py-2 text-sm font-semibold ${currentColor.text}`}
              >
                Continue →
              </span>
            </div>
            <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-black/30">
              <div className={`h-full rounded-full ${currentColor.bar}`} style={{ width: `${currentProgress}%` }} />
            </div>
          </Link>
        </section>
      )}

      <section className="mb-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">Subjects</h2>
        {profile.subjects.length === 0 ? (
          <p className="text-gray-400">No subjects yet.</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {profile.subjects.map((s) => {
              const color = colorForSubject(s.subject_name);
              const progress = s.total_questions > 0 ? Math.round((s.solved_count / s.total_questions) * 100) : 0;
              return (
                <Link
                  key={s.subject_id}
                  to={`/subjects/${s.subject_id}`}
                  className="rounded-xl border border-gray-800 bg-gray-900 p-4 transition-colors hover:border-gray-700"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="flex items-center gap-2 font-medium text-gray-100">
                      <span className={`h-2 w-2 rounded-full ${color.bar}`} />
                      {s.subject_name}
                    </span>
                    <span className="text-xs font-medium text-gray-400">{s.accuracy}% accuracy</span>
                  </div>
                  <div className="mb-1 flex justify-between text-xs text-gray-400">
                    <span>
                      {s.solved_count}/{s.total_questions} solved
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-800">
                    <div className={`h-full rounded-full ${color.bar}`} style={{ width: `${progress}%` }} />
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">Recent activity</h2>
        {profile.recent_attempts.length === 0 ? (
          <p className="text-gray-400">No attempts yet.</p>
        ) : (
          <ul className="divide-y divide-gray-800 rounded-xl border border-gray-800 bg-gray-900">
            {profile.recent_attempts.map((a, i) => (
              <li key={i} className="flex items-center gap-3 px-4 py-3 text-sm">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                    a.is_correct ? "bg-green-950/50 text-green-300" : "bg-red-950/50 text-red-300"
                  }`}
                >
                  {a.is_correct ? "✓" : "✗"}
                </span>
                <span className="flex-1 truncate text-gray-200">{a.question_text}</span>
                <span className="shrink-0 text-xs text-gray-500">{a.subject_name}</span>
                <span className="shrink-0 text-xs text-gray-500">{timeAgo(a.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4 text-center">
      <p className="text-2xl font-bold text-[#20bcd8]">{value}</p>
      <p className="text-xs text-gray-400">{label}</p>
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="mx-auto max-w-4xl animate-pulse p-6 sm:p-8">
      <div className="mb-8 flex items-center gap-4">
        <div className="h-16 w-16 rounded-full bg-gray-800" />
        <div className="space-y-2">
          <div className="h-5 w-40 rounded bg-gray-800" />
          <div className="h-3.5 w-56 rounded bg-gray-800/70" />
        </div>
      </div>
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-20 rounded-xl border border-gray-800 bg-gray-900" />
        ))}
      </div>
      <div className="h-40 rounded-2xl border border-gray-800 bg-gray-900" />
    </div>
  );
}
