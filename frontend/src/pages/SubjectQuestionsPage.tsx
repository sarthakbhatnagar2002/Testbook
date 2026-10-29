import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, resolveImageUrl } from "../lib/api";
import { filterQuestions, type QuestionFilter } from "../lib/questionFilter";
import type { QuestionListItem, QuestionStatus, Subject } from "../lib/types";

const STATUS_BADGE: Record<QuestionStatus, string> = {
  not_attempted: "bg-gray-800 text-gray-400",
  correct: "bg-green-950/50 text-green-300",
  incorrect: "bg-red-950/50 text-red-300",
};

const STATUS_LABEL: Record<QuestionStatus, string> = {
  not_attempted: "Not attempted",
  correct: "Solved",
  incorrect: "Incorrect",
};

const TABS: { key: QuestionFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "unsolved", label: "Unsolved" },
  { key: "solved", label: "Solved" },
  { key: "incorrect", label: "Incorrect" },
];

export default function SubjectQuestionsPage() {
  const { subjectId } = useParams();
  const navigate = useNavigate();
  const [subject, setSubject] = useState<Subject | null>(null);
  const [questions, setQuestions] = useState<QuestionListItem[] | null>(null);
  const [filter, setFilter] = useState<QuestionFilter>("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!subjectId) return;
    api
      .get<Subject[]>("/subjects")
      .then((all) => setSubject(all.find((s) => s.id === subjectId) ?? null));
    api
      .get<QuestionListItem[]>(`/subjects/${subjectId}/questions`)
      .then(setQuestions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load questions"));
  }, [subjectId]);

  const visible = useMemo(() => filterQuestions(questions ?? [], filter), [questions, filter]);

  function startPractice(startId?: string) {
    const id = startId ?? visible[0]?.id ?? questions?.[0]?.id;
    if (id) navigate(`/subjects/${subjectId}/practice/${id}`);
  }

  return (
    <div className="mx-auto max-w-3xl p-6 sm:p-8">
      <Link to="/subjects" className="text-sm font-medium text-[#20bcd8] hover:underline">
        ← All subjects
      </Link>
      <div className="mb-5 mt-2 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight text-gray-100">{subject?.name ?? "Subject"}</h1>
        <div className="flex gap-2">
          <button
            onClick={() => startPractice()}
            disabled={!questions || questions.length === 0}
            className="rounded-lg bg-[#20bcd8] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#1ba8c2] disabled:opacity-50"
          >
            Start practicing
          </button>
          <Link
            to={`/subjects/${subjectId}/questions/new`}
            className="rounded-lg border border-[#20bcd8] px-4 py-2 text-sm font-medium text-[#20bcd8] transition-colors hover:bg-[#20bcd8]/10"
          >
            + Add question
          </Link>
        </div>
      </div>

      {error && <p className="mb-4 rounded-lg bg-red-950/40 px-4 py-2.5 text-sm text-red-300">{error}</p>}

      <div className="mb-4 flex gap-1 border-b border-gray-800">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setFilter(t.key)}
            className={`px-3 py-2 text-sm font-medium transition-colors ${
              filter === t.key
                ? "border-b-2 border-[#20bcd8] text-[#20bcd8]"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {!questions ? (
        <p className="text-gray-400">Loading…</p>
      ) : visible.length === 0 ? (
        <p className="rounded-lg border border-dashed border-gray-700 p-8 text-center text-gray-400">
          No questions here yet.
        </p>
      ) : (
        <ul className="space-y-2">
          {visible.map((q, i) => (
            <li key={q.id}>
              <button
                onClick={() => startPractice(q.id)}
                className="flex w-full items-center justify-between gap-4 rounded-xl border border-gray-800 bg-gray-900 p-4 text-left transition-colors hover:border-[#20bcd8]/60"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <span className="shrink-0 text-sm font-semibold text-gray-500">{i + 1}.</span>
                  <span className="truncate text-sm text-gray-200">{q.text}</span>
                  {q.image_url && (
                    <img src={resolveImageUrl(q.image_url)} alt="" className="h-8 w-8 shrink-0 rounded object-cover" />
                  )}
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_BADGE[q.status]}`}>
                  {STATUS_LABEL[q.status]}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
