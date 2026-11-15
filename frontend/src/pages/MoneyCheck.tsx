import { useEffect, useState, type FormEvent } from "react";
import { useLocation } from "react-router-dom";

import { VENUE_LABELS, type Finding, type VenueType } from "../api/events";
import {
  approveDraft,
  checkBudget,
  dollars,
  draftApplication,
  getVocabulary,
  readDocuments,
  readFund,
  toCents,
  type BudgetEvent,
  type BudgetLine,
  type ClubMoney,
  type FundId,
  type FundReading,
  type MoneyCheckRequest,
  type MoneyFinding,
  type MoneyReport,
  type MoneyVocabulary,
  type PurchaseChannel,
  type QuoteDocument,
} from "../api/money";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { SourceLink } from "../components/SourceLink";
import { StatusBadge, type BadgeState } from "../components/StatusBadge";

// Lines are edited as text so a half-typed amount is never turned into a number the officer did not mean.
interface EditLine {
  vendor: string;
  item: string;
  category: string;
  category_sure: boolean;
  quantity: string;
  unit_price: string;
  amount: string;
  nights: string;
  has_quote: boolean;
  purchase_channel: PurchaseChannel;
  has_cart_screenshot: boolean;
  has_wish_list_link: boolean;
  document: number | null;
  unsure: string[];
}

const BLANK_LINE: EditLine = {
  vendor: "", item: "", category: "", category_sure: true, quantity: "1", unit_price: "", amount: "", nights: "",
  has_quote: false, purchase_channel: "vendor_quote", has_cart_screenshot: false, has_wish_list_link: false, document: null, unsure: [],
};

const BLANK_EVENT: BudgetEvent = {
  name: "", description: "", event_date: null, end_date: null, expected_attendance: null, venue: null, ticketed: null,
  open_to_all_students: null, attributes: [],
};

// The demo club's culture night (the story in PROJECT_CONTEXT section 11). Typed by hand, not read by the model.
const DEMO_EVENT: BudgetEvent = {
  name: "Culture Night", description: "Cultural celebration with food, music and dance performances", event_date: "2027-04-09",
  end_date: null, expected_attendance: 150, venue: "venue_outdoor", ticketed: true, open_to_all_students: true, attributes: [],
};
const DEMO_LINES: EditLine[] = [
  { ...BLANK_LINE, vendor: "Trojan Table Catering", item: "Buffet dinner for 150 guests", category: "food", quantity: "150", unit_price: "38.00", amount: "5700.00", has_quote: true },
  { ...BLANK_LINE, vendor: "Nova Sound DJ", item: "DJ performance, 4 hours", category: "performer_fee", unit_price: "800.00", amount: "800.00", has_quote: true },
  { ...BLANK_LINE, vendor: "Westside Event Rentals", item: "Speakers and stage lighting rental", category: "av_equipment", unit_price: "450.00", amount: "450.00", has_quote: true },
  { ...BLANK_LINE, vendor: "Campus Print Shop", item: "Flyers and posters", category: "printing", unit_price: "120.00", amount: "120.00", has_quote: true },
];

const TRI: { value: string; label: string }[] = [
  { value: "", label: "Not sure" },
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

function tri(value: boolean | null): string {
  return value === null ? "" : value ? "yes" : "no";
}
function fromTri(value: string): boolean | null {
  return value === "" ? null : value === "yes";
}

function badge(verdict: string): BadgeState {
  return (["green", "yellow", "red", "office_decides"].includes(verdict) ? verdict : "info") as BadgeState;
}

const REASON_LABELS: Record<string, string> = {
  category_unclear: "Category unclear",
  duplicate_line: "Possible duplicate",
  totals_mismatch: "Numbers do not add up",
  cannot_compute: "Cannot work it out",
  not_read: "Could not read",
};

function FindingItem({ finding, reason }: { finding: Finding; reason?: string }) {
  return (
    <li className="rounded border border-stone-200 bg-stone-50 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge state={badge(finding.verdict)} />
        {reason && reason !== "rule" ? <span className="text-sm text-stone-700">{REASON_LABELS[reason] ?? reason}</span> : null}
      </div>
      <p className="mt-1">{finding.message}</p>
      {finding.fix ? <p className="mt-1 text-sm"><span className="font-medium">Fix: </span>{finding.fix}</p> : null}
      <details className="mt-1">
        <summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Rule text and source</summary>
        <SourceLink citation={finding.citation} />
      </details>
    </li>
  );
}

function toRequestLines(lines: EditLine[]): { lines: BudgetLine[]; problems: string[] } {
  const out: BudgetLine[] = [];
  const problems: string[] = [];
  lines.forEach((l, i) => {
    const n = i + 1;
    const quantity = /^\d+$/.test(l.quantity.trim()) ? Number(l.quantity) : null;
    const unit = toCents(l.unit_price);
    const amount = toCents(l.amount);
    const nights = l.nights.trim() === "" ? null : /^\d+$/.test(l.nights.trim()) ? Number(l.nights) : NaN;
    if (quantity === null) problems.push(`Line ${n}: the quantity must be a whole number.`);
    if (unit === null) problems.push(`Line ${n}: the unit price must be a dollar amount such as 38.00.`);
    if (amount === null) problems.push(`Line ${n}: the amount must be a dollar amount such as 5700.00.`);
    if (Number.isNaN(nights)) problems.push(`Line ${n}: nights must be a whole number.`);
    if (quantity === null || unit === null || amount === null || Number.isNaN(nights)) return;
    out.push({
      line: n, vendor: l.vendor, item: l.item, category: l.category || null, category_sure: l.category_sure, quantity,
      unit_price_cents: unit, amount_cents: amount, nights: nights as number | null, has_quote: l.has_quote,
      purchase_channel: l.purchase_channel, has_cart_screenshot: l.purchase_channel === "online_cart" ? l.has_cart_screenshot : null,
      has_wish_list_link: l.purchase_channel === "amazon" ? l.has_wish_list_link : null, document: l.document,
    });
  });
  return { lines: out, problems };
}

const centsText = (cents: number | null) => (cents === null ? "" : (cents / 100).toFixed(2));

export function MoneyCheck() {
  const [vocab, setVocab] = useState<MoneyVocabulary | null>(null);
  const [event, setEvent] = useState<BudgetEvent>(BLANK_EVENT);
  const [club, setClub] = useState({ received: "", funded: "" });
  const [attachments, setAttachments] = useState<string[]>([]);
  const [lines, setLines] = useState<EditLine[]>([{ ...BLANK_LINE }]);
  const [documents, setDocuments] = useState<QuoteDocument[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [pasted, setPasted] = useState("");
  const [readProblems, setReadProblems] = useState<string[]>([]);
  const [fund, setFund] = useState<FundId | "">("");
  const [fundReading, setFundReading] = useState<FundReading | null>(null);
  const [report, setReport] = useState<MoneyReport | null>(null);
  const [purpose, setPurpose] = useState("");
  const [draft, setDraft] = useState("");
  const [draftNotes, setDraftNotes] = useState<string[]>([]);
  const [approved, setApproved] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  // Opened from the year plan: start from that event. Ticket sales and openness stay unknown unless the plan said so.
  const location = useLocation();
  useEffect(() => {
    const state = location.state as { event?: BudgetEvent; received?: string } | null;
    if (state?.event) {
      setEvent(state.event);
      setClub((old) => ({ ...old, received: state.received ?? "" }));
    }
  }, [location.state]);

  useEffect(() => {
    getVocabulary().then((r) => (r.ok ? setVocab(r.data) : setError(r.error))).catch(() => undefined);
  }, []);

  const categoryLabel = (name: string) => vocab?.categories.find((c) => c.name === name)?.description ?? name;
  const fundName = (id: string) => vocab?.funds.find((f) => f.id === id)?.name ?? id;

  function setLine(i: number, change: Partial<EditLine>) {
    setLines((old) => old.map((l, j) => (j === i ? { ...l, ...change } : l)));
    setReport(null);
  }

  function loadDemo() {
    setEvent(DEMO_EVENT);
    setLines(DEMO_LINES.map((l) => ({ ...l })));
    setAttachments(["esr", "hospitality_food_form", "food_health_permit_and_insurance", "food_justification"]);
    setClub({ received: "0", funded: "0" });
    setFund("usg-fund-social-recreation-startup");
    setDocuments([]);
    setReport(null);
    setDraft("");
    setApproved("");
  }

  function request(): { body: MoneyCheckRequest | null; problems: string[] } {
    const converted = toRequestLines(lines);
    const received = club.received.trim() === "" ? null : toCents(club.received);
    const funded = club.funded.trim() === "" ? null : /^\d+$/.test(club.funded.trim()) ? Number(club.funded) : NaN;
    const problems = [...converted.problems];
    if (club.received.trim() !== "" && received === null) problems.push("The amount received from USG this year must be a dollar amount.");
    if (Number.isNaN(funded)) problems.push("The number of funded events must be a whole number.");
    if (converted.lines.length === 0) problems.push("Add at least one budget line.");
    if (problems.length) return { body: null, problems };
    const clubMoney: ClubMoney = { usg_received_this_year_cents: received, usg_funded_events_this_semester: funded as number | null, first_registered: null };
    return {
      body: { event, club: clubMoney, attachments, lines: converted.lines, documents, fund: fund || null, fund_reading: fund ? null : fundReading },
      problems: [],
    };
  }

  async function read(e: FormEvent) {
    e.preventDefault();
    setBusy("reading");
    setError("");
    const result = await readDocuments(files, pasted);
    setBusy("");
    if (!result.ok) {
      setError(`${result.error} You can type the lines in by hand.`);
      return;
    }
    // Document numbers continue after the ones already read.
    const offset = documents.length;
    const docs = result.data.documents.map((d) => ({ ...d, index: d.index + offset }));
    setDocuments((old) => [...old, ...docs]);
    setReadProblems(result.data.problems.map((p) => `${p.name}: ${p.message}`));
    const added: EditLine[] = result.data.suggested_lines.map((s) => ({
      vendor: s.vendor, item: s.item, category: s.category ?? "", category_sure: s.category_sure,
      quantity: s.quantity === null ? "" : String(s.quantity), unit_price: centsText(s.unit_price_cents), amount: centsText(s.amount_cents),
      nights: s.nights === null ? "" : String(s.nights), has_quote: s.has_quote, purchase_channel: s.purchase_channel,
      has_cart_screenshot: Boolean(s.has_cart_screenshot), has_wish_list_link: false,
      document: s.document === null ? null : s.document + offset, unsure: s.unsure,
    }));
    setLines((old) => [...old.filter((l) => l.vendor || l.item || l.amount), ...added]);
    setFiles([]);
    setPasted("");
    setReport(null);
  }

  async function askFund() {
    setBusy("fund");
    setError("");
    const result = await readFund(event.name, event.description);
    setBusy("");
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setFundReading(result.data.reading);
    setFund("");
  }

  async function check(e: FormEvent) {
    e.preventDefault();
    const { body, problems } = request();
    if (!body) {
      setError(problems.join(" "));
      return;
    }
    setBusy("checking");
    setError("");
    setDraft("");
    setApproved("");
    const result = await checkBudget(body);
    setBusy("");
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setReport(result.data);
  }

  async function makeDraft() {
    const { body, problems } = request();
    if (!body) {
      setError(problems.join(" "));
      return;
    }
    setBusy("drafting");
    setError("");
    const result = await draftApplication(body, purpose);
    setBusy("");
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setDraft(result.data.text);
    setDraftNotes(result.data.notes);
    setApproved("");
  }

  async function approve() {
    setBusy("approving");
    const result = await approveDraft(draft, event.name);
    setBusy("");
    if (result.ok) setApproved(result.data.message);
    else setError(result.error);
  }

  const input = "mt-1 w-full rounded border border-stone-400 px-2 py-1";

  return (
    <div className="space-y-8">
      <header>
        <h2 className="text-2xl font-semibold">Money check</h2>
        <p className="mt-1 max-w-3xl">
          Upload the quotes for one event. Greenlight checks every line against the Undergraduate Student Government (USG) funding
          rules, shows a fix for each problem, names the fund, and drafts the application once nothing is red. You approve the draft
          and paste it into EngageSC yourself: Greenlight never submits anything.
        </p>
        <button type="button" onClick={loadDemo} className="mt-2 text-sm text-cardinal underline underline-offset-2">
          Load the demo club's culture night budget
        </button>
      </header>

      <form onSubmit={read} className="space-y-3 rounded-md border border-stone-300 bg-white p-4" aria-labelledby="read-title">
        <h3 id="read-title" className="text-lg font-semibold">1. Upload quotes (optional)</h3>
        <p className="text-sm text-stone-700">PDF, image or screenshot, Word file, or pasted text. Greenlight reads the lines into the budget below for you to check. Text inside a file is never followed as an instruction.</p>
        <label className="block">
          <span className="font-medium">Files</span>
          <input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.docx,.txt" className="mt-1 block"
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
        </label>
        <label className="block">
          <span className="font-medium">Or paste a quote</span>
          <textarea value={pasted} onChange={(e) => setPasted(e.target.value)} rows={3} className={input} />
        </label>
        <button type="submit" disabled={busy !== "" || (!files.length && !pasted.trim())}
          className="rounded bg-cardinal px-4 py-2 font-medium text-white disabled:opacity-50">
          {busy === "reading" ? "Reading…" : "Read the quotes"}
        </button>
        {readProblems.length ? <ul className="list-disc pl-5 text-sm text-red-900">{readProblems.map((p) => <li key={p}>{p}</li>)}</ul> : null}
        {documents.length ? (
          <ul className="space-y-1 text-sm">
            {documents.map((d) => (
              <li key={d.index}>
                <span className="font-medium">Document {d.index}: {d.name}</span>
                {d.vendor ? ` — ${d.vendor}` : ""}
                {d.stated_total_cents !== null ? `, total shown ${dollars(d.stated_total_cents)}` : ""}
                {d.notes.map((n) => <span key={n} className="block text-amber-950">! {n}</span>)}
              </li>
            ))}
          </ul>
        ) : null}
      </form>

      <form onSubmit={check} className="space-y-6">
        <fieldset className="grid gap-3 rounded-md border border-stone-300 bg-white p-4 sm:grid-cols-2">
          <legend className="px-1 text-lg font-semibold">2. The event</legend>
          <label>Name<input className={input} value={event.name} onChange={(e) => setEvent({ ...event, name: e.target.value })} /></label>
          <label>Date<input type="date" className={input} value={event.event_date ?? ""} onChange={(e) => setEvent({ ...event, event_date: e.target.value || null })} /></label>
          <label className="sm:col-span-2">What the event is<textarea rows={2} className={input} value={event.description} onChange={(e) => setEvent({ ...event, description: e.target.value })} /></label>
          <label>Last day (if more than one day)<input type="date" className={input} value={event.end_date ?? ""} onChange={(e) => setEvent({ ...event, end_date: e.target.value || null })} /></label>
          <label>Expected attendance<input inputMode="numeric" className={input} value={event.expected_attendance ?? ""}
            onChange={(e) => setEvent({ ...event, expected_attendance: /^\d+$/.test(e.target.value) ? Number(e.target.value) : null })} /></label>
          <label>Venue
            <select className={input} value={event.venue ?? ""} onChange={(e) => setEvent({ ...event, venue: (e.target.value || null) as VenueType | null })}>
              <option value="">Not sure</option>
              {Object.entries(VENUE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label>Sells tickets or charges entry?
            <select className={input} value={tri(event.ticketed)} onChange={(e) => setEvent({ ...event, ticketed: fromTri(e.target.value) })}>
              {TRI.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </label>
          <label>Open to all students?
            <select className={input} value={tri(event.open_to_all_students)} onChange={(e) => setEvent({ ...event, open_to_all_students: fromTri(e.target.value) })}>
              {TRI.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </label>
          <label>USG money already received this year ($)<input className={input} value={club.received} onChange={(e) => setClub({ ...club, received: e.target.value })} /></label>
          <label>Events USG already funded this semester<input inputMode="numeric" className={input} value={club.funded} onChange={(e) => setClub({ ...club, funded: e.target.value })} /></label>
          <fieldset className="sm:col-span-2">
            <legend className="font-medium">Also true of this event</legend>
            {vocab?.event_details.map((d) => (
              <label key={d.name} className="mr-4 inline-flex items-center gap-1">
                <input type="checkbox" checked={event.attributes.includes(d.name)}
                  onChange={(e) => setEvent({ ...event, attributes: e.target.checked ? [...event.attributes, d.name] : event.attributes.filter((a) => a !== d.name) })} />
                {d.description}
              </label>
            ))}
          </fieldset>
        </fieldset>

        <fieldset className="rounded-md border border-stone-300 bg-white p-4">
          <legend className="px-1 text-lg font-semibold">3. Budget lines</legend>
          <ol className="space-y-4">
            {lines.map((l, i) => (
              <li key={i} className="rounded border border-stone-200 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Line {i + 1}{l.document ? ` (from document ${l.document})` : ""}</span>
                  <button type="button" className="text-sm text-cardinal underline" onClick={() => setLines(lines.filter((_, j) => j !== i))}>Remove line {i + 1}</button>
                </div>
                {l.unsure.length ? <p className="text-sm text-amber-950">! Greenlight was not sure of: {l.unsure.join(", ")}. Check these against the quote.</p> : null}
                <div className="mt-2 grid gap-2 sm:grid-cols-4">
                  <label>Vendor<input className={input} value={l.vendor} onChange={(e) => setLine(i, { vendor: e.target.value })} /></label>
                  <label className="sm:col-span-2">Item<input className={input} value={l.item} onChange={(e) => setLine(i, { item: e.target.value })} /></label>
                  <label>Category
                    <select className={input} value={l.category} onChange={(e) => setLine(i, { category: e.target.value, category_sure: true })}>
                      <option value="">Not sure</option>
                      {vocab?.categories.map((c) => <option key={c.name} value={c.name}>{c.description}</option>)}
                    </select>
                  </label>
                  {!l.category_sure && l.category ? (
                    <label className="inline-flex items-center gap-1 sm:col-span-4">
                      <input type="checkbox" checked={false} onChange={() => setLine(i, { category_sure: true })} />
                      Greenlight guessed "{categoryLabel(l.category)}". Tick to confirm it.
                    </label>
                  ) : null}
                  <label>Quantity<input inputMode="numeric" className={input} value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} /></label>
                  <label>Unit price ($)<input inputMode="decimal" className={input} value={l.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value })} /></label>
                  <label>Amount ($)<input inputMode="decimal" className={input} value={l.amount} onChange={(e) => setLine(i, { amount: e.target.value })} /></label>
                  <label>Nights (hotel rooms)<input inputMode="numeric" className={input} value={l.nights} onChange={(e) => setLine(i, { nights: e.target.value })} /></label>
                  <label>Bought
                    <select className={input} value={l.purchase_channel} onChange={(e) => setLine(i, { purchase_channel: e.target.value as PurchaseChannel })}>
                      <option value="vendor_quote">From a vendor, with a quote</option>
                      <option value="online_cart">Online shop</option>
                      <option value="amazon">Amazon</option>
                    </select>
                  </label>
                  <label className="inline-flex items-center gap-1"><input type="checkbox" checked={l.has_quote} onChange={(e) => setLine(i, { has_quote: e.target.checked })} />Quote attached</label>
                  {l.purchase_channel === "online_cart" ? (
                    <label className="inline-flex items-center gap-1"><input type="checkbox" checked={l.has_cart_screenshot} onChange={(e) => setLine(i, { has_cart_screenshot: e.target.checked })} />Cart screenshot with all fees attached</label>
                  ) : null}
                  {l.purchase_channel === "amazon" ? (
                    <label className="inline-flex items-center gap-1"><input type="checkbox" checked={l.has_wish_list_link} onChange={(e) => setLine(i, { has_wish_list_link: e.target.checked })} />Wish list link given</label>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
          <button type="button" className="mt-3 text-cardinal underline" onClick={() => setLines([...lines, { ...BLANK_LINE }])}>Add a line</button>
        </fieldset>

        <fieldset className="rounded-md border border-stone-300 bg-white p-4">
          <legend className="px-1 text-lg font-semibold">4. Documents attached to the application</legend>
          {vocab?.attachments.map((a) => (
            <label key={a.name} className="block">
              <input type="checkbox" className="mr-2" checked={attachments.includes(a.name)}
                onChange={(e) => setAttachments(e.target.checked ? [...attachments, a.name] : attachments.filter((x) => x !== a.name))} />
              {a.description}
            </label>
          ))}
        </fieldset>

        <fieldset className="rounded-md border border-stone-300 bg-white p-4">
          <legend className="px-1 text-lg font-semibold">5. Fund</legend>
          <label className="block">Which fund
            <select className={input} value={fund} onChange={(e) => setFund(e.target.value as FundId | "")}>
              <option value="">Let Greenlight read it from the description</option>
              {vocab?.funds.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </label>
          {!fund ? (
            <button type="button" onClick={askFund} disabled={busy !== "" || !(event.name || event.description)} className="mt-2 text-cardinal underline disabled:opacity-50">
              {busy === "fund" ? "Reading…" : "Read the fund from the description"}
            </button>
          ) : null}
          {fundReading && !fund ? <p className="mt-1 text-sm">Read: {fundReading.fund ? fundName(fundReading.fund) : "no clear fund"} ({fundReading.confidence} confidence). The check shows it as a match only when it is sure.</p> : null}
        </fieldset>

        <button type="submit" disabled={busy !== ""} className="rounded bg-cardinal px-4 py-2 font-medium text-white disabled:opacity-50">
          {busy === "checking" ? "Checking…" : "Check the budget"}
        </button>
      </form>

      {error ? <p role="alert" className="rounded border border-red-700 bg-red-50 p-3 text-red-900">{error}</p> : null}

      {report ? (
        <section aria-labelledby="report-title" className="space-y-6">
          <div className="flex flex-wrap items-center gap-3">
            <h3 id="report-title" className="text-xl font-semibold">Report</h3>
            <StatusBadge state={badge(report.verdict)} label={`Overall: ${report.verdict_label}`} />
          </div>
          <PrecheckNotice />
          <dl className="grid gap-2 text-sm sm:grid-cols-3">
            <div><dt className="text-stone-600">Total asked</dt><dd className="font-semibold">{dollars(report.totals.total_cents)}</dd></div>
            {report.totals.food_per_person_text ? <div><dt className="text-stone-600">Food per person</dt><dd className="font-semibold">{report.totals.food_per_person_text}</dd></div> : null}
            {report.totals.usg_year_total_cents !== null ? <div><dt className="text-stone-600">USG total this year with this request</dt><dd className="font-semibold">{dollars(report.totals.usg_year_total_cents)}</dd></div> : null}
          </dl>
          {report.questions.length ? (
            <div className="rounded border border-amber-700 bg-amber-50 p-3"><p className="font-medium">Questions for you</p><ul className="list-disc pl-5">{report.questions.map((q) => <li key={q}>{q}</li>)}</ul></div>
          ) : null}

          <div>
            <h4 className="text-lg font-semibold">Lines</h4>
            <ul className="mt-2 space-y-3">
              {report.lines.map((line) => (
                <li key={line.line} className="rounded-md border border-stone-300 bg-white p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="font-semibold">Line {line.line}: {line.item || "(no item)"} — {dollars(line.amount_cents)}</p>
                      <p className="text-sm text-stone-600">{line.vendor || "No vendor"} · {line.category_label ?? "Category not known"}</p>
                    </div>
                    <StatusBadge state={badge(line.verdict)} />
                  </div>
                  {line.findings.length ? <ul className="mt-2 space-y-2">{line.findings.map((f, i) => <FindingItem key={i} finding={f.finding} reason={f.reason} />)}</ul> : null}
                  {line.passed.length ? (
                    <details className="mt-2"><summary className="cursor-pointer text-sm">Rules this line meets ({line.passed.length})</summary>
                      <ul className="mt-2 space-y-2">{line.passed.map((f) => <FindingItem key={f.rule_id} finding={f} />)}</ul></details>
                  ) : null}
                  <details className="mt-2"><summary className="cursor-pointer text-sm">Vendor list check (separate from eligibility): needs a human look</summary>
                    <ul className="mt-2"><FindingItem finding={line.vendor_check.finding} /></ul></details>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-lg font-semibold">The application as a whole</h4>
            {report.application.length ? <ul className="mt-2 space-y-2">{report.application.map((f: MoneyFinding, i) => <FindingItem key={i} finding={f.finding} reason={f.reason} />)}</ul> : <p>No findings.</p>}
            {report.application_passed.length ? (
              <details className="mt-2"><summary className="cursor-pointer text-sm">Rules the application meets ({report.application_passed.length})</summary>
                <ul className="mt-2 space-y-2">{report.application_passed.map((f) => <FindingItem key={f.rule_id} finding={f} />)}</ul></details>
            ) : null}
          </div>

          <div className="rounded-md border border-stone-300 bg-white p-4">
            <h4 className="text-lg font-semibold">Fund</h4>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              {report.fund.verdict ? <StatusBadge state="yellow" /> : <StatusBadge state="info" label={report.fund.status === "officer_chose" ? "Your choice" : "Matched from the description"} />}
              <span className="font-medium">{report.fund.fund_name ?? `Could be: ${report.fund.candidates.map(fundName).join(" or ")}`}</span>
            </div>
            <p className="mt-1">{report.fund.explanation}</p>
            <details className="mt-1"><summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Fund descriptions and sources</summary>
              {report.fund.citations.map((c) => <SourceLink key={c.rule_id} citation={c} />)}</details>
          </div>

          <div>
            <h4 className="text-lg font-semibold">USG dates for this event</h4>
            <ul className="mt-2 space-y-2">
              {report.dates.filter((o) => !o.superseded_by).map((o) => (
                <li key={o.rule_id} className="rounded border border-stone-200 bg-white p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    {o.finding ? <StatusBadge state={badge(o.finding.verdict)} /> : <StatusBadge state="info" label={o.status_label} />}
                    <span className="font-medium">{o.title}</span>
                  </div>
                  <p className="mt-1 text-sm">{o.due ? `Due ${o.due}. ` : ""}{o.due_note ?? o.note ?? ""}</p>
                  <details className="mt-1"><summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Rule text and source</summary><SourceLink citation={o.citation} /></details>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-md border border-stone-300 bg-white p-4">
            <h4 className="text-lg font-semibold">Draft the application</h4>
            {report.draft_allowed ? (
              <>
                <label className="block">Why the event matters, in your words
                  <textarea rows={3} className={input} value={purpose} onChange={(e) => setPurpose(e.target.value)} />
                </label>
                <button type="button" onClick={makeDraft} disabled={busy !== ""} className="mt-2 rounded bg-cardinal px-4 py-2 font-medium text-white disabled:opacity-50">
                  {busy === "drafting" ? "Drafting…" : "Draft the application"}
                </button>
              </>
            ) : (
              <div>
                <p>Greenlight drafts the application only when no red item remains. Fix these first:</p>
                <ul className="list-disc pl-5">{report.draft_blocked_by.map((b) => <li key={b}>{b}</li>)}</ul>
              </div>
            )}
            {draft ? (
              <div className="mt-3">
                {draftNotes.map((n) => <p key={n} className="text-sm text-amber-950">! {n}</p>)}
                <label className="block">Draft (edit it before approving)
                  <textarea rows={18} className={`${input} font-mono text-sm`} value={draft} onChange={(e) => { setDraft(e.target.value); setApproved(""); }} />
                </label>
                <button type="button" onClick={approve} disabled={busy !== "" || !draft.trim()} className="mt-2 rounded border border-cardinal px-4 py-2 font-medium text-cardinal disabled:opacity-50">
                  I have read and approve this text
                </button>
                {approved ? <p role="status" className="mt-2 font-medium">{approved}</p> : null}
              </div>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}
