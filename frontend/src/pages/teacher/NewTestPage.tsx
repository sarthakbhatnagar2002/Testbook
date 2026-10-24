import { useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError, resolveImageUrl, uploadImage } from "../../lib/api";

interface OptionDraft {
  text: string;
  imageUrl: string;
}

interface QuestionDraft {
  text: string;
  imageUrl: string;
  explanation: string;
  options: OptionDraft[];
  correctIndex: number;
}

interface SectionDraft {
  title: string;
  durationMins: number;
  questions: QuestionDraft[];
}

function emptyQuestion(): QuestionDraft {
  return {
    text: "",
    imageUrl: "",
    explanation: "",
    options: [
      { text: "", imageUrl: "" },
      { text: "", imageUrl: "" },
    ],
    correctIndex: 0,
  };
}

function emptySection(n: number): SectionDraft {
  return { title: `Section ${n}`, durationMins: 30, questions: [emptyQuestion()] };
}

export default function NewTestPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [marksCorrect, setMarksCorrect] = useState(4);
  const [marksWrong, setMarksWrong] = useState(-1);
  const [marksSkipped, setMarksSkipped] = useState(0);
  const [published, setPublished] = useState(false);
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [sections, setSections] = useState<SectionDraft[]>([emptySection(1)]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function updateSection(i: number, patch: Partial<SectionDraft>) {
    setSections((prev) => prev.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
  }

  function addSection() {
    setSections((prev) => [...prev, emptySection(prev.length + 1)]);
  }

  function removeSection(i: number) {
    setSections((prev) => (prev.length > 1 ? prev.filter((_, idx) => idx !== i) : prev));
  }

  const totalDuration = sections.reduce((sum, s) => sum + (s.durationMins || 0), 0);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.post("/tests/with-questions", {
        title,
        marks_correct: marksCorrect,
        marks_wrong: marksWrong,
        marks_skipped: marksSkipped,
        published,
        start_time: startTime ? new Date(startTime).toISOString() : undefined,
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
        sections: sections.map((s) => ({
          title: s.title,
          duration_mins: s.durationMins,
          questions: s.questions.map((q) => ({
            text: q.text,
            image_url: q.imageUrl || undefined,
            explanation: q.explanation || undefined,
            options: q.options
              .filter((o) => o.text.trim())
              .map((o, i) => ({
                text: o.text,
                image_url: o.imageUrl || undefined,
                is_correct: i === q.correctIndex,
              })),
          })),
        })),
      });
      navigate("/teacher/tests");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the test");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-1 text-xl font-semibold text-gray-900">New test</h1>
      <p className="mb-6 text-sm text-gray-500">
        Build your test as one or more timed sections. When a section's time runs out it locks and the next
        section starts automatically.
      </p>
      <form onSubmit={onSubmit} className="space-y-6">
        {error && <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-5">
          <label className="block text-sm">
            Title
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Untitled test"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-lg font-medium"
            />
          </label>

          <div className="grid grid-cols-3 gap-4">
            <label className="block text-sm">
              Marks correct
              <input
                type="number"
                min={0}
                value={marksCorrect}
                onChange={(e) => setMarksCorrect(Number(e.target.value))}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              />
            </label>
            <label className="block text-sm">
              Marks wrong
              <input
                type="number"
                max={0}
                value={marksWrong}
                onChange={(e) => setMarksWrong(Number(e.target.value))}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              />
            </label>
            <label className="block text-sm">
              Marks skipped
              <input
                type="number"
                max={0}
                value={marksSkipped}
                onChange={(e) => setMarksSkipped(Number(e.target.value))}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <label className="block text-sm">
              Start time (optional — open immediately if blank)
              <input
                type="datetime-local"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              />
            </label>
            <label className="block text-sm">
              End time (optional — no deadline if blank)
              <input
                type="datetime-local"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              />
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={published} onChange={(e) => setPublished(e.target.checked)} />
            Publish immediately
          </label>

          <p className="text-sm text-gray-500">Total duration: {totalDuration} min across {sections.length} section{sections.length === 1 ? "" : "s"}</p>
        </div>

        <div className="space-y-5">
          {sections.map((s, i) => (
            <SectionCard
              key={i}
              index={i}
              draft={s}
              onChange={(patch) => updateSection(i, patch)}
              onRemove={() => removeSection(i)}
              removable={sections.length > 1}
            />
          ))}
        </div>

        <button
          type="button"
          onClick={addSection}
          className="w-full rounded border-2 border-dashed border-[#176b87] py-3 text-sm font-semibold text-[#176b87] hover:bg-[#f0f8fb]"
        >
          + Add section
        </button>

        <button
          type="submit"
          disabled={busy}
          className="rounded bg-[#20bcd8] px-4 py-2 font-semibold text-white disabled:opacity-60"
        >
          {busy ? "Saving…" : "Create test"}
        </button>
      </form>
    </div>
  );
}

function SectionCard({
  index,
  draft,
  onChange,
  onRemove,
  removable,
}: {
  index: number;
  draft: SectionDraft;
  onChange: (patch: Partial<SectionDraft>) => void;
  onRemove: () => void;
  removable: boolean;
}) {
  function updateQuestion(i: number, patch: Partial<QuestionDraft>) {
    onChange({ questions: draft.questions.map((q, idx) => (idx === i ? { ...q, ...patch } : q)) });
  }

  function addQuestion() {
    onChange({ questions: [...draft.questions, emptyQuestion()] });
  }

  function removeQuestion(i: number) {
    if (draft.questions.length > 1) onChange({ questions: draft.questions.filter((_, idx) => idx !== i) });
  }

  return (
    <div className="rounded-lg border-2 border-[#176b87]/30 bg-[#f7fbfd] p-5">
      <div className="mb-4 flex items-end gap-4">
        <label className="flex-1 text-sm">
          Section title
          <input
            required
            value={draft.title}
            onChange={(e) => onChange({ title: e.target.value })}
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2 font-medium"
          />
        </label>
        <label className="text-sm">
          Duration (mins)
          <input
            type="number"
            min={1}
            max={600}
            value={draft.durationMins}
            onChange={(e) => onChange({ durationMins: Number(e.target.value) })}
            className="mt-1 w-28 rounded border border-gray-300 px-3 py-2"
          />
        </label>
        {removable && (
          <button type="button" onClick={onRemove} className="pb-2 text-sm text-red-600">
            Remove section
          </button>
        )}
      </div>

      <div className="space-y-4">
        {draft.questions.map((q, i) => (
          <QuestionCard
            key={i}
            sectionIndex={index}
            index={i}
            draft={q}
            onChange={(patch) => updateQuestion(i, patch)}
            onRemove={() => removeQuestion(i)}
            removable={draft.questions.length > 1}
          />
        ))}
      </div>

      <button
        type="button"
        onClick={addQuestion}
        className="mt-4 w-full rounded border-2 border-dashed border-gray-300 py-2 text-sm font-medium text-gray-500 hover:border-[#176b87] hover:text-[#176b87]"
      >
        + Add question to this section
      </button>
    </div>
  );
}

function ImageUploadField({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (url: string) => void;
  label: string;
}) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file again later
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      onChange(await uploadImage(file));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  if (value) {
    return (
      <div className="flex items-center gap-2">
        <img src={resolveImageUrl(value)} alt="" className="h-12 w-12 rounded border border-gray-200 object-cover" />
        <button type="button" onClick={() => onChange("")} className="text-xs text-red-600">
          Remove image
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <label className="cursor-pointer rounded border border-dashed border-gray-300 px-3 py-1.5 text-xs text-gray-500 hover:border-[#176b87] hover:text-[#176b87]">
        {uploading ? "Uploading…" : label}
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          className="hidden"
          disabled={uploading}
          onChange={handleFile}
        />
      </label>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}

function QuestionCard({
  sectionIndex,
  index,
  draft,
  onChange,
  onRemove,
  removable,
}: {
  sectionIndex: number;
  index: number;
  draft: QuestionDraft;
  onChange: (patch: Partial<QuestionDraft>) => void;
  onRemove: () => void;
  removable: boolean;
}) {
  function updateOption(i: number, patch: Partial<OptionDraft>) {
    onChange({ options: draft.options.map((o, idx) => (idx === i ? { ...o, ...patch } : o)) });
  }

  function addOption() {
    if (draft.options.length < 6) onChange({ options: [...draft.options, { text: "", imageUrl: "" }] });
  }

  function removeOption(i: number) {
    if (draft.options.length <= 2) return;
    onChange({ options: draft.options.filter((_, idx) => idx !== i) });
    if (draft.correctIndex >= i && draft.correctIndex > 0) onChange({ correctIndex: draft.correctIndex - 1 });
  }

  return (
    <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <span className="mt-2 shrink-0 text-sm font-semibold text-gray-400">Q{index + 1}</span>
        {removable && (
          <button type="button" onClick={onRemove} className="text-sm text-red-600">
            Remove
          </button>
        )}
      </div>

      <textarea
        required
        value={draft.text}
        onChange={(e) => onChange({ text: e.target.value })}
        placeholder="Question text"
        rows={2}
        className="w-full rounded border border-gray-300 px-3 py-2"
      />

      <div>
        <p className="mb-1 text-xs font-medium text-gray-500">Diagram (optional)</p>
        <ImageUploadField
          value={draft.imageUrl}
          onChange={(url) => onChange({ imageUrl: url })}
          label="Upload image"
        />
      </div>

      <div className="space-y-3">
        {draft.options.map((o, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              type="radio"
              name={`correct-${sectionIndex}-${index}`}
              checked={draft.correctIndex === i}
              onChange={() => onChange({ correctIndex: i })}
            />
            <input
              value={o.text}
              onChange={(e) => updateOption(i, { text: e.target.value })}
              placeholder={o.imageUrl ? `Option ${i + 1} text (optional)` : `Option ${i + 1}`}
              className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
            />
            <ImageUploadField value={o.imageUrl} onChange={(url) => updateOption(i, { imageUrl: url })} label="Image" />
            {draft.options.length > 2 && (
              <button type="button" onClick={() => removeOption(i)} className="text-sm text-red-600">
                ×
              </button>
            )}
          </div>
        ))}
        {draft.options.length < 6 && (
          <button type="button" onClick={addOption} className="text-sm text-[#176b87] underline">
            + Add option
          </button>
        )}
      </div>

      <textarea
        value={draft.explanation}
        onChange={(e) => onChange({ explanation: e.target.value })}
        placeholder="Explanation (optional)"
        rows={2}
        className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
      />
    </div>
  );
}
