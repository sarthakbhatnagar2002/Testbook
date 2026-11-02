import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { colorForSubject } from "../lib/subjectColors";
import type { Chapter, Subject } from "../lib/types";

export default function ChaptersPage() {
  const { subjectId } = useParams();
  const [subject, setSubject] = useState<Subject | null>(null);
  const [chapters, setChapters] = useState<Chapter[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!subjectId) return;
    api
      .get<Subject[]>("/subjects")
      .then((all) => setSubject(all.find((s) => s.id === subjectId) ?? null));
    api
      .get<Chapter[]>(`/subjects/${subjectId}/chapters`)
      .then(setChapters)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load chapters"));
  }, [subjectId]);

  const color = colorForSubject(subject?.name ?? "");

  return (
    <div className="mx-auto max-w-3xl p-6 sm:p-8">
      <Link to="/subjects" className="text-sm font-medium text-[#20bcd8] hover:underline">
        ← All subjects
      </Link>
      <div className="mb-6 mt-2">
        <h1 className="text-2xl font-bold tracking-tight text-gray-100">{subject?.name ?? "Subject"}</h1>
        <p className="mt-1 text-sm text-gray-400">Pick a chapter to start practicing.</p>
      </div>

      {error && <p className="mb-4 rounded-lg bg-red-950/40 px-4 py-2.5 text-sm text-red-300">{error}</p>}

      {!chapters ? (
        <ChaptersSkeleton />
      ) : chapters.length === 0 ? (
        <p className="rounded-lg border border-dashed border-gray-700 p-8 text-center text-gray-400">
          No chapters here yet.
        </p>
      ) : (
        <ul className="space-y-2">
          {chapters.map((c) => {
            const progress = c.question_count > 0 ? Math.round((c.solved_count / c.question_count) * 100) : 0;
            return (
              <li key={c.id}>
                <Link
                  to={`/subjects/${subjectId}/chapters/${c.id}`}
                  className="flex items-center justify-between gap-4 rounded-xl border border-gray-800 bg-gray-900 p-4 transition-colors hover:border-gray-700"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-gray-100">{c.name}</p>
                    <div className="mt-2 flex items-center gap-3">
                      <div className="h-1.5 w-32 overflow-hidden rounded-full bg-gray-800">
                        <div
                          className={`h-full rounded-full ${color.bar} transition-[width] duration-500`}
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                      <span className="shrink-0 text-xs text-gray-400">
                        {c.solved_count}/{c.question_count} solved
                      </span>
                    </div>
                  </div>
                  <span className="shrink-0 text-sm font-medium text-gray-500">{c.question_count} Qs</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function ChaptersSkeleton() {
  return (
    <ul className="space-y-2">
      {[0, 1, 2, 3].map((i) => (
        <li key={i} className="animate-pulse rounded-xl border border-gray-800 bg-gray-900 p-4">
          <div className="h-3.5 w-40 rounded bg-gray-800" />
          <div className="mt-3 h-1.5 w-32 rounded-full bg-gray-800" />
        </li>
      ))}
    </ul>
  );
}
