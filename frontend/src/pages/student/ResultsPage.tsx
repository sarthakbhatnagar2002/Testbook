import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, resolveImageUrl } from "../../lib/api";
import type { AttemptResult } from "../../lib/types";

export default function ResultsPage() {
  const { attemptId } = useParams();
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!attemptId) return;
    api
      .get<AttemptResult>(`/student/attempts/${attemptId}/result`)
      .then(setResult)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load results"));
  }, [attemptId]);

  if (error) return <p className="m-6 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  if (!result) return <p className="m-6 text-gray-500">Loading…</p>;

  return (
    <div className="mx-auto max-w-3xl p-6">
      <Link to="/tests" className="text-sm text-[#176b87] underline">
        ← Back to tests
      </Link>
      <h1 className="mb-1 mt-2 text-xl font-semibold text-gray-900">{result.test_title}</h1>
      <p className="mb-6 text-sm text-gray-500">
        Score {result.score} · {result.correct_count} correct · {result.wrong_count} wrong ·{" "}
        {result.skipped_count} skipped
      </p>

      <ol className="space-y-5">
        {result.answers.map((a, i) => (
          <li key={a.question.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="font-medium text-gray-900">
              {i + 1}. {a.question.text}
            </p>
            {a.question.image_url && (
              <img src={resolveImageUrl(a.question.image_url)} alt="" className="mt-2 max-h-48 rounded" />
            )}
            <ul className="mt-3 space-y-1">
              {a.question.options.map((o) => {
                const isSelected = o.id === a.selected_option_id;
                const isCorrect = o.is_correct;
                return (
                  <li
                    key={o.id}
                    className={`rounded px-3 py-1.5 text-sm ${
                      isCorrect
                        ? "bg-green-50 text-green-800"
                        : isSelected
                          ? "bg-red-50 text-red-800"
                          : "text-gray-700"
                    }`}
                  >
                    {o.text}
                    {isCorrect ? " ✓" : isSelected ? " ✗ (your answer)" : ""}
                    {o.image_url && (
                      <img src={resolveImageUrl(o.image_url)} alt="" className="mt-1 max-h-16 rounded" />
                    )}
                  </li>
                );
              })}
            </ul>
            {a.question.explanation && (
              <p className="mt-3 rounded bg-gray-50 px-3 py-2 text-sm text-gray-600">{a.question.explanation}</p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
