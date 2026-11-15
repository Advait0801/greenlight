import { useEffect, useRef, useState, type FormEvent } from "react";

import { PrecheckNotice } from "../components/PrecheckNotice";
import { checkConstitution, type ConstitutionReport } from "./recognitionApi";
import { RecognitionReadiness } from "./RecognitionReadiness";
import { RecognitionReport } from "./RecognitionReport";

type Answer = "yes" | "no" | "";
const QUESTIONS: [string, string][] = [
  ["has_parent_organization", "Is the club a chapter of a national or parent organization?"],
  ["has_school_affiliation", "Is the club affiliated with a USC school, department or program?"],
  ["has_additional_officers", "Does the club have officer positions beyond the five required ones?"],
  ["has_appointed_positions", "Is any officer position appointed rather than elected?"],
];

export function Recognition() {
  const [mode, setMode] = useState<"file" | "text">("file");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ConstitutionReport | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (report) resultRef.current?.querySelector<HTMLElement>("h2")?.focus();
  }, [report]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const form = new FormData();
    if (mode === "file") {
      if (!file) return setError("Choose a file first.");
      form.append("file", file);
    } else {
      if (!text.trim()) return setError("Paste the constitution's text first.");
      form.append("text", text);
    }
    for (const [name] of QUESTIONS) if (answers[name]) form.append(name, answers[name] ?? "");
    setBusy(true);
    const outcome = await checkConstitution(form);
    setBusy(false);
    if (outcome.ok) setReport(outcome.data);
    else setError(outcome.error);
  }

  return (
    <div className="space-y-10">
      <section aria-labelledby="recognition-heading" className="space-y-3">
        <h1 id="recognition-heading" className="text-3xl font-bold tracking-tight">
          Recognition check
        </h1>
        <p className="max-w-2xl text-stone-700">
          Compare your constitution with the 2026-27 Campus Activities template before you submit. Greenlight marks each required
          clause as present, missing, changed or in conflict with a rule, and shows the template's wording and its source.
        </p>
        <p className="max-w-2xl text-stone-700">
          The application's key dates, with their sources, are in the readiness checklist below.
        </p>
        <PrecheckNotice />
      </section>

      <form onSubmit={submit} className="space-y-5 rounded-lg border border-stone-200 bg-white p-5 shadow-sm" aria-busy={busy}>
        <fieldset className="flex flex-wrap gap-4">
          <legend className="mb-2 font-semibold">Your constitution</legend>
          <label className="flex items-center gap-2">
            <input type="radio" name="mode" checked={mode === "file"} onChange={() => setMode("file")} />
            Upload a file (PDF, Word or text)
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" name="mode" checked={mode === "text"} onChange={() => setMode("text")} />
            Paste the text
          </label>
        </fieldset>

        {mode === "file" ? (
          <label className="block">
            <span className="text-sm font-medium">File</span>
            <input
              type="file"
              accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,image/*"
              className="mt-1 block w-full text-sm"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
        ) : (
          <label className="block">
            <span className="text-sm font-medium">Constitution text</span>
            <textarea
              className="mt-1 block h-56 w-full rounded border border-stone-400 p-2 font-mono text-sm"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </label>
        )}

        <fieldset className="space-y-3">
          <legend className="font-semibold">About your club</legend>
          <p className="text-sm text-stone-600">
            These decide which optional clauses apply. If you are not sure, leave it; Greenlight then treats the clause as required.
          </p>
          {QUESTIONS.map(([name, question]) => (
            <fieldset key={name} className="text-sm">
              <legend>{question}</legend>
              <div className="mt-1 flex flex-wrap gap-4">
                {(["yes", "no", ""] as const).map((value) => (
                  <label key={value || "unsure"} className="flex items-center gap-1.5">
                    <input
                      type="radio"
                      name={name}
                      checked={(answers[name] ?? "") === value}
                      onChange={() => setAnswers((old) => ({ ...old, [name]: value }))}
                    />
                    {value === "yes" ? "Yes" : value === "no" ? "No" : "Not sure"}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
        </fieldset>

        {error ? (
          <p role="alert" className="rounded border border-red-300 px-3 py-2 text-red-900">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-cardinal px-4 py-2 font-medium text-white hover:bg-cardinal-dark disabled:opacity-60"
        >
          {busy ? "Checking…" : "Check my constitution"}
        </button>
        <p className="text-xs text-stone-600">
          Nothing is submitted anywhere. Greenlight does not save your file; when its AI reader reads it, the words it quotes are
          kept in a private audit log.
        </p>
      </form>

      <div ref={resultRef} aria-live="polite">
        {report ? <RecognitionReport report={report} /> : null}
      </div>

      <RecognitionReadiness />
    </div>
  );
}
