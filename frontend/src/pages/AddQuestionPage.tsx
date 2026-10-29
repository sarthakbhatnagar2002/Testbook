import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError, resolveImageUrl, uploadImage } from "../lib/api";

interface OptionDraft {
  text: string;
  imageUrl: string;
}

function emptyOption(): OptionDraft {
  return { text: "", imageUrl: "" };
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
    e.target.value = "";
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
        <img src={resolveImageUrl(value)} alt="" className="h-12 w-12 rounded border border-gray-700 object-cover" />
        <button type="button" onClick={() => onChange("")} className="text-xs text-red-400">
          Remove image
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <label className="cursor-pointer rounded border border-dashed border-gray-700 px-3 py-1.5 text-xs text-gray-400 hover:border-[#20bcd8] hover:text-[#20bcd8]">
        {uploading ? "Uploading…" : label}
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          className="hidden"
          disabled={uploading}
          onChange={handleFile}
        />
      </label>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </div>
  );
}

export default function AddQuestionPage() {
  const { subjectId } = useParams();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [explanation, setExplanation] = useState("");
  const [options, setOptions] = useState<OptionDraft[]>([emptyOption(), emptyOption()]);
  const [correctIndex, setCorrectIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function updateOption(i: number, patch: Partial<OptionDraft>) {
    setOptions((prev) => prev.map((o, idx) => (idx === i ? { ...o, ...patch } : o)));
  }

  function addOption() {
    if (options.length < 6) setOptions((prev) => [...prev, emptyOption()]);
  }

  function removeOption(i: number) {
    if (options.length <= 2) return;
    setOptions((prev) => prev.filter((_, idx) => idx !== i));
    if (correctIndex >= i && correctIndex > 0) setCorrectIndex((c) => c - 1);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.post("/questions", {
        subject_id: subjectId,
        text,
        image_url: imageUrl || undefined,
        explanation: explanation || undefined,
        options: options
          .filter((o) => o.text.trim() || o.imageUrl)
          .map((o, i) => ({
            text: o.text,
            image_url: o.imageUrl || undefined,
            is_correct: i === correctIndex,
          })),
      });
      navigate(`/subjects/${subjectId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the question");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-6 sm:p-8">
      <Link to={`/subjects/${subjectId}`} className="text-sm font-medium text-[#20bcd8] hover:underline">
        ← Back
      </Link>
      <h1 className="mb-6 mt-2 text-2xl font-bold tracking-tight text-gray-100">Add a question</h1>

      <form onSubmit={onSubmit} className="space-y-4 rounded-2xl border border-gray-800 bg-gray-900 p-5">
        {error && <p className="rounded-lg bg-red-950/40 px-4 py-2.5 text-sm text-red-300">{error}</p>}

        <textarea
          required
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Question text"
          rows={3}
          className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 placeholder:text-gray-500 outline-none focus:border-[#20bcd8]"
        />

        <div>
          <p className="mb-1 text-xs font-medium text-gray-400">Diagram (optional)</p>
          <ImageUploadField value={imageUrl} onChange={setImageUrl} label="Upload image" />
        </div>

        <div className="space-y-3">
          {options.map((o, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                type="radio"
                name="correct"
                checked={correctIndex === i}
                onChange={() => setCorrectIndex(i)}
                className="accent-[#20bcd8]"
              />
              <input
                value={o.text}
                onChange={(e) => updateOption(i, { text: e.target.value })}
                placeholder={o.imageUrl ? `Option ${i + 1} text (optional)` : `Option ${i + 1}`}
                className="flex-1 rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder:text-gray-500 outline-none focus:border-[#20bcd8]"
              />
              <ImageUploadField value={o.imageUrl} onChange={(url) => updateOption(i, { imageUrl: url })} label="Image" />
              {options.length > 2 && (
                <button type="button" onClick={() => removeOption(i)} className="text-sm text-red-400">
                  ×
                </button>
              )}
            </div>
          ))}
          {options.length < 6 && (
            <button type="button" onClick={addOption} className="text-sm text-[#20bcd8] underline">
              + Add option
            </button>
          )}
        </div>

        <textarea
          value={explanation}
          onChange={(e) => setExplanation(e.target.value)}
          placeholder="Explanation shown after answering (optional)"
          rows={2}
          className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder:text-gray-500 outline-none focus:border-[#20bcd8]"
        />

        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-[#20bcd8] px-4 py-2 font-semibold text-white transition-colors hover:bg-[#1ba8c2] disabled:opacity-60"
        >
          {busy ? "Saving…" : "Save question"}
        </button>
      </form>
    </div>
  );
}
