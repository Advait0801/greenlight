import { useEffect, useState, type FormEvent } from "react";
import { useLocation } from "react-router-dom";

import { VENUE_LABELS, type VenueType } from "../api/events";
import { ASK_LABELS, approveEmail, draftEmail, gapOptions, type AskKind, type EmailKind, type GapReport, type GapRequest } from "../api/gap";
import { toCents } from "../api/money";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { SourceLink } from "../components/SourceLink";
import { StatusBadge } from "../components/StatusBadge";

interface Form {
  event_name: string;
  event_date: string;
  venue: VenueType | "";
  headcount: string;
  attributes: string[];
  shortfall: string;
  asks_usg: boolean;
  note: string;
}

const BLANK: Form = { event_name: "", event_date: "", venue: "", headcount: "", attributes: [], shortfall: "", asks_usg: false, note: "" };
const input = "mt-1 w-full rounded border border-stone-400 px-2 py-1";

// The demo club's example (data/demo); its drafted paragraph is recorded, so the demo works when the AI service is down.
const DEMO_EMAIL: { club_name: string; recipient: string; description: string; ask: AskKind[] } = {
  club_name: "Lantern Cultural Society",
  recipient: "The manager, Golden Lantern Kitchen",
  description: "Our spring culture night brings 150 USC students together for lantern-making, music and food from East and Southeast Asia.",
  ask: ["food"],
};

export function GapHelper() {
  const [form, setForm] = useState<Form>(BLANK);
  const [report, setReport] = useState<GapReport | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [emailKind, setEmailKind] = useState<EmailKind>("in_kind_sponsor");
  const [email, setEmail] = useState<{ club_name: string; recipient: string; description: string; ask: AskKind[] }>({ club_name: "", recipient: "", description: "", ask: [] });
  const [subject, setSubject] = useState("");
  const [draft, setDraft] = useState("");
  const [draftNotes, setDraftNotes] = useState<string[]>([]);
  const [approved, setApproved] = useState("");

  // Opened from the year plan: start from that event and its shortfall (worked out by the plan's code).
  const location = useLocation();
  useEffect(() => {
    const state = location.state as { gap?: Partial<GapRequest>; club?: string } | null;
    if (!state?.gap) return;
    const g = state.gap;
    setForm({
      ...BLANK, event_name: g.event_name ?? "", event_date: g.event_date ?? "", venue: g.venue ?? "",
      headcount: g.headcount == null ? "" : String(g.headcount), attributes: g.attributes ?? [],
      shortfall: g.shortfall_cents ? (g.shortfall_cents / 100).toFixed(2) : "", asks_usg: g.asks_usg ?? false,
    });
    setEmail((old) => ({ ...old, club_name: state.club ?? old.club_name }));
  }, [location.state]);

  async function check(e: FormEvent) {
    e.preventDefault();
    setError("");
    const shortfall = form.shortfall.trim() ? toCents(form.shortfall) : 0;
    if (shortfall === null) return setError("Enter the shortfall as a dollar amount, for example 900 or 900.50.");
    const headcount = form.headcount.trim() ? Number(form.headcount) : null;
    if (headcount !== null && (!Number.isInteger(headcount) || headcount < 0)) return setError("Enter the headcount as a whole number.");
    setBusy("options");
    const result = await gapOptions({
      event_name: form.event_name, event_date: form.event_date || null, venue: form.venue || null, headcount,
      attributes: form.attributes, shortfall_cents: shortfall, asks_usg: form.asks_usg, note: form.note,
    });
    setBusy("");
    if (!result.ok) return setError(result.error);
    setReport(result.data);
  }

  async function makeEmail() {
    setBusy("email");
    setApproved("");
    const result = await draftEmail({ kind: emailKind, event_name: form.event_name, event_date: form.event_date || null, ...email });
    setBusy("");
    if (!result.ok) return setError(result.error);
    setSubject(result.data.subject);
    setDraft(result.data.text);
    setDraftNotes(result.data.notes);
  }

  async function approve() {
    setBusy("approving");
    const result = await approveEmail(subject, draft);
    setBusy("");
    if (!result.ok) return setError(result.error);
    setApproved(result.data.message);
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold">Close a funding gap</h2>
        <p>
          When an event costs more than the club and USG (Undergraduate Student Government) can cover, Greenlight lists only the ways
          USC allows, each with its rule and when to start, and explains the ways USC does not allow. It can draft an outreach email
          for you to edit and approve. Greenlight never sends anything.
        </p>
      </header>

      <form onSubmit={check} className="grid gap-3 rounded-md border border-stone-300 bg-white p-4 sm:grid-cols-2">
        <label className="block">Event name<input className={input} value={form.event_name} onChange={(e) => setForm({ ...form, event_name: e.target.value })} /></label>
        <label className="block">Event date<input type="date" className={input} value={form.event_date} onChange={(e) => setForm({ ...form, event_date: e.target.value })} /></label>
        <label className="block">Venue
          <select className={input} value={form.venue} onChange={(e) => setForm({ ...form, venue: e.target.value as VenueType | "" })}>
            <option value="">Not known yet</option>
            {Object.entries(VENUE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="block">Expected headcount<input inputMode="numeric" className={input} value={form.headcount} onChange={(e) => setForm({ ...form, headcount: e.target.value })} /></label>
        <label className="block">Shortfall (dollars)<input inputMode="decimal" className={input} value={form.shortfall} onChange={(e) => setForm({ ...form, shortfall: e.target.value })} /></label>
        <label className="flex items-center gap-2 self-end py-2"><input type="checkbox" className="h-5 w-5" checked={form.asks_usg} onChange={(e) => setForm({ ...form, asks_usg: e.target.checked })} /> This event also asks USG for money</label>
        <label className="block sm:col-span-2">What you have in mind (optional)
          <textarea rows={2} className={input} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} placeholder="For example: could a local restaurant provide the food?" />
        </label>
        <div className="sm:col-span-2">
          <button type="submit" disabled={busy !== ""} className="rounded bg-cardinal px-4 py-2 font-medium text-white disabled:opacity-50">
            {busy === "options" ? "Checking…" : "Show the options USC allows"}
          </button>
        </div>
      </form>

      {error ? <p role="alert" className="rounded border border-red-700 bg-red-50 px-3 py-2 text-red-900">{error}</p> : null}

      {report ? (
        <section aria-labelledby="gap-results" className="space-y-6">
          <h3 id="gap-results" className="text-xl font-semibold">{report.event_name || "This event"}: {report.shortfall_text} short</h3>
          <PrecheckNotice text={report.notice} />
          {report.notes.map((n) => <p key={n} className="text-sm text-amber-950">! {n}</p>)}

          <div>
            <h4 className="text-lg font-semibold">Ways USC allows</h4>
            <ul className="mt-2 space-y-3">
              {report.options.map((o) => (
                <li key={o.id} className="rounded-md border border-stone-300 bg-white p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge state={o.status === "allowed" ? "info" : o.status === "office_decides" ? "office_decides" : "yellow"} label={o.status_label} />
                    <span className="font-semibold">{o.title}</span>
                  </div>
                  <p className="mt-1">{o.message}</p>
                  {o.finding ? <p className="mt-1 text-sm text-amber-950">! {o.finding.message} {o.finding.fix ?? ""}</p> : null}
                  <p className="mt-1 text-sm"><span className="font-medium">When to start: </span>{o.lead_time}</p>
                  {o.steps.length ? (
                    <ul className="mt-1 list-disc pl-5 text-sm">
                      {o.steps.map((s) => <li key={s.rule_id}>{s.title} ({s.owner_office}){s.due ? `: due ${s.due}` : ""}{s.past_due ? " (already passed)" : ""}</li>)}
                    </ul>
                  ) : null}
                  <details className="mt-1"><summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Rule text, conditions and sources</summary>
                    <SourceLink citation={o.citation} />
                    {o.conditions.map((c) => <SourceLink key={c.rule_id} citation={c} />)}
                  </details>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-lg font-semibold">Not allowed at USC (a generic assistant may suggest these)</h4>
            <ul className="mt-2 space-y-3">
              {report.not_allowed.map((b) => (
                <li key={b.rule_id} className="rounded-md border border-red-200 bg-white p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge state="red" label="Not allowed" />
                    <span className="font-semibold">{b.title}</span>
                    {b.in_your_note ? <span className="text-sm font-medium text-red-900">(your note mentions this)</span> : null}
                  </div>
                  <p className="mt-1">{b.why}</p>
                  {b.instead ? <p className="mt-1 text-sm"><span className="font-medium">Instead: </span>{b.instead}</p> : null}
                  <details className="mt-1"><summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Rule text and source</summary><SourceLink citation={b.citation} /></details>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-md border border-stone-300 bg-white p-4">
            <h4 className="text-lg font-semibold">Draft an outreach email</h4>
            <button type="button" className="mt-1 text-sm text-cardinal underline underline-offset-2"
              onClick={() => { setEmailKind("in_kind_sponsor"); setEmail(DEMO_EMAIL); }}>
              Fill in the demo club's example
            </button>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              <label className="block">Kind of help
                <select className={input} value={emailKind} onChange={(e) => setEmailKind(e.target.value as EmailKind)}>
                  <option value="in_kind_sponsor">In-kind sponsor (goods or services)</option>
                  <option value="co_host">Co-host (another recognized club)</option>
                </select>
              </label>
              <label className="block">Your club's name<input className={input} value={email.club_name} onChange={(e) => setEmail({ ...email, club_name: e.target.value })} /></label>
              <label className="block">Who it is to<input className={input} value={email.recipient} onChange={(e) => setEmail({ ...email, recipient: e.target.value })} /></label>
              {emailKind === "in_kind_sponsor" ? (
                <fieldset className="sm:col-span-2">
                  <legend>What you would like (in kind only; add details when you edit the draft)</legend>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
                    {(Object.keys(ASK_LABELS) as AskKind[]).map((k) => (
                      <label key={k} className="flex items-center gap-2">
                        <input type="checkbox" className="h-5 w-5" checked={email.ask.includes(k)}
                          onChange={(e) => setEmail({ ...email, ask: e.target.checked ? [...email.ask, k] : email.ask.filter((x) => x !== k) })} />
                        {ASK_LABELS[k]}
                      </label>
                    ))}
                  </div>
                </fieldset>
              ) : null}
              <label className="block sm:col-span-2">About the event, in your words<textarea rows={2} className={input} value={email.description} onChange={(e) => setEmail({ ...email, description: e.target.value })} /></label>
            </div>
            <button type="button" onClick={makeEmail} disabled={busy !== ""} className="mt-2 rounded bg-cardinal px-4 py-2 font-medium text-white disabled:opacity-50">
              {busy === "email" ? "Drafting…" : "Draft the email"}
            </button>
            {draft ? (
              <div className="mt-3 space-y-2">
                {draftNotes.map((n) => <p key={n} className="text-sm text-amber-950">! {n}</p>)}
                <label className="block">Subject (edit it)<input className={input} value={subject} onChange={(e) => { setSubject(e.target.value); setApproved(""); }} /></label>
                <label className="block">Email (edit it before approving)
                  <textarea rows={16} className={`${input} font-mono text-sm`} value={draft} onChange={(e) => { setDraft(e.target.value); setApproved(""); }} />
                </label>
                <button type="button" onClick={approve} disabled={busy !== "" || !draft.trim()} className="rounded border border-cardinal px-4 py-2 font-medium text-cardinal disabled:opacity-50">
                  I have read and approve this email
                </button>
                {approved ? <p role="status" className="font-medium">{approved}</p> : null}
              </div>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}
