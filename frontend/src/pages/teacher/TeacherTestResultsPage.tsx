import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError } from "../../lib/api";
import type { TeacherTestResults } from "../../lib/types";

export default function TeacherTestResultsPage() {
  const { testId } = useParams();
  const [results, setResults] = useState<TeacherTestResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!testId) return;
    api
      .get<TeacherTestResults>(`/tests/${testId}/results`)
      .then(setResults)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load results"));
  }, [testId]);

  if (error) return <p className="m-6 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  if (!results) return <p className="m-6 text-gray-500">Loading…</p>;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-1 text-xl font-semibold text-gray-900">{results.title}</h1>
      <p className="mb-6 text-sm text-gray-500">
        {results.attempt_count} attempts · average {results.average_score} · highest {results.highest_score}
      </p>
      {results.attempts.length === 0 ? (
        <p className="text-gray-500">No submitted attempts yet.</p>
      ) : (
        <table className="w-full border-collapse overflow-hidden rounded-lg border border-gray-200 text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-2">Student</th>
              <th className="px-4 py-2">Score</th>
              <th className="px-4 py-2">Correct</th>
              <th className="px-4 py-2">Wrong</th>
              <th className="px-4 py-2">Skipped</th>
              <th className="px-4 py-2">Submitted</th>
            </tr>
          </thead>
          <tbody>
            {results.attempts.map((a, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="px-4 py-2">
                  {a.user_name} <span className="text-gray-400">({a.user_email})</span>
                </td>
                <td className="px-4 py-2 font-medium">{a.score}</td>
                <td className="px-4 py-2">{a.correct_count}</td>
                <td className="px-4 py-2">{a.wrong_count}</td>
                <td className="px-4 py-2">{a.skipped_count}</td>
                <td className="px-4 py-2 text-gray-500">
                  {a.submitted_at ? new Date(a.submitted_at).toLocaleString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
