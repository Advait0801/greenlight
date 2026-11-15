import { useState, type ReactNode } from "react";

import { dollars } from "../api/money";
import type { CalendarItem, PlanProblem, TableDeadline, YearPlanReport } from "../api/plans";
import { formatDay } from "../components/EventTimeline";
import { SourceLink } from "../components/SourceLink";
import { StatusBadge, type BadgeState } from "../components/StatusBadge";
import { MasterDetail, Panel, SummaryStats, Tabs, type Stat } from "../components/ui";

export function Section({ id, title, children, intro }: { id: string; title: string; intro?: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="space-y-3">
      <h2 id={id} className="text-xl font-semibold">{title}</h2>
      {intro ? <p className="text-sm text-stone-700">{intro}</p> : null}
      {children}
    </section>
  );
}

function itemBadge(item: CalendarItem): { state: BadgeState; label: string } {
  if (item.kind === "event") return { state: "info", label: "The event" };
  if (item.past_due) return { state: item.unconfirmed ? "yellow" : "red", label: item.unconfirmed ? "May have passed: check with USG" : "Passed" };
  if (item.unconfirmed) return { state: "yellow", label: "Check with USG" };
  if (item.status === "office_decides") return { state: "office_decides", label: "Contact the office" };
  if (item.status === "check_with_office") return { state: "yellow", label: "Check with the office" };
  if (item.status === "blocked") return { state: "red", label: "Blocked as described" };
  return { state: "info", label: item.status_label };
}

function Sources({ citations }: { citations: (TableDeadline["citation"] | null)[] }) {
  const shown = citations.filter((c): c is NonNullable<typeof c> => c !== null);
  if (!shown.length) return null;
  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-sm text-cardinal">Rule text and source</summary>
      {shown.map((c) => <SourceLink key={c.rule_id} citation={c} />)}
    </details>
  );
}

function ProblemCard({ p, names }: { p: PlanProblem; names: Record<string, string> }) {
  const who = p.events.length > 2 ? `${p.events.length} events` : p.events.map((k) => names[k] ?? k).join(", ");
  return (
    <li className="border-b border-stone-200 py-4 last:border-b-0">
      <div className="flex items-start justify-between gap-3">
        <p className="font-medium" title={p.events.map((k) => names[k] ?? k).join(", ")}>{who}</p>
        <StatusBadge state={p.severity} label={p.severity_label} />
      </div>
      {p.fix ? <p className="mt-1 text-sm text-stone-700">{p.fix}</p> : null}
      <details className="mt-1">
        <summary className="cursor-pointer text-sm text-cardinal">Why?</summary>
        <p className="mt-2 text-sm">{p.note}</p>
        <p className="mt-1 text-sm text-stone-600">Events: {p.events.map((k) => names[k] ?? k).join(", ")}</p>
        {p.citation ? [p.citation, ...p.also_cites].filter((c): c is NonNullable<typeof c> => c !== null).map((c) => <SourceLink key={c.rule_id} citation={c} />) : <p className="mt-2 text-xs text-stone-600">From your own plan, not a USC rule.</p>}
      </details>
    </li>
  );
}

function deadlineText(d: TableDeadline): string {
  const table = d.table_date
    ? `USG's table (Greenlight's unconfirmed copy) says ${formatDay(d.table_date)}`
    : d.table_status === "not_in_table" ? "USG's table has no row for this week" : "USG's table lists no deadline for this week";
  return `${table}; counted back in calendar weeks it is ${formatDay(d.calendar_count)}. Apply by the earlier date, ${formatDay(d.apply_by)}.`;
}

function weekOf(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const day = new Date(Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1));
  day.setUTCDate(day.getUTCDate() - ((day.getUTCDay() + 6) % 7));
  return day.toISOString().slice(0, 10);
}

function namesOf(report: YearPlanReport): Record<string, string> {
  return Object.fromEntries(report.events.map((e) => [e.key, e.name]));
}

export function planStats(report: YearPlanReport): Stat[] {
  return [
    { label: "Breaks a rule", value: report.counts.red ?? 0, tone: "red", hint: "red items across the plan" },
    { label: "To check", value: report.counts.yellow ?? 0, tone: "yellow", hint: "need a person to confirm" },
    { label: "Events", value: report.events.length, hint: `${report.calendar.filter((c) => c.kind !== "event").length} dated deadlines` },
    { label: "Still to find", value: dollars(report.budget.shortfall_cents), tone: report.budget.shortfall_cents > 0 ? "yellow" : "info", hint: "after USG and club money" },
  ];
}

function WeekItem({ item }: { item: CalendarItem }) {
  const badge = itemBadge(item);
  return (
    <li className="border-b border-stone-200 py-4 last:border-b-0">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm font-medium text-stone-600"><time dateTime={item.day}>{formatDay(item.day)}</time></p>
        <StatusBadge state={badge.state} label={badge.label} />
      </div>
      <p>{item.title}</p>
      <p className="text-sm text-stone-600">{item.event_name}{item.unconfirmed ? " · unconfirmed date: check with usgfunds@usc.edu" : ""}</p>
      <Sources citations={[item.citation]} />
    </li>
  );
}

export function ThisWeek({ report }: { report: YearPlanReport }) {
  return (
    <Panel id="week-heading" title="This week" intro={`As of ${formatDay(report.as_of)}.`}>
      {report.this_week.length === 0 ? <p className="text-stone-700">Nothing dated is coming up.</p> : (
        <ol>
          {report.this_week.map((item) => <WeekItem key={`${item.day}-${item.event_key}-${item.rule_id}`} item={item} />)}
        </ol>
      )}
    </Panel>
  );
}

export function Problems({ report }: { report: YearPlanReport }) {
  const names = namesOf(report);
  return (
    <Panel id="problems-heading" title={`Problems found early (${report.problems.length})`}
      intro="Red first; yellow needs a person to confirm.">
      {report.problems.length === 0 ? <p className="text-stone-700">No problems found across the plan.</p> : (
        <ul>{report.problems.map((p, i) => <ProblemCard key={`${p.type}-${p.rule_id}-${i}`} p={p} names={names} />)}</ul>
      )}
      {report.questions.length ? (
        <div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm">
          <p className="font-medium">Questions for you</p>
          <ul className="list-disc pl-5">{report.questions.map((q) => <li key={q}>{q}</li>)}</ul>
        </div>
      ) : null}
    </Panel>
  );
}

export function PlanOverview({ report }: { report: YearPlanReport }) {
  return (
    <div className="space-y-10">
      <SummaryStats stats={planStats(report)} />
      <div className="grid gap-10 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <ThisWeek report={report} />
        <Problems report={report} />
      </div>
    </div>
  );
}

export function Strategy({ report }: { report: YearPlanReport }) {
  return (
    <Panel id="strategy-heading" title="Funding strategy: what to ask USG for, in this order">
      <details className="text-sm text-stone-700"><summary className="cursor-pointer font-medium text-cardinal">How the order is worked out</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5">{report.strategy.explanation.map((t) => <li key={t}>{t}</li>)}</ul></details>
      {report.strategy.steps.length === 0 ? <p className="mt-3 text-stone-700">No event is planned for USG funding.</p> : (
        <ol className="mt-4 space-y-3">
          {report.strategy.steps.map((s) => (
            <li key={s.key} className="rounded-xl border border-stone-200 bg-white p-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <p className="font-semibold"><span className="mr-2 tabular-nums text-stone-500">{s.order}.</span>{s.name}</p>
                <StatusBadge state={s.status === "apply" ? "info" : "yellow"} label={s.status === "apply" ? `Ask for ${dollars(s.planned_cents)}` : `Ask for ${dollars(s.planned_cents)} of ${dollars(s.requested_cents)}`} />
              </div>
              <p className="mt-1 text-sm">{s.note}</p>
              {s.apply_by ? <p className="mt-1 text-sm"><span className="font-medium">Apply by: </span>{deadlineText(s.apply_by)}</p> : null}
              <p className="mt-1 text-sm">
                <span className="font-medium">Fund: </span>
                {s.fund.fund_name ?? "Not chosen yet"}{s.fund.status === "unsure" ? " (needs a human look)" : ""}. {s.fund.explanation}
              </p>
              <Sources citations={[...(s.apply_by ? [s.apply_by.citation, s.apply_by.table_citation] : []), ...s.fund.citations]} />
            </li>
          ))}
        </ol>
      )}
      {report.strategy.not_planned.length ? (
        <div className="mt-5">
          <h3 className="font-semibold">Not in the funding plan</h3>
          <ul className="mt-2 space-y-2">
            {report.strategy.not_planned.map((n) => (
              <li key={n.key} className="rounded-xl border border-stone-200 bg-white p-3">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <p className="font-medium">{n.name} ({dollars(n.requested_cents)} requested)</p>
                  <StatusBadge state={n.severity} />
                </div>
                <p className="text-sm">{n.reason}</p>
                <Sources citations={[n.citation]} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </Panel>
  );
}

export function Budget({ report }: { report: YearPlanReport }) {
  const b = report.budget;
  return (
    <Panel id="budget-heading" title="Year budget">
      <dl className="grid grid-cols-1 gap-x-6 sm:grid-cols-2">
        {[
          ["Events cost in all", dollars(b.total_cost_cents)],
          ["Club money (on hand and expected)", dollars(b.funds_available_cents)],
          ["Gap before any USG money", dollars(b.gap_before_usg_cents)],
          ["Asked of USG in all", dollars(b.usg_requested_cents)],
          ["Over the yearly USG cap", b.usg_requested_over_yearly_cap_cents === null ? "Unknown: enter what USG already gave" : dollars(b.usg_requested_over_yearly_cap_cents)],
          ["USG money in the funding plan", dollars(b.usg_planned_cents)],
          ["Club money used", dollars(b.club_money_cents)],
          ["Still to find", dollars(b.shortfall_cents)],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3 border-b border-stone-200 py-2">
            <dt className="text-stone-700">{label}</dt>
            <dd className="font-semibold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
      <details className="mt-3 text-sm text-stone-700"><summary className="cursor-pointer font-medium text-cardinal">How the budget is worked out</summary>
        <ul className="mt-2 list-disc pl-5">{b.explanation.map((t) => <li key={t}>{t}</li>)}</ul></details>
      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[32rem] text-sm">
          <thead><tr><th scope="col" className="py-3 pr-3">Event</th><th scope="col" className="px-3 py-2 text-right">Cost</th><th scope="col" className="px-3 py-2 text-right">USG (planned)</th><th scope="col" className="px-3 py-2 text-right">Club money</th><th scope="col" className="px-3 py-2 text-right">Still to find</th></tr></thead>
          <tbody className="divide-y divide-stone-200">
            {b.rows.map((r) => (
              <tr key={r.key}>
                <th scope="row" className="px-3 py-2 text-left font-semibold">{r.name}</th>
                <td className="px-3 py-2 text-right tabular-nums">{dollars(r.cost_cents)}</td>
                <td className="px-3 py-2 text-right tabular-nums">{dollars(r.usg_planned_cents)}</td>
                <td className="px-3 py-2 text-right tabular-nums">{dollars(r.club_money_cents)}</td>
                <td className="px-3 py-2 text-right font-semibold tabular-nums">{dollars(r.shortfall_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Sources citations={[b.citation]} />
    </Panel>
  );
}

export function BudgetAndFunding({ report }: { report: YearPlanReport }) {
  return (
    <div className="grid gap-10 xl:grid-cols-2">
      <Budget report={report} />
      <Strategy report={report} />
    </div>
  );
}

export function YearCalendar({ report }: { report: YearPlanReport }) {
  const names = namesOf(report);
  const busy = new Set(report.crowded_weeks.map((w) => w.week_start));
  const months = new Map<string, CalendarItem[]>();
  for (const item of report.calendar) {
    const label = new Date(`${item.day}T00:00:00Z`).toLocaleDateString("en-US", { month: "long", year: "numeric", timeZone: "UTC" });
    months.set(label, [...(months.get(label) ?? []), item]);
  }
  return (
    <div className="grid gap-10 xl:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)]">
      <Panel id="calendar-heading" title="Year calendar" intro="Every event's deadlines, worked back from its date by the event packet's rules. Busy weeks have many deadlines at once. Pick a month.">
        <Tabs label="Months" tabs={[...months.entries()].map(([month, items]) => ({
          id: month.replace(/\s+/g, "-"),
          label: month,
          count: items.length,
          content: (
            <ul className="divide-y divide-stone-200 rounded-xl border border-stone-200 bg-white">
              {items.map((item, i) => {
                const badge = itemBadge(item);
                const crowded = busy.has(weekOf(item.day));
                return (
                  <li key={`${item.day}-${item.event_key}-${item.rule_id}-${i}`} className={`grid gap-1 p-3 sm:grid-cols-[9rem_1fr_auto] sm:items-start sm:gap-4 ${crowded ? "border-l-4 border-amber-500" : ""} ${item.kind === "event" ? "bg-cardinal-50" : ""}`}>
                    <p><time dateTime={item.day} className="font-semibold">{formatDay(item.day)}</time>{crowded ? <span className="block text-xs font-medium text-amber-900">Busy week</span> : null}</p>
                    <div className="min-w-0">
                      <p className={item.kind === "event" ? "font-semibold text-cardinal" : ""}>{item.title}</p>
                      {item.kind !== "event" ? <p className="text-sm text-stone-600">{item.event_name}</p> : null}
                      {item.citation ? <Sources citations={[item.citation]} /> : null}
                    </div>
                    <StatusBadge state={badge.state} label={badge.label} />
                  </li>
                );
              })}
            </ul>
          ),
        }))} />
      </Panel>
      <Panel title="Busy weeks" intro="Weeks with many things due at once.">
        {report.crowded_weeks.length ? (
          <ul className="space-y-2 text-sm">
            {report.crowded_weeks.map((w) => (
              <li key={w.week_start} className="rounded-xl border border-amber-200 bg-amber-50 p-3">
                <StatusBadge state="yellow" label="Busy week" />
                <p className="mt-1 font-semibold">{formatDay(w.week_start)} to {formatDay(w.week_end)}</p>
                <p>{w.count} things due, for {w.events.map((k) => names[k] ?? k).join(", ")}</p>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-stone-700">No crowded weeks.</p>}
      </Panel>
    </div>
  );
}

export function EventsPane({ report, onOpenPacket, onOpenMoney, onOpenGap }: {
  report: YearPlanReport;
  onOpenPacket: (key: string) => void;
  onOpenMoney: (key: string) => void;
  onOpenGap: (key: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <div className="space-y-3">
      <p className="text-sm text-stone-700">Open an event's full packet (every form, approval and deadline) or its money check.</p>
      <MasterDetail
        label="Events in the plan"
        items={report.events}
        selected={selected}
        onSelect={setSelected}
        itemKey={(e) => e.key}
        renderItem={(e) => (
          <div className="space-y-1">
            <p className="font-semibold">{e.name}</p>
            <p className="text-sm text-stone-600">{e.event_date ? formatDay(e.event_date) : "No date yet"}</p>
            <StatusBadge state={e.verdict} label={e.verdict_label} />
          </div>
        )}
        renderDetail={(e) => {
          const due = report.calendar.filter((c) => c.event_key === e.key && c.kind !== "event");
          return (
            <div className="space-y-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h3 className="text-xl font-semibold">{e.name}</h3>
                  <p className="text-sm text-stone-600">{e.event_date ? formatDay(e.event_date) : "No date yet"}{e.end_date ? ` to ${formatDay(e.end_date)}` : ""}</p>
                </div>
                <StatusBadge state={e.verdict} label={e.verdict_label} />
              </div>
              <p className="text-sm">{e.packet.obligations.filter((o) => !o.superseded_by).length} items in its packet; {e.packet.hard_blocks.length} blocked as described.</p>
              {e.usg_deadlines.map((d) => <p key={d.rule_id} className="text-sm"><span className="font-medium">{d.title}: </span>{deadlineText(d)}</p>)}
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => onOpenPacket(e.key)} className="rounded-md bg-cardinal px-3 py-2 text-sm font-medium text-white">Open event packet</button>
                <button type="button" onClick={() => onOpenMoney(e.key)} className="rounded-md border border-stone-400 px-3 py-2 text-sm">Open money check</button>
                {e.budget.shortfall_cents > 0 ? (
                  <button type="button" onClick={() => onOpenGap(e.key)} className="rounded-md border border-stone-400 px-3 py-2 text-sm">Close the {dollars(e.budget.shortfall_cents)} gap</button>
                ) : null}
              </div>
              {due.length ? (
                <div>
                  <h4 className="font-semibold">Its deadlines ({due.length})</h4>
                  <ul className="mt-2 divide-y divide-stone-200 border-y border-stone-200">
                    {due.map((item, i) => {
                      const badge = itemBadge(item);
                      return (
                        <li key={`${item.day}-${item.rule_id}-${i}`} className="py-3">
                          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                            <p><time dateTime={item.day} className="font-medium">{formatDay(item.day)}</time> · {item.title}</p>
                            <StatusBadge state={badge.state} label={badge.label} />
                          </div>
                          {item.citation ? <Sources citations={[item.citation]} /> : null}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ) : null}
            </div>
          );
        }}
      />
    </div>
  );
}
