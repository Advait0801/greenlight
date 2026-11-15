import { useState, type FormEvent } from "react";

import {
  approveDenial, clubStatus, draftDenial, getApplication, getQueue, getStats, withdraw,
  type ApplicationDetail, type ClubStatus, type FailureStats, type QueueItem,
} from "../api/usg";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { SourceLink } from "../components/SourceLink";
import { StatusBadge } from "../components/StatusBadge";

const input = "mt-1 w-full rounded border border-stone-400 px-2 py-1";
const DENIAL_LABELS = { none: "No reason drafted", draft: "Reason drafted, not approved", approved: "Reason approved" } as const;

function FailureChart({ stats }: { stats: FailureStats }) {
  const top = stats.rows.slice(0, 8);
  const max = Math.max(1, ...top.map((r) => r.applications));
  return (
    <section aria-labelledby="chart-heading" className="space-y-2 rounded-md border border-stone-300 bg-white p-4">
      <h3 id="chart-heading" className="text-lg font-semibold">Why applications fail</h3>
      <p className="text-sm text-stone-600">{stats.note} Applications counted: {stats.applications}. Reasons approved by a person: {stats.approved_denials}.</p>
      {top.length === 0 ? <p>No sent application breaks a rule yet.</p> : (
        <ul className="space-y-2">
          {top.map((r) => (
            <li key={r.rule_id}>
              <div className="flex justify-between gap-2 text-sm"><span>{r.title}</span><span className="font-medium">{r.applications} of {stats.applications}</span></div>
              <div className="mt-1 h-3 w-full rounded bg-stone-100" aria-hidden="true">
                <div className="h-3 rounded bg-cardinal" style={{ width: `${(r.applications / max) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ClubCorner() {
  const [reference, setReference] = useState("");
  const [token, setToken] = useState("");
  const [status, setStatus] = useState<ClubStatus | null>(null);
  const [error, setError] = useState("");

  async function look(e: FormEvent) {
    e.preventDefault();
    setError("");
    const result = await clubStatus(reference.trim(), token.trim());
    if (!result.ok) { setStatus(null); return setError(result.error); }
    setStatus(result.data);
  }

  async function takeBack() {
    const result = await withdraw(reference.trim(), token.trim());
    if (!result.ok) return setError(result.error);
    const again = await clubStatus(reference.trim(), token.trim());
    if (again.ok) setStatus(again.data);
  }

  return (
    <section aria-labelledby="club-heading" className="space-y-2 rounded-md border border-stone-300 bg-white p-4">
      <h3 id="club-heading" className="text-lg font-semibold">For clubs: an application you sent</h3>
      <p className="text-sm">Enter the reference and token Greenlight gave you when you sent the application from the money check.</p>
      <form onSubmit={look} className="grid gap-2 sm:grid-cols-3">
        <label className="block">Reference<input className={input} value={reference} onChange={(e) => setReference(e.target.value)} /></label>
        <label className="block">Token<input className={input} value={token} onChange={(e) => setToken(e.target.value)} autoComplete="off" /></label>
        <button type="submit" className="self-end rounded border border-cardinal px-3 py-2 font-medium text-cardinal">Show status</button>
      </form>
      {error ? <p role="alert" className="text-red-900">{error}</p> : null}
      {status ? (
        <div className="space-y-2">
          <p>{status.event_name}: {status.status === "sent" ? "in the USG queue" : "withdrawn"} (sent {status.sent_at.slice(0, 10)}).</p>
          {status.reviewer_message ? <pre className="whitespace-pre-wrap rounded bg-stone-50 p-3 text-sm">{status.reviewer_message}</pre> : <p className="text-sm text-stone-600">{status.note}</p>}
          {status.status === "sent" ? <button type="button" onClick={takeBack} className="rounded border border-stone-400 px-3 py-2 text-sm">Withdraw it from the USG screen</button> : null}
        </div>
      ) : null}
    </section>
  );
}

export function UsgScreen() {
  const [key, setKey] = useState("");
  const [open, setOpen] = useState(false);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [stats, setStats] = useState<FailureStats | null>(null);
  const [current, setCurrent] = useState<ApplicationDetail | null>(null);
  const [chosen, setChosen] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [notes, setNotes] = useState<string[]>([]);
  const [reviewer, setReviewer] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  async function refresh(passcode: string): Promise<boolean> {
    const [q, s] = await Promise.all([getQueue(passcode), getStats(passcode)]);
    if (!q.ok) { setError(q.error); return false; }
    if (!s.ok) { setError(s.error); return false; }
    setQueue(q.data.applications);
    setStats(s.data);
    return true;
  }

  async function unlock(e: FormEvent) {
    e.preventDefault();
    setError("");
    setOpen(await refresh(key));
  }

  async function select(id: number) {
    setError(""); setMessage(""); setDraft(""); setNotes([]);
    const result = await getApplication(key, id);
    if (!result.ok) return setError(result.error);
    setCurrent(result.data);
    setChosen(result.data.denial_rule_ids.length ? result.data.denial_rule_ids : result.data.reasons.filter((r) => r.verdict === "red").map((r) => r.rule_id));
    setDraft(result.data.denial_status === "approved" ? result.data.denial_approved_text ?? "" : result.data.denial_draft ?? "");
  }

  async function makeDraft() {
    if (!current) return;
    setBusy("drafting"); setMessage("");
    const result = await draftDenial(key, current.id, Array.from(new Set(chosen)));
    setBusy("");
    if (!result.ok) return setError(result.error);
    setDraft(result.data.text);
    setNotes(result.data.notes);
  }

  async function approve() {
    if (!current) return;
    setBusy("approving");
    const result = await approveDenial(key, current.id, draft, reviewer);
    setBusy("");
    if (!result.ok) return setError(result.error);
    setMessage(result.data.message);
    await refresh(key);
  }

  const uniqueRules = current ? Array.from(new Map(current.reasons.map((r) => [`${r.rule_id}|${r.where}`, r])).values()) : [];

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold">USG screen</h2>
        <p>
          For the USG (Undergraduate Student Government) Funding Department. Applications arrive already checked by Greenlight, but only
          the ones a club chose to send. A reviewer can draft a reason for not funding an application, citing the guideline; nothing
          reaches the club until a person approves the text.
        </p>
      </header>

      {!open ? (
        <form onSubmit={unlock} className="flex flex-col gap-2 rounded-md border border-stone-300 bg-white p-4 sm:flex-row sm:items-end">
          <label className="block grow">Reviewer passcode<input type="password" className={input} value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" /></label>
          <button type="submit" className="rounded bg-cardinal px-4 py-2 font-medium text-white">Open the USG screen</button>
        </form>
      ) : null}
      {error ? <p role="alert" className="rounded border border-red-700 bg-red-50 px-3 py-2 text-red-900">{error}</p> : null}

      {open ? (
        <>
          <PrecheckNotice />
          {stats ? <FailureChart stats={stats} /> : null}
          <section aria-labelledby="queue-heading" className="space-y-2">
            <h3 id="queue-heading" className="text-lg font-semibold">Queue ({queue.length})</h3>
            {queue.length === 0 ? <p>No club has sent an application yet.</p> : (
              <ul className="space-y-2">
                {queue.map((a) => (
                  <li key={a.id} className="rounded-md border border-stone-300 bg-white p-3">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="font-semibold">{a.event_name} · {a.club_name}</p>
                        <p className="text-sm text-stone-600">{a.reference} · {a.event_date ?? "no date"} · {a.total_text} · {DENIAL_LABELS[a.denial_status]}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge state={a.verdict} label={a.verdict_label} />
                        <button type="button" onClick={() => select(a.id)} className="rounded border border-cardinal px-3 py-2 text-sm font-medium text-cardinal">Open</button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {current ? (
            <section aria-labelledby="detail-heading" className="space-y-4 rounded-md border border-stone-300 bg-white p-4">
              <h3 id="detail-heading" className="text-lg font-semibold">{current.event_name} · {current.club_name}</h3>
              <p className="text-sm">Fund: {current.fund_name ?? "not chosen"} · Total {current.total_text}</p>
              <ul className="space-y-1 text-sm">
                {current.lines.map((l) => <li key={l.line} className="flex flex-wrap items-center gap-2"><StatusBadge state={l.verdict} label={l.verdict_label} /> {l.item || `Line ${l.line}`} ({l.vendor || "no vendor"}): {l.amount_text}</li>)}
              </ul>
              <fieldset>
                <legend className="font-semibold">Reasons you may cite (Greenlight's findings)</legend>
                <ul className="mt-2 space-y-3">
                  {uniqueRules.map((r) => (
                    <li key={`${r.rule_id}|${r.where}`} className="rounded border border-stone-200 p-3">
                      <label className="flex items-start gap-2">
                        <input type="checkbox" className="mt-1 h-5 w-5" checked={chosen.includes(r.rule_id)}
                          onChange={(e) => setChosen(e.target.checked ? [...chosen, r.rule_id] : chosen.filter((x) => x !== r.rule_id))} />
                        <span><StatusBadge state={r.verdict} label={r.verdict_label} /> <span className="font-medium">{r.where}:</span> {r.message}</span>
                      </label>
                      <details className="mt-1"><summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Rule text and source</summary><SourceLink citation={r.citation} /></details>
                    </li>
                  ))}
                </ul>
              </fieldset>
              <button type="button" onClick={makeDraft} disabled={busy !== "" || chosen.length === 0} className="rounded bg-cardinal px-4 py-2 font-medium text-white disabled:opacity-50">
                {busy === "drafting" ? "Drafting…" : "Draft a reason from the ones ticked"}
              </button>
              {draft ? (
                <div className="space-y-2">
                  {notes.map((n) => <p key={n} className="text-sm text-amber-950">! {n}</p>)}
                  <label className="block">Reason for the club (edit it before approving)
                    <textarea rows={16} className={`${input} font-mono text-sm`} value={draft} onChange={(e) => { setDraft(e.target.value); setMessage(""); }} />
                  </label>
                  <label className="block">Your name<input className={input} value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
                  <button type="button" onClick={approve} disabled={busy !== "" || !draft.trim() || !reviewer.trim()} className="rounded border border-cardinal px-4 py-2 font-medium text-cardinal disabled:opacity-50">
                    I have read and approve this reason
                  </button>
                  {message ? <p role="status" className="font-medium">{message}</p> : null}
                </div>
              ) : null}
            </section>
          ) : null}
        </>
      ) : null}

      <ClubCorner />
    </div>
  );
}
