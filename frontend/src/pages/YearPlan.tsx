import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { VENUE_LABELS, getDetails, type Detail, type EventFacts, type VenueType } from "../api/events";
import { dollars, toCents, type BudgetEvent, type FundId } from "../api/money";
import {
  computePlan,
  downloadPlanIcs,
  getDemoPlan,
  readEvents,
  type PlanEvent,
  type ReadRow,
  type YearPlanReport,
  type YearPlanRequest,
} from "../api/plans";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { StatusBadge } from "../components/StatusBadge";
import { PlanResults, Section } from "./YearPlanResults";

const STORAGE_KEY = "greenlight-year-plan-v1";
const FUNDS: { id: FundId; name: string }[] = [
  { id: "usg-fund-professional-academic", name: "Professional and Academic Research" },
  { id: "usg-fund-philanthropy", name: "Philanthropy" },
  { id: "usg-fund-social-recreation-startup", name: "Social and Recreation / Startup" },
  { id: "usg-fund-performing-visual-arts", name: "Performing and Visual Arts" },
];

// What the officer edits. Money and headcounts stay as typed text until they are checked and turned into numbers.
interface EditEvent {
  key: string;
  name: string;
  event_date: string;
  end_date: string;
  venue: VenueType | "";
  headcount: string;
  attributes: string[];
  possible_attributes: string[];
  cost: string;
  request: string;
  fund: FundId | "";
}

interface EditPlan {
  club_name: string;
  mission: string;
  level: "undergraduate" | "graduate" | "";
  on_hand: string;
  income: string;
  received: string;
  unavailable: string[];
  events: EditEvent[];
}

const EMPTY_PLAN: EditPlan = { club_name: "", mission: "", level: "", on_hand: "", income: "", received: "", unavailable: [], events: [] };

function centsText(cents: number | null): string {
  return cents === null ? "" : (cents / 100).toFixed(2);
}

function newKey(events: EditEvent[]): string {
  let n = events.length + 1;
  while (events.some((e) => e.key === `event-${n}`)) n += 1;
  return `event-${n}`;
}

function blankEvent(events: EditEvent[], name = ""): EditEvent {
  return { key: newKey(events), name, event_date: "", end_date: "", venue: "", headcount: "", attributes: [], possible_attributes: [], cost: "", request: "0", fund: "" };
}

function fromRequest(plan: YearPlanRequest): EditPlan {
  return {
    club_name: plan.club_name, mission: plan.mission, level: plan.level ?? "",
    on_hand: centsText(plan.money_on_hand_cents), income: centsText(plan.expected_income_cents), received: centsText(plan.usg_received_this_year_cents),
    unavailable: [...plan.unavailable_dates],
    events: plan.events.map((e) => ({
      key: e.key, name: e.name, event_date: e.event_date ?? "", end_date: e.end_date ?? "", venue: e.venue ?? "",
      headcount: e.headcount === null ? "" : String(e.headcount), attributes: [...e.attributes], possible_attributes: [...e.possible_attributes],
      cost: centsText(e.estimated_cost_cents), request: centsText(e.usg_request_cents), fund: e.fund ?? "",
    })),
  };
}

function toRequest(edit: EditPlan): { body: YearPlanRequest | null; problems: string[] } {
  const problems: string[] = [];
  const money = (text: string, label: string, blank: number | null): number | null => {
    if (text.trim() === "") return blank;
    const cents = toCents(text);
    if (cents === null) problems.push(`${label} must be a dollar amount, like 1200 or 1,200.50.`);
    return cents;
  };
  const onHand = money(edit.on_hand, "Money on hand", 0);
  const income = money(edit.income, "Expected income", 0);
  const received = money(edit.received, "Money already received from USG", null);
  const events: PlanEvent[] = edit.events.map((e, i) => {
    const label = e.name.trim() || `Event ${i + 1}`;
    if (!e.name.trim()) problems.push(`Event ${i + 1} needs a name.`);
    const cost = money(e.cost, `${label}: estimated cost`, 0) ?? 0;
    const request = money(e.request, `${label}: USG request`, 0) ?? 0;
    if (request > cost) problems.push(`${label}: the USG request cannot be more than the estimated cost.`);
    let headcount: number | null = null;
    if (e.headcount.trim() !== "") {
      if (/^\d+$/.test(e.headcount.trim())) headcount = Number(e.headcount.trim());
      else problems.push(`${label}: the headcount must be a whole number.`);
    }
    if (e.end_date && !e.event_date) problems.push(`${label}: give the first day as well as the last.`);
    if (e.end_date && e.event_date && e.end_date < e.event_date) problems.push(`${label}: the last day is before the first.`);
    return {
      key: e.key, name: e.name.trim() || label, event_date: e.event_date || null, end_date: e.end_date && e.end_date !== e.event_date ? e.end_date : null,
      venue: e.venue || null, headcount, attributes: e.attributes, possible_attributes: e.possible_attributes,
      estimated_cost_cents: cost, usg_request_cents: request, fund: e.fund || null,
    };
  });
  if (problems.length) return { body: null, problems };
  return {
    body: {
      club_name: edit.club_name, mission: edit.mission, level: edit.level || null, money_on_hand_cents: onHand ?? 0,
      expected_income_cents: income ?? 0, usg_received_this_year_cents: received, unavailable_dates: edit.unavailable.filter(Boolean), events,
    },
    problems: [],
  };
}

function loadSaved(): EditPlan {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...EMPTY_PLAN, ...(JSON.parse(raw) as EditPlan) };
  } catch {
    // Saved plans are a convenience only; start empty if the browser refuses.
  }
  return EMPTY_PLAN;
}

const input = "mt-1 w-full rounded-md border border-stone-400 bg-white p-2";

function EventEditor({ e, details, onChange, onDelete }: {
  e: EditEvent;
  details: Detail[];
  onChange: (change: Partial<EditEvent>) => void;
  onDelete: () => void;
}) {
  const ticked = new Set([...e.attributes, ...e.possible_attributes]);
  const id = `ev-${e.key}`;
  return (
    <li className="rounded-md border border-stone-300 bg-white p-4">
      <fieldset className="grid gap-3 sm:grid-cols-2">
        <legend className="sr-only">{e.name || "New event"}</legend>
        <label className="block sm:col-span-2"><span className="font-medium">Event name</span>
          <input value={e.name} maxLength={200} onChange={(x) => onChange({ name: x.target.value })} className={input} /></label>
        <label className="block"><span className="font-medium">First day</span>
          <input type="date" value={e.event_date} onChange={(x) => onChange({ event_date: x.target.value })} className={input} /></label>
        <label className="block"><span className="font-medium">Last day (if more than one)</span>
          <input type="date" value={e.end_date} onChange={(x) => onChange({ end_date: x.target.value })} className={input} /></label>
        <label className="block"><span className="font-medium">Venue</span>
          <select value={e.venue} onChange={(x) => onChange({ venue: x.target.value as VenueType | "" })} className={input}>
            <option value="">Not known yet</option>
            {Object.entries(VENUE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
        <label className="block"><span className="font-medium">About how many people</span>
          <input inputMode="numeric" value={e.headcount} onChange={(x) => onChange({ headcount: x.target.value })} className={input} /></label>
        <label className="block"><span className="font-medium">Rough cost ($)</span>
          <input inputMode="decimal" value={e.cost} onChange={(x) => onChange({ cost: x.target.value })} className={input} /></label>
        <label className="block"><span className="font-medium">Ask USG for ($, 0 for none)</span>
          <input inputMode="decimal" value={e.request} onChange={(x) => onChange({ request: x.target.value })} className={input} /></label>
        <label className="block sm:col-span-2"><span className="font-medium">USG fund (if you know it)</span>
          <select value={e.fund} onChange={(x) => onChange({ fund: x.target.value as FundId | "" })} className={input}>
            <option value="">Not chosen</option>
            {FUNDS.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
          </select></label>
      </fieldset>
      <details className="mt-3">
        <summary className="cursor-pointer font-medium">Event details ({ticked.size} ticked)</summary>
        {e.possible_attributes.length ? <p className="mt-2 text-sm"><StatusBadge state="yellow" label="Please confirm" /> Greenlight was not sure about the details marked "not sure". Tick to confirm or untick to remove.</p> : null}
        <div className="mt-2 grid gap-1 sm:grid-cols-2">
          {details.map((d) => (
            <label key={d.name} className="flex items-start gap-2 text-sm">
              <input id={`${id}-${d.name}`} type="checkbox" className="mt-1" checked={e.attributes.includes(d.name)}
                onChange={(x) => onChange({
                  attributes: x.target.checked ? [...new Set([...e.attributes, d.name])] : e.attributes.filter((a) => a !== d.name),
                  possible_attributes: e.possible_attributes.filter((a) => a !== d.name),
                })} />
              <span>{d.description}{e.possible_attributes.includes(d.name) ? " (not sure)" : ""}</span>
            </label>
          ))}
        </div>
      </details>
      <button type="button" onClick={onDelete} className="mt-3 rounded-md border border-red-700 px-3 py-1 text-sm text-red-900">Delete this event</button>
    </li>
  );
}

export function YearPlan() {
  const navigate = useNavigate();
  const [edit, setEdit] = useState<EditPlan>(loadSaved);
  const [details, setDetails] = useState<Detail[]>([]);
  const [report, setReport] = useState<YearPlanReport | null>(null);
  const [inputProblems, setInputProblems] = useState<string[]>([]);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState("");
  const [pasted, setPasted] = useState("");
  const [readRows, setReadRows] = useState<ReadRow[]>([]);
  const [reading, setReading] = useState(false);
  const [newDate, setNewDate] = useState("");
  const latest = useRef(0);

  useEffect(() => {
    getDetails().then((r) => (r.ok ? setDetails(r.data) : setError(r.error))).catch(() => undefined);
  }, []);

  // Every change recomputes the whole plan from scratch, so no date, sum or problem is left over from before.
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(edit));
    } catch {
      // Not saved in this browser; the plan still works.
    }
    const { body, problems } = toRequest(edit);
    setInputProblems(problems);
    const ticket = ++latest.current;
    if (!body) {
      setReport(null);
      setUpdating(false);
      return;
    }
    setUpdating(true);
    const timer = window.setTimeout(() => {
      computePlan(body).then((result) => {
        if (ticket !== latest.current) return;
        setUpdating(false);
        if (result.ok) {
          setReport(result.data);
          setError("");
        } else {
          setReport(null);
          setError(result.error);
        }
      }).catch(() => undefined);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [edit]);

  const setEvent = (key: string, change: Partial<EditEvent>) =>
    setEdit((old) => ({ ...old, events: old.events.map((e) => (e.key === key ? { ...e, ...change } : e)) }));

  async function loadDemo() {
    const result = await getDemoPlan();
    if (result.ok) setEdit(fromRequest(result.data));
    else setError(result.error);
  }

  async function read(event: FormEvent) {
    event.preventDefault();
    setReading(true);
    const result = await readEvents(pasted);
    setReading(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setReadRows(result.data.rows);
  }

  function addRead() {
    setEdit((old) => {
      const events = [...old.events];
      for (const row of readRows) {
        const base = blankEvent(events, row.facts?.name ?? row.text.slice(0, 200));
        const f: EventFacts | null = row.facts;
        events.push(f ? {
          ...base, event_date: f.event_date ?? "", end_date: f.end_date ?? "", venue: f.venue ?? "",
          headcount: f.headcount === null ? "" : String(f.headcount), attributes: f.attributes, possible_attributes: f.possible_attributes,
        } : base);
      }
      return { ...old, events };
    });
    setReadRows([]);
    setPasted("");
  }

  function openPacket(key: string) {
    const e = report?.events.find((x) => x.key === key);
    if (e) navigate("/events/packet", { state: { facts: { ...e.packet.event, needs_officer_input: [] } } });
  }

  function openMoney(key: string) {
    const e = report?.events.find((x) => x.key === key);
    if (!e) return;
    const facts = e.packet.event;
    const budgetEvent: BudgetEvent = {
      name: e.name, description: "", event_date: facts.event_date, end_date: facts.end_date, expected_attendance: facts.headcount,
      venue: facts.venue, ticketed: facts.attributes.includes("ticket_sales") ? true : null, open_to_all_students: null,
      attributes: facts.attributes.filter((a) => a !== "usg_funding" && a !== "ticket_sales" && !a.startsWith("venue_")),
    };
    navigate("/money/check", { state: { event: budgetEvent, received: edit.received } });
  }

  async function ics() {
    const { body } = toRequest(edit);
    if (!body) return;
    const result = await downloadPlanIcs(body);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    const url = URL.createObjectURL(result.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = "greenlight-year-plan.ics";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-10">
      <section aria-labelledby="plan-heading" className="space-y-3">
        <h1 id="plan-heading" className="text-3xl font-bold tracking-tight">Your club's year plan</h1>
        <p className="max-w-2xl text-stone-700">
          Enter your club's money and the events you want to run. Greenlight lays out every deadline on one calendar, splits
          your budget, plans what to ask Undergraduate Student Government (USG) for within its caps, and flags problems early.
          Change anything and the whole plan is worked out again.
        </p>
        <PrecheckNotice {...(report ? { text: report.notice } : {})} />
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={loadDemo} className="rounded-md bg-cardinal px-4 py-2 font-medium text-white">Load the demo club</button>
          <button type="button" onClick={() => { setEdit(EMPTY_PLAN); setReport(null); }} className="rounded-md border border-stone-400 px-4 py-2">Start an empty plan</button>
        </div>
        {error ? <p role="alert" className="rounded-md border border-red-700 bg-red-50 p-3 text-red-900">{error}</p> : null}
      </section>

      <div aria-live="polite" className="space-y-2">
        {inputProblems.length ? (
          <div role="alert" className="rounded-md border border-amber-700 bg-amber-50 p-3">
            <p className="font-medium">Fix these to see the plan:</p>
            <ul className="list-disc pl-5">{inputProblems.map((p) => <li key={p}>{p}</li>)}</ul>
          </div>
        ) : null}
        {updating ? <p className="text-stone-700">Working out the plan…</p> : null}
      </div>

      {report && !updating ? (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-medium">
              {report.counts.red ?? 0} red, {report.counts.yellow ?? 0} to check · {dollars(report.budget.shortfall_cents)} still to find
            </p>
            <button type="button" onClick={ics} className="rounded-md border border-stone-400 px-4 py-2">Download the calendar (.ics)</button>
          </div>
          <PlanResults report={report} onOpenPacket={openPacket} onOpenMoney={openMoney} />
        </>
      ) : null}
      <details open={edit.events.length === 0} className="space-y-6 rounded-md border border-stone-300 bg-stone-50 p-3">
        <summary className="cursor-pointer text-lg font-semibold">Edit the plan: club, money and {edit.events.length} events</summary>
        <div className="mt-4 space-y-8">
      <Section id="club-heading" title="Club and money">
        <div className="grid gap-3 rounded-md border border-stone-300 bg-white p-4 sm:grid-cols-2">
          <label className="block"><span className="font-medium">Club name</span>
            <input value={edit.club_name} maxLength={200} onChange={(x) => setEdit({ ...edit, club_name: x.target.value })} className={input} /></label>
          <label className="block"><span className="font-medium">Undergraduate or graduate</span>
            <select value={edit.level} onChange={(x) => setEdit({ ...edit, level: x.target.value as EditPlan["level"] })} className={input}>
              <option value="">Not said</option><option value="undergraduate">Undergraduate</option><option value="graduate">Graduate</option>
            </select></label>
          <label className="block sm:col-span-2"><span className="font-medium">Purpose or mission</span>
            <textarea value={edit.mission} maxLength={2000} rows={2} onChange={(x) => setEdit({ ...edit, mission: x.target.value })} className={input} /></label>
          <label className="block"><span className="font-medium">Money on hand ($)</span>
            <input inputMode="decimal" value={edit.on_hand} onChange={(x) => setEdit({ ...edit, on_hand: x.target.value })} className={input} /></label>
          <label className="block"><span className="font-medium">Expected income ($)</span>
            <input inputMode="decimal" value={edit.income} onChange={(x) => setEdit({ ...edit, income: x.target.value })} className={input} /></label>
          <label className="block sm:col-span-2"><span className="font-medium">Already received from USG this academic year ($; leave empty if you do not know)</span>
            <input inputMode="decimal" value={edit.received} onChange={(x) => setEdit({ ...edit, received: x.target.value })} className={input} /></label>
          <div className="sm:col-span-2">
            <label htmlFor="unavailable" className="font-medium">Dates the officers are unavailable</label>
            <div className="mt-1 flex flex-wrap gap-2">
              <input id="unavailable" type="date" value={newDate} onChange={(x) => setNewDate(x.target.value)} className="rounded-md border border-stone-400 p-2" />
              <button type="button" disabled={!newDate} onClick={() => { setEdit({ ...edit, unavailable: [...new Set([...edit.unavailable, newDate])].sort() }); setNewDate(""); }} className="rounded-md border border-stone-400 px-3 py-2 disabled:opacity-60">Add date</button>
            </div>
            <ul className="mt-2 flex flex-wrap gap-2">
              {edit.unavailable.map((d) => (
                <li key={d}><button type="button" onClick={() => setEdit({ ...edit, unavailable: edit.unavailable.filter((x) => x !== d) })} className="rounded-full border border-stone-400 px-3 py-1 text-sm" aria-label={`Remove ${d}`}>{d} ✕</button></li>
              ))}
            </ul>
          </div>
        </div>
      </Section>

      <Section id="events-edit-heading" title={`Events (${edit.events.length})`} intro="You supply the events; Greenlight never invents them.">
        <form onSubmit={read} className="space-y-2 rounded-md border border-stone-300 bg-white p-4">
          <label htmlFor="paste" className="block font-medium">Paste a list, one event per line (optional)</label>
          <textarea id="paste" value={pasted} onChange={(x) => setPasted(x.target.value)} rows={3} className={input}
            placeholder="Culture night for about 150 people on McCarthy Quad on Friday, April 9, 2027, with a DJ and catered food." />
          <button type="submit" disabled={reading || !pasted.trim()} className="rounded-md border border-stone-400 px-4 py-2 disabled:opacity-60">{reading ? "Reading…" : "Read my list"}</button>
          {readRows.length ? (
            <div className="space-y-2">
              <p className="text-sm">Greenlight read these. Costs are never read: type them in after adding. Check every detail.</p>
              <ul className="space-y-1 text-sm">
                {readRows.map((r) => (
                  <li key={r.line}>
                    <StatusBadge state={r.facts ? "info" : "yellow"} label={r.facts ? "Read" : "Fill in by hand"} /> {r.text}
                    {r.error ? <span className="block text-stone-700">{r.error}</span> : null}
                    {r.had_instructions ? <span className="block text-stone-700">This line contained words that read like instructions; they were treated as text.</span> : null}
                  </li>
                ))}
              </ul>
              <button type="button" onClick={addRead} className="rounded-md bg-cardinal px-4 py-2 font-medium text-white">Add these to the plan</button>
            </div>
          ) : null}
        </form>
        <ul className="space-y-3">
          {edit.events.map((e) => (
            <EventEditor key={e.key} e={e} details={details} onChange={(c) => setEvent(e.key, c)}
              onDelete={() => setEdit({ ...edit, events: edit.events.filter((x) => x.key !== e.key) })} />
          ))}
        </ul>
        <button type="button" onClick={() => setEdit({ ...edit, events: [...edit.events, blankEvent(edit.events)] })} className="rounded-md border border-stone-400 px-4 py-2">Add an event</button>
      </Section>

        </div>
      </details>
    </div>
  );
}
