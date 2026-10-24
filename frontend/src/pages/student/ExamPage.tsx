import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { api, ApiError, resolveImageUrl } from "../../lib/api";
import { countByStatus, deriveTileStatus, type TileStatus } from "../../lib/examStatus";
import type { AttemptSection, AttemptState, QuestionState, SectionState } from "../../lib/types";

const AUTOSAVE_INTERVAL_MS = 5000;

function pad(n: number): string {
  return String(Math.max(0, Math.floor(n))).padStart(2, "0");
}

function hms(totalSeconds: number) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  return { h: pad(h), m: pad(m), s: pad(s) };
}

function ms(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${pad(m)}:${pad(s)}`;
}

const EMPTY_QUESTION_STATE: QuestionState = {
  selected_option_id: null,
  visited: false,
  marked_for_review: false,
  time_spent_seconds: 0,
};

const EMPTY_SECTION_STATE: SectionState = { started_at: null, locked: false };

/**
 * Walks sections in order, locking any whose time has run out, and returns
 * the first still-open one (starting its clock the moment it's first
 * reached). Null means every section is done — the whole test should submit.
 * Used both once on load and every second while the test is running, so a
 * section always locks and the next one starts the same way either way.
 */
function advanceToActiveSection(
  sections: AttemptSection[],
  sectionProgress: Record<string, SectionState>,
  now: number,
): { sectionProgress: Record<string, SectionState>; activeIndex: number | null } {
  const sp = { ...sectionProgress };
  for (let i = 0; i < sections.length; i++) {
    const s = sections[i];
    const state = sp[s.id] ?? EMPTY_SECTION_STATE;
    if (state.locked) continue;
    if (!state.started_at) {
      sp[s.id] = { started_at: new Date(now).toISOString(), locked: false };
      return { sectionProgress: sp, activeIndex: i };
    }
    const endMs = new Date(state.started_at).getTime() + s.duration_mins * 60_000;
    if (now < endMs) {
      return { sectionProgress: sp, activeIndex: i };
    }
    sp[s.id] = { ...state, locked: true };
  }
  return { sectionProgress: sp, activeIndex: null };
}

export default function ExamPage() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [attempt, setAttempt] = useState<AttemptState | null>(null);
  const [progress, setProgress] = useState<Record<string, QuestionState>>({});
  const [sectionProgress, setSectionProgress] = useState<Record<string, SectionState>>({});
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [modal, setModal] = useState<null | "report" | "paper" | "instructions" | "submit">(null);
  const [reportText, setReportText] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const autoSubmitted = useRef(false);
  const progressRef = useRef(progress);
  progressRef.current = progress;
  const sectionProgressRef = useRef(sectionProgress);
  sectionProgressRef.current = sectionProgress;

  const sections = attempt?.sections ?? [];
  const currentSection = sections[currentSectionIndex];
  const currentQuestion = currentSection?.questions[currentQuestionIndex];

  const submit = useCallback(async () => {
    if (!attemptId || submitting) return;
    setSubmitting(true);
    try {
      await api.post(`/student/attempts/${attemptId}/submit`, {
        current_question_id: currentQuestion?.id ?? null,
        questions: progressRef.current,
        sections: sectionProgressRef.current,
      });
      navigate(`/tests/results/${attemptId}`, { replace: true });
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Could not submit the test");
      setSubmitting(false);
    }
  }, [attemptId, currentQuestion?.id, navigate, submitting]);

  const autosave = useCallback(
    (overrides?: { sections?: Record<string, SectionState> }) => {
      if (!attemptId || !currentQuestion) return;
      api
        .patch(`/student/attempts/${attemptId}/autosave`, {
          current_question_id: currentQuestion.id,
          questions: progressRef.current,
          sections: overrides?.sections ?? sectionProgressRef.current,
        })
        .catch(() => void 0);
    },
    [attemptId, currentQuestion],
  );

  function markVisited(questionId: string) {
    setProgress((prev) => ({ ...prev, [questionId]: { ...(prev[questionId] ?? EMPTY_QUESTION_STATE), visited: true } }));
  }

  // ---- load the attempt ----
  useEffect(() => {
    if (!attemptId) return;
    api
      .get<AttemptState>(`/student/attempts/${attemptId}`)
      .then((state) => {
        if (state.status === "submitted") {
          navigate(`/tests/results/${attemptId}`, { replace: true });
          return;
        }
        setAttempt(state);

        const initialProgress: Record<string, QuestionState> = {};
        for (const s of state.sections) {
          for (const q of s.questions) {
            initialProgress[q.id] = { ...EMPTY_QUESTION_STATE, ...state.draft.questions[q.id] };
          }
        }

        const { sectionProgress: resolvedSP, activeIndex } = advanceToActiveSection(
          state.sections,
          state.draft.sections,
          Date.now(),
        );

        if (activeIndex === null) {
          // Every section's time has already run out (e.g. reopened after a
          // long absence) — submit now, same as the auto-submit-at-zero path.
          setSectionProgress(resolvedSP);
          setProgress(initialProgress);
          if (!autoSubmitted.current) {
            autoSubmitted.current = true;
            api
              .post(`/student/attempts/${attemptId}/submit`, {
                current_question_id: null,
                questions: initialProgress,
                sections: resolvedSP,
              })
              .then(() => navigate(`/tests/results/${attemptId}`, { replace: true }))
              .catch(() => setLoadError("This test's time has run out."));
          }
          return;
        }

        const section = state.sections[activeIndex];
        let questionIndex = 0;
        if (state.draft.current_question_id) {
          const idx = section.questions.findIndex((q) => q.id === state.draft.current_question_id);
          if (idx >= 0) questionIndex = idx;
        }
        const firstQuestion = section.questions[questionIndex];
        if (firstQuestion) initialProgress[firstQuestion.id] = { ...initialProgress[firstQuestion.id], visited: true };

        setProgress(initialProgress);
        setSectionProgress(resolvedSP);
        setCurrentSectionIndex(activeIndex);
        setCurrentQuestionIndex(questionIndex);

        const sectionState = resolvedSP[section.id];
        const endMs = new Date(sectionState.started_at as string).getTime() + section.duration_mins * 60_000;
        setSecondsLeft(Math.max(0, Math.round((endMs - Date.now()) / 1000)));
      })
      .catch((err) => setLoadError(err instanceof ApiError ? err.message : "Could not load the test"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attemptId]);

  // ---- per-section countdown; locks + auto-advances when time runs out ----
  useEffect(() => {
    if (!attempt) return;
    const id = setInterval(() => {
      const { sectionProgress: nextSP, activeIndex } = advanceToActiveSection(
        attempt.sections,
        sectionProgressRef.current,
        Date.now(),
      );
      const changed = JSON.stringify(nextSP) !== JSON.stringify(sectionProgressRef.current);

      if (activeIndex === null) {
        if (!autoSubmitted.current) {
          autoSubmitted.current = true;
          setSectionProgress(nextSP);
          submit();
        }
        return;
      }

      if (changed) {
        setSectionProgress(nextSP);
        if (activeIndex !== currentSectionIndex) {
          setCurrentSectionIndex(activeIndex);
          setCurrentQuestionIndex(0);
          const firstQ = attempt.sections[activeIndex].questions[0];
          if (firstQ) markVisited(firstQ.id);
        }
        autosave({ sections: nextSP });
      }

      const section = attempt.sections[activeIndex];
      const endMs = new Date(nextSP[section.id].started_at as string).getTime() + section.duration_mins * 60_000;
      setSecondsLeft(Math.max(0, Math.round((endMs - Date.now()) / 1000)));
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, 1000);
    return () => clearInterval(id);
  }, [attempt, currentSectionIndex, submit, autosave]);

  // ---- per-question stopwatch ----
  useEffect(() => {
    if (!currentQuestion) return;
    const id = setInterval(() => {
      setProgress((prev) => {
        const q = prev[currentQuestion.id];
        if (!q) return prev;
        return { ...prev, [currentQuestion.id]: { ...q, time_spent_seconds: q.time_spent_seconds + 1 } };
      });
    }, 1000);
    return () => clearInterval(id);
  }, [currentQuestion]);

  // ---- autosave every 5s ----
  useEffect(() => {
    const id = setInterval(() => autosave(), AUTOSAVE_INTERVAL_MS);
    return () => clearInterval(id);
  }, [autosave]);

  function updateCurrent(patch: Partial<QuestionState>) {
    if (!currentQuestion) return;
    setProgress((prev) => ({ ...prev, [currentQuestion.id]: { ...prev[currentQuestion.id], ...patch } }));
  }

  function goToQuestionInSection(index: number) {
    const q = currentSection?.questions[index];
    if (!q) return;
    markVisited(q.id);
    setCurrentQuestionIndex(index);
    setMobileDrawerOpen(false);
  }

  /** Locks the current section and moves to the next open one (or submits if that was the last). */
  function advanceSection() {
    if (!currentSection) return;
    const locked = {
      ...sectionProgressRef.current,
      [currentSection.id]: { ...(sectionProgressRef.current[currentSection.id] ?? EMPTY_SECTION_STATE), locked: true },
    };
    const { sectionProgress: next, activeIndex } = advanceToActiveSection(sections, locked, Date.now());
    setSectionProgress(next);
    if (activeIndex === null) {
      if (!autoSubmitted.current) {
        autoSubmitted.current = true;
        submit();
      }
      return;
    }
    setCurrentSectionIndex(activeIndex);
    setCurrentQuestionIndex(0);
    const firstQ = sections[activeIndex].questions[0];
    if (firstQ) markVisited(firstQ.id);
    autosave({ sections: next });
  }

  function saveAndNext() {
    if (!currentSection) return;
    updateCurrent({ visited: true });
    if (currentQuestionIndex < currentSection.questions.length - 1) {
      goToQuestionInSection(currentQuestionIndex + 1);
      autosave();
    } else if (currentSectionIndex < sections.length - 1) {
      advanceSection();
    } else {
      // Last question of the last section: wrap back to the first question.
      goToQuestionInSection(0);
      autosave();
    }
  }

  function markForReviewAndNext() {
    if (!currentSection) return;
    updateCurrent({ visited: true, marked_for_review: true });
    if (currentQuestionIndex < currentSection.questions.length - 1) {
      goToQuestionInSection(currentQuestionIndex + 1);
      autosave();
    } else if (currentSectionIndex < sections.length - 1) {
      advanceSection();
    } else {
      autosave();
    }
  }

  function clearResponse() {
    updateCurrent({ selected_option_id: null });
    autosave();
  }

  function requestFullscreen() {
    document.documentElement.requestFullscreen?.().catch(() => void 0);
  }

  async function sendReport() {
    if (!currentQuestion || !reportText.trim()) return;
    try {
      await api.post("/student/reports", {
        question_id: currentQuestion.id,
        test_attempt_id: attemptId,
        message: reportText.trim(),
      });
      setReportText("");
      setModal(null);
      alert("Thanks — your report has been sent to the teacher.");
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Could not send the report");
    }
  }

  const allQuestions = useMemo(() => sections.flatMap((s) => s.questions), [sections]);

  const tileStatuses: TileStatus[] = useMemo(
    () => (currentSection?.questions ?? []).map((q) => deriveTileStatus(toProgress(progress[q.id]))),
    [currentSection, progress],
  );
  const sectionCounts = useMemo(
    () => countByStatus((currentSection?.questions ?? []).map((q) => toProgress(progress[q.id]))),
    [currentSection, progress],
  );
  const wholeTestCounts = useMemo(
    () => countByStatus(allQuestions.map((q) => toProgress(progress[q.id]))),
    [allQuestions, progress],
  );

  if (loadError) return <div className="m-6 rounded bg-red-50 px-3 py-2 text-sm text-red-700">{loadError}</div>;
  if (!attempt || !currentSection || !currentQuestion) {
    return <div className="m-6 text-gray-500">Loading…</div>;
  }

  const time = hms(secondsLeft);
  const currentState = progress[currentQuestion.id] ?? EMPTY_QUESTION_STATE;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-white">
      {/* Top header bar */}
      <header className="flex h-[70px] shrink-0 items-center justify-between border-b border-gray-200 px-5">
        <div className="flex items-baseline gap-3">
          <span className="text-lg font-bold text-[#176b87]">MCQ Platform</span>
          <span className="text-sm font-normal text-gray-600">{attempt.test_title}</span>
        </div>
        <div className="flex items-center gap-2 rounded border border-gray-300 px-3 py-1.5">
          <span className="text-sm text-gray-600">Time Left</span>
          {[time.h, time.m, time.s].map((v, i) => (
            <span key={i} className="flex items-center">
              {i > 0 && <span className="mx-0.5 text-gray-400">:</span>}
              <span className="rounded bg-gray-700 px-1.5 py-0.5 font-mono text-sm font-semibold text-white">
                {v}
              </span>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <button
            onClick={requestFullscreen}
            className="rounded border border-[#20bcd8] px-3 py-1.5 text-sm font-medium text-[#20bcd8]"
          >
            Switch to full screen
          </button>
          <button
            onClick={() => setMobileDrawerOpen(true)}
            className="rounded border border-[#20bcd8] px-3 py-1.5 text-sm font-medium text-[#20bcd8] lg:hidden"
          >
            Palette
          </button>
        </div>
      </header>

      {/* Section tab row */}
      <div className="flex shrink-0 flex-wrap items-center gap-2 bg-gray-100 px-5 py-2">
        <span className="text-xs font-semibold tracking-wide text-gray-500">SECTIONS</span>
        {sections.map((s, i) => {
          const locked = sectionProgress[s.id]?.locked;
          const isCurrent = i === currentSectionIndex;
          return (
            <span
              key={s.id}
              className={`rounded px-4 py-1 text-sm font-medium ${
                isCurrent ? "bg-[#176b87] text-white" : locked ? "bg-gray-300 text-gray-500" : "bg-gray-200 text-gray-400"
              }`}
            >
              {s.title}
              {locked && !isCurrent ? " ✓" : ""}
            </span>
          );
        })}
      </div>

      <div className="flex min-h-0 flex-1">
        {/* Main question column */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Question header row */}
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-3">
            <p className="font-bold text-gray-900">Question No. {currentQuestionIndex + 1}</p>
            <div className="flex items-center gap-5 text-xs text-gray-500">
              <div>
                <p className="mb-1">Marks</p>
                <div className="flex gap-1">
                  <span className="rounded-full bg-green-600 px-2 py-0.5 font-semibold text-white">
                    +{attempt.marks_correct}
                  </span>
                  <span className="rounded-full bg-red-600 px-2 py-0.5 font-semibold text-white">
                    {attempt.marks_wrong}
                  </span>
                </div>
              </div>
              <div>
                <p className="mb-1">Time</p>
                <p className="font-mono text-sm text-gray-700">{ms(currentState.time_spent_seconds)}</p>
              </div>
              <div>
                <p className="mb-1">View in</p>
                <select className="rounded border border-gray-300 px-2 py-1 text-sm" defaultValue="English">
                  <option>English</option>
                </select>
              </div>
              <button
                onClick={() => setModal("report")}
                className="flex items-center gap-1 text-amber-600 hover:underline"
              >
                ⚠ Report
              </button>
            </div>
          </div>

          {/* Question body */}
          <div className="flex-1 overflow-y-auto px-5 py-5">
            <p className="text-base text-gray-900">{currentQuestion.text}</p>
            {currentQuestion.image_url && (
              <img
                src={resolveImageUrl(currentQuestion.image_url)}
                alt=""
                className="mt-4 max-h-72 rounded border border-gray-200"
              />
            )}
            <hr className="my-4 border-gray-200" />
            <div className="space-y-3">
              {currentQuestion.options.map((o, i) => {
                const selected = currentState.selected_option_id === o.id;
                return (
                  <label
                    key={o.id}
                    className={`flex cursor-pointer items-center gap-3 rounded-md border px-4 py-3 ${
                      selected ? "border-[#176b87] bg-[#f0f8fb]" : i === 0 ? "border-gray-200 bg-gray-50" : "border-gray-200"
                    }`}
                  >
                    <input
                      type="radio"
                      name="option"
                      checked={selected}
                      onChange={() => updateCurrent({ selected_option_id: o.id })}
                      className="h-4 w-4"
                    />
                    <span className="text-sm text-gray-800">{o.text}</span>
                    {o.image_url && <img src={resolveImageUrl(o.image_url)} alt="" className="max-h-16 rounded" />}
                  </label>
                );
              })}
            </div>
          </div>

          {/* Bottom action bar */}
          <div className="flex shrink-0 items-center justify-between border-t border-gray-200 bg-gray-50 px-5 py-3">
            <div className="flex gap-2">
              <button
                onClick={markForReviewAndNext}
                className="rounded bg-[#cfe8f3] px-4 py-2 text-sm font-medium text-[#176b87]"
              >
                Mark for Review &amp; Next
              </button>
              <button
                onClick={clearResponse}
                className="rounded bg-[#cfe8f3] px-4 py-2 text-sm font-medium text-[#176b87]"
              >
                Clear Response
              </button>
            </div>
            <button
              onClick={saveAndNext}
              className="rounded bg-[#20bcd8] px-5 py-2 text-sm font-semibold text-white"
            >
              Save &amp; Next
            </button>
          </div>
        </div>

        {/* Collapse handle */}
        <button
          onClick={() => setSidebarCollapsed((c) => !c)}
          className="hidden w-4 shrink-0 items-center justify-center bg-gray-800 text-white lg:flex"
          aria-label="Toggle palette"
        >
          {sidebarCollapsed ? "‹" : "›"}
        </button>

        {/* Right sidebar */}
        <aside
          className={`${sidebarCollapsed ? "lg:w-0 lg:overflow-hidden lg:p-0" : "lg:w-[22%]"} ${
            mobileDrawerOpen ? "fixed inset-y-0 right-0 z-40 w-80 shadow-xl" : "hidden"
          } flex shrink-0 flex-col bg-[#d9ecf7] lg:static lg:flex lg:shadow-none`}
        >
          <div className="flex items-center justify-between p-4 lg:hidden">
            <span className="font-semibold">Palette</span>
            <button onClick={() => setMobileDrawerOpen(false)} className="text-xl leading-none">
              ×
            </button>
          </div>

          <div className="flex items-center gap-2 px-4 pt-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#bcdcee] text-[#176b87]">
              👤
            </div>
            <span className="text-sm font-medium text-gray-800">{user?.name}</span>
          </div>

          <div className="space-y-1.5 px-4 py-3 text-xs text-gray-700">
            <div className="flex items-center gap-3">
              <LegendShape kind="answered" count={sectionCounts.answered} /> <span>Answered</span>
              <LegendShape kind="marked" count={sectionCounts.marked} /> <span>Marked</span>
              <LegendShape kind="not_visited" count={sectionCounts.not_visited} /> <span>Not Visited</span>
            </div>
            <div className="flex items-center gap-3">
              <LegendShape kind="marked_and_answered" count={sectionCounts.marked_and_answered} />{" "}
              <span>Marked and answered</span>
              <LegendShape kind="not_answered" count={sectionCounts.not_answered} /> <span>Not Answered</span>
            </div>
          </div>

          <div className="bg-[#b7d8ee] px-4 py-2 text-sm font-bold text-gray-800">
            SECTION : {currentSection.title}
          </div>

          <div className="grid grid-cols-5 gap-2 overflow-y-auto p-4">
            {currentSection.questions.map((q, i) => (
              <PaletteTile
                key={q.id}
                number={i + 1}
                status={tileStatuses[i]}
                current={i === currentQuestionIndex}
                onClick={() => goToQuestionInSection(i)}
              />
            ))}
          </div>

          <div className="mt-auto space-y-2 p-4">
            <div className="flex gap-2">
              <button
                onClick={() => setModal("paper")}
                className="flex-1 rounded bg-[#bcdcee] px-3 py-2 text-sm font-medium text-[#176b87]"
              >
                Question Paper
              </button>
              <button
                onClick={() => setModal("instructions")}
                className="flex-1 rounded bg-[#bcdcee] px-3 py-2 text-sm font-medium text-[#176b87]"
              >
                Instructions
              </button>
            </div>
            <button
              onClick={() => setModal("submit")}
              className="w-full rounded bg-[#20bcd8] px-3 py-2 text-sm font-bold text-white"
            >
              Submit Test
            </button>
          </div>
        </aside>
        {mobileDrawerOpen && (
          <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setMobileDrawerOpen(false)} />
        )}
      </div>

      {modal === "report" && (
        <Modal title="Report a problem" onClose={() => setModal(null)}>
          <textarea
            value={reportText}
            onChange={(e) => setReportText(e.target.value)}
            rows={4}
            placeholder="What's wrong with this question?"
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <button onClick={sendReport} className="mt-3 rounded bg-[#20bcd8] px-4 py-2 text-sm font-semibold text-white">
            Send report
          </button>
        </Modal>
      )}

      {modal === "paper" && (
        <Modal title="Question Paper" onClose={() => setModal(null)}>
          <div className="max-h-96 space-y-4 overflow-y-auto">
            {sections.map((s) => (
              <div key={s.id}>
                <p className="mb-1 text-sm font-semibold text-gray-700">{s.title}</p>
                <ol className="list-decimal space-y-1 pl-5 text-sm">
                  {s.questions.map((q) => (
                    <li key={q.id}>{q.text}</li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </Modal>
      )}

      {modal === "instructions" && (
        <Modal title="Instructions" onClose={() => setModal(null)}>
          <ul className="space-y-2 text-sm text-gray-700">
            {sections.map((s) => (
              <li key={s.id}>
                {s.title}: {s.duration_mins} minutes.
              </li>
            ))}
            <li>
              Marking scheme: +{attempt.marks_correct} for a correct answer, {attempt.marks_wrong} for a wrong
              answer, {attempt.marks_skipped} for a skipped question.
            </li>
            <li>When a section's time runs out it locks and the next section starts automatically.</li>
            <li>White with a border: question not visited yet.</li>
            <li>Red: visited but not answered.</li>
            <li>Green: answered.</li>
            <li>Purple: marked for review.</li>
            <li>Purple with a tick: marked for review and answered (still graded on submit).</li>
          </ul>
        </Modal>
      )}

      {modal === "submit" && (
        <Modal title="Submit test?" onClose={() => setModal(null)}>
          <ul className="mb-4 space-y-1 text-sm text-gray-700">
            <li>Answered: {wholeTestCounts.answered + wholeTestCounts.marked_and_answered}</li>
            <li>Not answered: {wholeTestCounts.not_answered}</li>
            <li>Marked for review: {wholeTestCounts.marked + wholeTestCounts.marked_and_answered}</li>
            <li>Not visited: {wholeTestCounts.not_visited}</li>
          </ul>
          <div className="flex justify-end gap-2">
            <button onClick={() => setModal(null)} className="rounded border border-gray-300 px-4 py-2 text-sm">
              Cancel
            </button>
            <button
              onClick={submit}
              disabled={submitting}
              className="rounded bg-[#20bcd8] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {submitting ? "Submitting…" : "Submit"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function toProgress(s: QuestionState | undefined) {
  const state = s ?? EMPTY_QUESTION_STATE;
  return {
    visited: state.visited,
    selectedOptionId: state.selected_option_id,
    markedForReview: state.marked_for_review,
  };
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-xl leading-none text-gray-500">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

const TILE_CLASSES: Record<TileStatus, string> = {
  not_visited: "bg-white border-2 border-gray-800 text-gray-900",
  not_answered: "bg-[#c0392b] text-white rounded-t-full rounded-b-md",
  answered: "bg-[#2fb35a] text-white rounded-t-full rounded-b-md",
  marked: "bg-[#9b59b6] text-white rounded-full",
  marked_and_answered: "bg-[#9b59b6] text-white rounded-full",
};

function PaletteTile({
  number,
  status,
  current,
  onClick,
}: {
  number: number;
  status: TileStatus;
  current: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`relative flex h-9 w-9 items-center justify-center text-sm font-semibold ${TILE_CLASSES[status]} ${
        current ? "ring-2 ring-offset-2 ring-[#176b87]" : ""
      }`}
    >
      {number}
      {status === "marked_and_answered" && (
        <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-green-500 text-[10px] text-white">
          ✓
        </span>
      )}
    </button>
  );
}

function LegendShape({ kind, count }: { kind: TileStatus; count: number }) {
  return (
    <span
      className={`relative flex h-5 w-5 shrink-0 items-center justify-center text-[10px] font-semibold ${TILE_CLASSES[kind]}`}
    >
      {count}
      {kind === "marked_and_answered" && (
        <span className="absolute -right-1 -top-1 flex h-2.5 w-2.5 items-center justify-center rounded-full bg-green-500 text-[7px] text-white">
          ✓
        </span>
      )}
    </span>
  );
}
