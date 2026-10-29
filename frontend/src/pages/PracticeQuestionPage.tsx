import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, resolveImageUrl } from "../lib/api";
import type { AnswerResult, QuestionPractice } from "../lib/types";

interface FeedItem {
  question: QuestionPractice;
  selected: string | null;
  result: AnswerResult | null;
  submitting: boolean;
}

export default function PracticeQuestionPage() {
  const { subjectId, questionId } = useParams();
  const [items, setItems] = useState<FeedItem[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!questionId) return;
    setItems([]);
    setError(null);
    setInitialLoading(true);
    api
      .get<QuestionPractice>(`/questions/${questionId}/practice`)
      .then((q) => setItems([{ question: q, selected: null, result: null, submitting: false }]))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load question"))
      .finally(() => setInitialLoading(false));
  }, [questionId]);

  const lastItem = items[items.length - 1];
  const nextId = lastItem?.question.next_question_id ?? null;

  useEffect(() => {
    if (!nextId || loadingMore) return;
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0]?.isIntersecting) return;
        setLoadingMore(true);
        api
          .get<QuestionPractice>(`/questions/${nextId}/practice`)
          .then((q) => setItems((cur) => [...cur, { question: q, selected: null, result: null, submitting: false }]))
          .catch(() => setError("Failed to load more questions"))
          .finally(() => setLoadingMore(false));
      },
      { rootMargin: "600px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [nextId, loadingMore]);

  function selectOption(qid: string, optionId: string) {
    setItems((cur) => cur.map((it) => (it.question.id === qid ? { ...it, selected: optionId } : it)));
  }

  async function submitAnswer(qid: string) {
    const item = items.find((it) => it.question.id === qid);
    if (!item || !item.selected || item.submitting) return;
    setItems((cur) => cur.map((it) => (it.question.id === qid ? { ...it, submitting: true } : it)));
    try {
      const r = await api.post<AnswerResult>(`/questions/${qid}/answer`, { selected_option_id: item.selected });
      setItems((cur) => cur.map((it) => (it.question.id === qid ? { ...it, result: r, submitting: false } : it)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Could not submit your answer");
      setItems((cur) => cur.map((it) => (it.question.id === qid ? { ...it, submitting: false } : it)));
    }
  }

  if (error && items.length === 0) {
    return <p className="m-6 rounded-lg bg-red-950/40 px-4 py-2.5 text-sm text-red-300">{error}</p>;
  }

  return (
    <div className="mx-auto max-w-2xl p-6 sm:p-8">
      <Link to={`/subjects/${subjectId}`} className="text-sm font-medium text-[#20bcd8] hover:underline">
        ← {items[0]?.question.subject_name ?? "Back"}
      </Link>

      {initialLoading ? (
        <p className="mt-6 text-gray-400">Loading…</p>
      ) : (
        <div className="mt-4 space-y-5">
          {items.map((item, i) => (
            <QuestionCard
              key={item.question.id}
              index={i}
              item={item}
              onSelect={selectOption}
              onSubmit={submitAnswer}
            />
          ))}
        </div>
      )}

      <div ref={sentinelRef} className="h-4" />

      {loadingMore && <p className="py-4 text-center text-sm text-gray-500">Loading more…</p>}
      {!initialLoading && !loadingMore && !nextId && items.length > 0 && (
        <p className="py-6 text-center text-sm text-gray-500">You've reached the end of this subject.</p>
      )}
      {error && items.length > 0 && <p className="py-2 text-center text-sm text-red-300">{error}</p>}
    </div>
  );
}

function QuestionCard({
  index,
  item,
  onSelect,
  onSubmit,
}: {
  index: number;
  item: FeedItem;
  onSelect: (questionId: string, optionId: string) => void;
  onSubmit: (questionId: string) => void;
}) {
  const { question, selected, result, submitting } = item;

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900 p-6">
      <p className="mb-1 text-xs font-semibold text-gray-500">Question {index + 1}</p>
      <p className="text-base font-medium text-gray-100">{question.text}</p>
      {question.image_url && (
        <img
          src={resolveImageUrl(question.image_url)}
          alt=""
          className="mt-4 max-h-72 rounded-lg border border-gray-800"
        />
      )}

      <div className="mt-5 space-y-3">
        {question.options.map((o) => {
          const isSelected = selected === o.id;
          const isCorrectOption = result && o.id === result.correct_option_id;
          const isWrongSelected = result && isSelected && !result.is_correct;

          let classes = "border-gray-800";
          if (result) {
            if (isCorrectOption) classes = "border-green-600 bg-green-950/30";
            else if (isWrongSelected) classes = "border-red-600 bg-red-950/30";
          } else if (isSelected) {
            classes = "border-[#20bcd8] bg-[#20bcd8]/10";
          }

          return (
            <label
              key={o.id}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-colors ${classes} ${
                result ? "cursor-default" : "cursor-pointer hover:border-gray-700"
              }`}
            >
              <input
                type="radio"
                name={`option-${question.id}`}
                disabled={!!result}
                checked={isSelected}
                onChange={() => onSelect(question.id, o.id)}
                className="h-4 w-4 accent-[#20bcd8]"
              />
              <span className="text-sm text-gray-200">{o.text}</span>
              {o.image_url && <img src={resolveImageUrl(o.image_url)} alt="" className="max-h-16 rounded" />}
              {isCorrectOption && <span className="ml-auto text-sm font-semibold text-green-400">✓ Correct</span>}
              {isWrongSelected && <span className="ml-auto text-sm font-semibold text-red-400">✗ Your answer</span>}
            </label>
          );
        })}
      </div>

      {result && (
        <div
          className={`mt-5 rounded-xl p-4 text-sm ${
            result.is_correct ? "bg-green-950/30 text-green-300" : "bg-red-950/30 text-red-300"
          }`}
        >
          <p className="font-semibold">{result.is_correct ? "Correct!" : "Not quite."}</p>
          {result.explanation && <p className="mt-1 text-gray-300">{result.explanation}</p>}
        </div>
      )}

      {!result && (
        <div className="mt-6 flex justify-end">
          <button
            onClick={() => onSubmit(question.id)}
            disabled={!selected || submitting}
            className="rounded-lg bg-[#20bcd8] px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#1ba8c2] disabled:opacity-50"
          >
            {submitting ? "Checking…" : "Check answer"}
          </button>
        </div>
      )}
    </div>
  );
}
