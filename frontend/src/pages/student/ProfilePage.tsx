import { useEffect, useState } from "react";
import { api, ApiError } from "../../lib/api";
import type { Profile } from "../../lib/types";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Profile>("/profile")
      .then(setProfile)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load profile"));
  }, []);

  if (error) return <p className="m-6 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  if (!profile) return <p className="m-6 text-gray-500">Loading…</p>;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-1 text-xl font-semibold text-gray-900">{profile.name}</h1>
      <p className="mb-6 text-sm text-gray-500">
        {profile.email} · {profile.role}
      </p>

      <div className="mb-8 grid grid-cols-3 gap-4">
        <Stat label="Tests taken" value={profile.tests_taken} />
        <Stat label="Average score" value={profile.average_score} />
        <Stat label="Overall accuracy" value={`${profile.overall_accuracy}%`} />
      </div>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Recent scores</h2>
        {profile.recent_scores.length === 0 ? (
          <p className="text-gray-500">No submitted tests yet.</p>
        ) : (
          <ul className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
            {profile.recent_scores.map((s, i) => (
              <li key={i} className="flex items-center justify-between px-4 py-2 text-sm">
                <span>{s.test_title}</span>
                <span className="text-gray-400">{s.submitted_at ? new Date(s.submitted_at).toLocaleDateString() : ""}</span>
                <span className="font-medium">{s.score}</span>
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
    <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
      <p className="text-2xl font-semibold text-[#176b87]">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}
