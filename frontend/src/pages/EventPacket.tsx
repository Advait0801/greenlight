import { useEffect, useState, type FormEvent } from "react";
import { useLocation } from "react-router-dom";

import {
  VENUE_LABELS,
  downloadIcs,
  getDetails,
  postJson,
  type Detail,
  type EventFacts,
  type EventPacket as Packet,
  type PacketObligation,
  type ParseResult,
  type VenueType,
} from "../api/events";
import { EventTimeline, formatDay } from "../components/EventTimeline";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { SourceLink } from "../components/SourceLink";
import { StatusBadge, type BadgeState } from "../components/StatusBadge";

const EXAMPLE = "Culture night for about 150 people on McCarthy Quad on Friday, April 9, 2027, with a DJ and catered food.";
const EMPTY: EventFacts = { name: null, event_date: null, end_date: null, venue: null, headcount: null, attributes: [], possible_attributes: [], needs_officer_input: [] };
const ORDER = ["blocked", "check_with_office", "office_decides", "to_do", "condition"] as const;
const GROUP_TITLES: Record<(typeof ORDER)[number], string> = {
  blocked: "Blocked as described",
  check_with_office: "Check with the office",
  office_decides: "The office decides: contact them",
  to_do: "To do",
  condition: "Rules to keep",
};

function badgeFor(o: PacketObligation): { state: BadgeState; label: string } {
  if (o.superseded_by) return { state: "info", label: "Not applied: a stricter source is used" };
  if (o.finding) {
    const verdict = o.finding.verdict;
    if (verdict === "green") return { state: "green", label: "Meets the rule (date checked)" };
    if (verdict === "red") return { state: "red", label: o.past_due ? "Deadline passed" : "Breaks the rule" };
    if (verdict === "office_decides") return { state: "office_decides", label: "The office decides" };
    return { state: "yellow", label: "Check with the office" };
  }
  return { state: "info", label: o.status_label };
}

function ObligationCard({ o, describe }: { o: PacketObligation; describe: (name: string) => string }) {
  const badge = badgeFor(o);
  return (
    <li id={`ob-${o.rule_id}`} className="rounded-md border border-stone-300 bg-white p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 className="font-semibold">{o.title}</h4>
          <p className="text-sm text-stone-600">{o.owner_office}</p>
        </div>
        <StatusBadge state={badge.state} label={badge.label} />
      </div>
      <p className="mt-2">{o.message}</p>
      {o.due && !o.superseded_by ? (
        <p className="mt-2 font-medium">
          {o.status === "office_decides" ? "Contact them by " : "Due "}
          <time dateTime={o.due}>{formatDay(o.due)}</time>
          {o.past_due ? " (passed)" : ""}
        </p>
      ) : null}
      {o.due_note ? <p className="text-sm text-stone-600">{o.due_note}</p> : null}
      {o.contact_by ? (
        <p className="mt-2 font-medium">
          Contact them well before <time dateTime={o.contact_by}>{formatDay(o.contact_by)}</time>, when every approval must be in place
        </p>
      ) : null}
      {o.note ? <p className="mt-2 text-sm">{o.note}</p> : null}
      {o.fix && (o.violated || o.past_due) ? <p className="mt-2 text-sm"><span className="font-medium">Fix: </span>{o.fix}</p> : null}
      {o.fallbacks.length ? (
        <div className="mt-2 text-sm">
          <p className="font-medium">Options</p>
          <ul className="list-disc pl-5">{o.fallbacks.map((f) => <li key={f.kind + f.text}>{f.text}</li>)}</ul>
        </div>
      ) : null}
      <p className="mt-2 text-xs text-stone-600">Applies because of: {o.triggered_by.map(describe).join("; ")}</p>
      <details className="mt-2">
        <summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Rule text and source</summary>
        <SourceLink citation={o.citation} />
        {o.contact_by_citation ? <SourceLink citation={o.contact_by_citation} /> : null}
      </details>
    </li>
  );
}

export function EventPacket() {
  const [sentence, setSentence] = useState("");
  const [facts, setFacts] = useState<EventFacts | null>(null);
  const [notes, setNotes] = useState<string[]>([]);
  const [packet, setPacket] = useState<Packet | null>(null);
  const [details, setDetails] = useState<Detail[]>([]);
  const [busy, setBusy] = useState<"" | "reading" | "checking" | "ics">("");
  const [error, setError] = useState("");

  // Opened from the year plan: start from that event's details. The officer still checks them before the packet runs.
  const location = useLocation();
  useEffect(() => {
    const state = location.state as { facts?: EventFacts } | null;
    if (state?.facts) {
      setFacts({ ...EMPTY, ...state.facts, needs_officer_input: [] });
      setNotes(["Opened from your year plan. Check the details, then build the packet."]);
    }
  }, [location.state]);

  useEffect(() => {
    getDetails().then((result) => (result.ok ? setDetails(result.data) : setError(result.error))).catch(() => undefined);
  }, []);

  const describe = (name: string) => details.find((d) => d.name === name)?.description ?? VENUE_LABELS[name as VenueType] ?? name;

  async function read(event: FormEvent) {
    event.preventDefault();
    setBusy("reading");
    setError("");
    setPacket(null);
    const result = await postJson<ParseResult>("/events/parse", { sentence });
    setBusy("");
    if (!result.ok) {
      setError(`${result.error} You can fill in the details below by hand.`);
      setFacts({ ...EMPTY });
      setNotes([]);
      return;
    }
    setFacts(result.data.facts);
    setNotes(result.data.notes);
  }

  // A packet built from other details is wrong once a detail changes: clear it (phase 6 iteration 2).
  useEffect(() => {
    setPacket(null);
  }, [facts, details]);

  async function check(event: FormEvent) {
    event.preventDefault();
    if (!facts) return;
    setBusy("checking");
    setError("");
    // The officer has now seen and confirmed every detail on the form.
    const confirmed: EventFacts = { ...facts, needs_officer_input: [] };
    const result = await postJson<Packet>("/events/packet", { event: confirmed });
    setBusy("");
    if (result.ok) setPacket(result.data);
    else setError(result.error);
  }

  async function ics() {
    if (!packet) return;
    setBusy("ics");
    const result = await downloadIcs(packet.event);
    setBusy("");
    if (!result.ok) {
      setError(result.error);
      return;
    }
    const url = URL.createObjectURL(result.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "greenlight-event.ics";
    link.click();
    URL.revokeObjectURL(url);
  }

  function toggle(name: string, on: boolean) {
    if (!facts) return;
    const attributes = on ? [...new Set([...facts.attributes, name])] : facts.attributes.filter((a) => a !== name);
    setFacts({ ...facts, attributes, possible_attributes: facts.possible_attributes.filter((a) => a !== name) });
  }

  const ask = new Set(facts?.needs_officer_input ?? []);
  const shown = details.filter((d) => facts && (facts.attributes.includes(d.name) || facts.possible_attributes.includes(d.name)));
  const others = details.filter((d) => !shown.includes(d));

  return (
    <div className="space-y-8">
      <section aria-labelledby="packet-heading" className="space-y-3">
        <h1 id="packet-heading" className="text-3xl font-bold tracking-tight">Event packet</h1>
        <p className="max-w-2xl text-stone-700">
          Describe one event in a sentence. Greenlight reads it, asks about anything unclear, then lists every form, approval and
          deadline that applies, with dates counted back from the event and the rule text behind each.
        </p>
        <form onSubmit={read} className="space-y-2">
          <label htmlFor="sentence" className="block font-medium">Your event</label>
          <textarea id="sentence" value={sentence} onChange={(e) => setSentence(e.target.value)} maxLength={2000} rows={3} required
            placeholder={EXAMPLE} className="w-full rounded-md border border-stone-400 bg-white p-2" />
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={busy !== "" || !sentence.trim()} className="rounded-md bg-cardinal px-4 py-2 font-medium text-white disabled:opacity-60">
              {busy === "reading" ? "Reading…" : "Read my event"}
            </button>
            <button type="button" onClick={() => setSentence(EXAMPLE)} className="rounded-md border border-stone-400 px-4 py-2">Use an example</button>
            <button type="button" onClick={() => { setFacts({ ...EMPTY }); setNotes([]); setPacket(null); }} className="rounded-md border border-stone-400 px-4 py-2">Fill in a form instead</button>
          </div>
        </form>
        {error ? <p role="alert" className="rounded-md border border-red-700 bg-red-50 p-3 text-red-900">{error}</p> : null}
      </section>

      {facts ? (
        <section aria-labelledby="facts-heading" className="space-y-4 rounded-md border border-stone-300 bg-white p-4">
          <h2 id="facts-heading" className="text-xl font-semibold">Check the details</h2>
          <p className="text-sm text-stone-700">Greenlight only uses what you confirm here. Fields marked "please answer" were not clear.</p>
          {notes.map((n) => <p key={n} className="text-sm"><StatusBadge state="yellow" label="Note" /> {n}</p>)}
          <form onSubmit={check} className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="font-medium">Event name</span>
              <input value={facts.name ?? ""} maxLength={200} onChange={(e) => setFacts({ ...facts, name: e.target.value || null })} className="mt-1 w-full rounded-md border border-stone-400 p-2" />
            </label>
            <label className="block">
              <span className="font-medium">Venue {ask.has("venue") ? <StatusBadge state="yellow" label="Please answer" /> : null}</span>
              <select value={facts.venue ?? ""} onChange={(e) => setFacts({ ...facts, venue: (e.target.value || null) as VenueType | null })} className="mt-1 w-full rounded-md border border-stone-400 p-2">
                <option value="">No venue (for example a walk-up table) or not known</option>
                {Object.entries(VENUE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="font-medium">First day {ask.has("event_date") ? <StatusBadge state="yellow" label="Please answer" /> : null}</span>
              <input type="date" value={facts.event_date ?? ""} onChange={(e) => setFacts({ ...facts, event_date: e.target.value || null })} className="mt-1 w-full rounded-md border border-stone-400 p-2" />
            </label>
            <label className="block">
              <span className="font-medium">Last day, if more than one {ask.has("end_date") ? <StatusBadge state="yellow" label="Please answer" /> : null}</span>
              <input type="date" value={facts.end_date ?? ""} onChange={(e) => setFacts({ ...facts, end_date: e.target.value || null })} className="mt-1 w-full rounded-md border border-stone-400 p-2" />
            </label>
            <label className="block">
              <span className="font-medium">Expected people {ask.has("headcount") ? <StatusBadge state="yellow" label="Please answer" /> : null}</span>
              <input type="number" min={0} max={1000000} value={facts.headcount ?? ""} onChange={(e) => setFacts({ ...facts, headcount: e.target.value === "" ? null : Number(e.target.value) })} className="mt-1 w-full rounded-md border border-stone-400 p-2" />
            </label>
            {facts.attributes.includes("tent") || facts.possible_attributes.includes("tent") ? (
              <label className="block">
                <span className="font-medium">Largest tent or canopy, in square feet (if known)</span>
                <input type="number" min={0} max={1000000} value={facts.tent_area_sqft ?? ""} onChange={(e) => setFacts({ ...facts, tent_area_sqft: e.target.value === "" ? null : Number(e.target.value) })} className="mt-1 w-full rounded-md border border-stone-400 p-2" />
              </label>
            ) : null}
            <fieldset className="sm:col-span-2">
              <legend className="font-medium">What the event has {ask.has("attributes") ? <StatusBadge state="yellow" label="Please answer" /> : null}</legend>
              <ul className="mt-2 grid gap-1 sm:grid-cols-2">
                {shown.map((d) => (
                  <li key={d.name}>
                    <label className="flex items-start gap-2">
                      <input type="checkbox" className="mt-1" checked={facts.attributes.includes(d.name)} onChange={(e) => toggle(d.name, e.target.checked)} />
                      <span>{d.description}{facts.possible_attributes.includes(d.name) ? <> <StatusBadge state="yellow" label="Not sure: tick if true" /></> : null}</span>
                    </label>
                  </li>
                ))}
              </ul>
              <details className="mt-2">
                <summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Add other details</summary>
                <ul className="mt-2 grid gap-1 sm:grid-cols-2">
                  {others.map((d) => (
                    <li key={d.name}>
                      <label className="flex items-start gap-2">
                        <input type="checkbox" className="mt-1" checked={facts.attributes.includes(d.name)} onChange={(e) => toggle(d.name, e.target.checked)} />
                        <span>{d.description}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              </details>
            </fieldset>
            <p className="text-sm text-stone-700 sm:col-span-2">
              Details still marked "Not sure" are kept as "check with the office" items until you tick them or leave them out.
            </p>
            <div className="sm:col-span-2">
              <button type="submit" disabled={busy !== ""} className="rounded-md bg-cardinal px-4 py-2 font-medium text-white disabled:opacity-60">
                {busy === "checking" ? "Checking…" : "Build the packet"}
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {packet ? (
        <section aria-labelledby="result-heading" className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="result-heading" className="text-2xl font-semibold">Packet for {packet.event.name ?? "your event"}</h2>
            <button type="button" onClick={ics} disabled={busy !== "" || packet.timeline.length === 0} className="rounded-md border border-cardinal px-4 py-2 font-medium text-cardinal disabled:opacity-60">
              {busy === "ics" ? "Preparing…" : "Add the dates to my calendar (.ics)"}
            </button>
          </div>
          <PrecheckNotice text={packet.notice} />
          <p className="text-sm text-stone-700">Worked out on {formatDay(packet.as_of)}. {packet.obligations.length} items: {ORDER.map((s) => `${packet.counts[s] ?? 0} ${GROUP_TITLES[s].toLowerCase()}`).join(", ")}.</p>

          {packet.hard_blocks.length ? (
            <div role="alert" className="rounded-md border-2 border-red-700 bg-red-50 p-4">
              <h3 className="flex items-center gap-2 font-semibold text-red-900"><StatusBadge state="red" label="Blocked" /> Fix these first</h3>
              <ul className="mt-2 list-disc pl-5">{packet.hard_blocks.map((b) => <li key={b}>{b}</li>)}</ul>
              {packet.fallbacks.length ? (
                <>
                  <p className="mt-3 font-medium">Options</p>
                  <ul className="list-disc pl-5">{packet.fallbacks.map((f) => <li key={f.text}>{f.text}</li>)}</ul>
                </>
              ) : null}
            </div>
          ) : null}

          {packet.questions.length ? (
            <div className="rounded-md border border-amber-700 bg-amber-50 p-4">
              <h3 className="flex items-center gap-2 font-semibold"><StatusBadge state="yellow" label="Questions" /> Answer these for a complete packet</h3>
              <ul className="mt-2 list-disc pl-5">{packet.questions.map((q) => <li key={q}>{q}</li>)}</ul>
            </div>
          ) : null}

          {packet.source_conflicts.length ? (
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Sources disagree</h3>
              {packet.source_conflicts.map((c) => (
                <div key={c.rules.join("|")} className="rounded-md border border-sky-700 bg-sky-50 p-4">
                  <p><StatusBadge state="info" label="Two sources" /> {c.explanation}</p>
                  {c.citations.map((citation) => <SourceLink key={citation.rule_id} citation={citation} />)}
                </div>
              ))}
            </div>
          ) : null}

          <div>
            <h3 className="mb-3 text-lg font-semibold">Timeline</h3>
            <EventTimeline packet={packet} />
          </div>

          {ORDER.map((status) => {
            const items = packet.obligations.filter((o) => o.status === status);
            if (!items.length) return null;
            return (
              <div key={status}>
                <h3 className="mb-3 text-lg font-semibold">{GROUP_TITLES[status]} ({items.length})</h3>
                <ul className="space-y-3">{items.map((o) => <ObligationCard key={o.rule_id} o={o} describe={describe} />)}</ul>
              </div>
            );
          })}
        </section>
      ) : null}
    </div>
  );
}
