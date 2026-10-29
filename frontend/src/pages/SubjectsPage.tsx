import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { colorForSubject, initialsForSubject } from "../lib/subjectColors";
import type { Subject } from "../lib/types";

export default function SubjectsPage() {
  const [subjects, setSubjects] = useState<Subject[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Subject[]>("/subjects")
      .then(setSubjects)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load subjects"));
  }, []);

  return (
    <div className="mx-auto max-w-5xl p-6 sm:p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-gray-100">Question banks</h1>
        <p className="mt-1 text-sm text-gray-400">Pick a subject below and start practicing.</p>
      </div>

      {error && <p className="mb-4 rounded-lg bg-red-950/40 px-4 py-2.5 text-sm text-red-300">{error}</p>}

      {!subjects ? (
        <SubjectsSkeleton />
      ) : subjects.length === 0 ? (
        <p className="rounded-lg border border-dashed border-gray-700 p-8 text-center text-gray-400">
          No subjects yet.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {subjects.map((s) => {
            const color = colorForSubject(s.name);
            const progress = s.question_count > 0 ? Math.round((s.solved_count / s.question_count) * 100) : 0;
            return (
              <Link
                key={s.id}
                to={`/subjects/${s.id}`}
                className="group rounded-2xl border border-gray-800 bg-gray-900 p-5 transition-colors hover:border-gray-700"
              >
                <div className="mb-4 flex items-center gap-3">
                  <div
                    className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${color.bg} ring-2 ${color.ring} text-sm font-bold ${color.text}`}
                  >
                    {initialsForSubject(s.name)}
                  </div>
                  <div>
                    <p className="font-semibold text-gray-100 group-hover:text-white">{s.name}</p>
                    <p className="text-xs text-gray-400">{s.question_count} questions</p>
                  </div>
                </div>

                <div className="mb-1.5 flex items-center justify-between text-xs text-gray-400">
                  <span>
                    {s.solved_count}/{s.question_count} solved
                  </span>
                  <span className="font-medium">{s.accuracy}% accuracy</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-800">
                  <div
                    className={`h-full rounded-full ${color.bar} transition-[width] duration-500`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SubjectsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[0, 1, 2].map((i) => (
        <div key={i} className="animate-pulse rounded-2xl border border-gray-800 bg-gray-900 p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-12 w-12 rounded-full bg-gray-800" />
            <div className="space-y-2">
              <div className="h-3.5 w-24 rounded bg-gray-800" />
              <div className="h-2.5 w-16 rounded bg-gray-800/70" />
            </div>
          </div>
          <div className="h-2 w-full rounded-full bg-gray-800" />
        </div>
      ))}
    </div>
  );
}
