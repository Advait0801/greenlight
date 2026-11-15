import type { ReactNode } from "react";

import { dollars } from "../api/money";
import type { CalendarItem, PlanProblem, TableDeadline, YearPlanReport } from "../api/plans";
import { formatDay } from "../components/EventTimeline";
import { SourceLink } from "../components/SourceLink";
import { StatusBadge, type BadgeState } from "../components/StatusBadge";

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
  if (item.past_due) return { state: item.unconfirmed ? "yellow" : "red", label: "Passed" };
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
      <summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Rule text and source</summary>
      {shown.map((c) => <SourceLink key={c.rule_id} citation={c} />)}
    </details>
  );
}

function ProblemCard({ p, names }: { p: PlanProblem; names: Record<string, string> }) {
  return (
    <li className="rounded-md border border-stone-300 bg-white p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <p className="font-semibold">{p.events.map((k) => names[k] ?? k).join(", ")}</p>
        <StatusBadge state={p.severity} label={p.severity_label} />
      </div>
      <p className="mt-2">{p.note}</p>
      {p.fix ? <p className="mt-2 text-sm"><span className="font-medium">What to do: </span>{p.fix}</p> : null}
      {p.citation ? <Sources citations={[p.citation, ...p.also_cites]} /> : <p className="mt-2 text-xs text-stone-600">From your own plan, not a USC rule.</p>}
    </li>
  );
}

function deadlineText(d: TableDeadline): string {
  const table = d.table_date
    ? `USG's table (Greenlight's unconfirmed copy) says ${formatDay(d.table_date)}`
    : d.table_status === "not_in_table" ? "USG's table has no row for this week" : "USG's table lists no deadline for this week";
  return `${table}; counted in calendar weeks it is ${formatDay(d.latest_possible)} at the latest.`;
}

export function PlanResults({ report, onOpenPacket, onOpenMoney }: {
  report: YearPlanReport;
  onOpenPacket: (key: string) => void;
  onOpenMoney: (key: string) => void;
}) {
  const names = Object.fromEntries(report.events.map((e) => [e.key, e.name]));
  const busy = new Set(report.crowded_weeks.map((w) => w.week_start));
  const weekOf = (iso: string) => {
    const [y, m, d] = iso.split("-").map(Number);
    const day = new Date(Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1));
    day.setUTCDate(day.getUTCDate() - ((day.getUTCDay() + 6) % 7));
    return day.toISOString().slice(0, 10);
  };
  const months = new Map<string, CalendarItem[]>();
  for (const item of report.calendar) {
    const label = new Date(`${item.day}T00:00:00Z`).toLocaleDateString("en-US", { month: "long", year: "numeric", timeZone: "UTC" });
    months.set(label, [...(months.get(label) ?? []), item]);
  }
  const b = report.budget;

  return (
    <div className="space-y-10">
      <Section id="week-heading" title="This week: the next three things to do" intro={`As of ${formatDay(report.as_of)}.`}>
        {report.this_week.length === 0 ? <p className="text-stone-700">Nothing dated is coming up.</p> : (
          <ol className="space-y-2">
            {report.this_week.map((item) => {
              const badge = itemBadge(item);
              return (
                <li key={`${item.day}-${item.event_key}-${item.rule_id}`} className="rounded-md border border-stone-300 bg-white p-3">
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                    <p className="font-semibold"><time dateTime={item.day}>{formatDay(item.day)}</time></p>
                    <StatusBadge state={badge.state} label={badge.label} />
                  </div>
                  <p>{item.title}</p>
                  <p className="text-sm text-stone-600">{item.event_name}{item.unconfirmed ? " · date from an unconfirmed copy of USG's deadline table; confirm with usgfunds@usc.edu" : ""}</p>
                  <Sources citations={[item.citation]} />
                </li>
              );
            })}
          </ol>
        )}
      </Section>

      <Section id="problems-heading" title={`Problems found early (${report.problems.length})`}
        intro="Each problem shows the rule behind it. Fix the red ones first; yellow ones need a person to confirm.">
        {report.problems.length === 0 ? <p className="text-stone-700">No problems found across the plan.</p> : (
          <ul className="space-y-3">{report.problems.map((p, i) => <ProblemCard key={`${p.type}-${p.rule_id}-${i}`} p={p} names={names} />)}</ul>
        )}
        {report.questions.length ? (
          <div className="rounded-md border border-amber-700 bg-amber-50 p-3 text-sm">
            <p className="font-medium">Questions for you</p>
            <ul className="list-disc pl-5">{report.questions.map((q) => <li key={q}>{q}</li>)}</ul>
          </div>
        ) : null}
      </Section>

      <Section id="strategy-heading" title="Funding strategy: what to ask USG for, in this order">
        <ul className="list-disc space-y-1 pl-5 text-sm text-stone-700">{report.strategy.explanation.map((t) => <li key={t}>{t}</li>)}</ul>
        {report.strategy.steps.length === 0 ? <p className="text-stone-700">No event is planned for USG funding.</p> : (
          <ol className="space-y-3">
            {report.strategy.steps.map((s) => (
              <li key={s.key} className="rounded-md border border-stone-300 bg-white p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <p className="font-semibold">{s.order}. {s.name}</p>
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
          <div>
            <h3 className="font-semibold">Not in the funding plan</h3>
            <ul className="mt-2 space-y-2">
              {report.strategy.not_planned.map((n) => (
                <li key={n.key} className="rounded-md border border-stone-300 bg-white p-3">
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
      </Section>

      <Section id="budget-heading" title="Year budget">
        <dl className="grid grid-cols-1 gap-2 rounded-md border border-stone-300 bg-white p-4 sm:grid-cols-2">
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
            <div key={label} className="flex justify-between gap-3 border-b border-stone-200 py-1">
              <dt className="text-stone-700">{label}</dt>
              <dd className="font-semibold tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
        <ul className="list-disc pl-5 text-sm text-stone-700">{b.explanation.map((t) => <li key={t}>{t}</li>)}</ul>
        <ul className="space-y-2">
          {b.rows.map((r) => (
            <li key={r.key} className="rounded-md border border-stone-300 bg-white p-3 text-sm">
              <p className="font-semibold">{r.name}: {dollars(r.cost_cents)}</p>
              <p>USG (planned) {dollars(r.usg_planned_cents)} + club money {dollars(r.club_money_cents)} + still to find {dollars(r.shortfall_cents)}</p>
            </li>
          ))}
        </ul>
        <Sources citations={[b.citation]} />
      </Section>

      <Section id="calendar-heading" title="Year calendar" intro="Every event's deadlines, worked back from its date by the event packet's rules. Busy weeks have many deadlines at once.">
        {report.crowded_weeks.length ? (
          <ul className="space-y-1 text-sm">
            {report.crowded_weeks.map((w) => (
              <li key={w.week_start}><StatusBadge state="yellow" label="Busy week" /> {formatDay(w.week_start)} to {formatDay(w.week_end)}: {w.count} things due, for {w.events.map((k) => names[k] ?? k).join(", ")}</li>
            ))}
          </ul>
        ) : null}
        {[...months.entries()].map(([month, items]) => (
          <div key={month}>
            <h3 className="mt-4 font-semibold">{month}</h3>
            <ul className="mt-1 divide-y divide-stone-200 rounded-md border border-stone-300 bg-white">
              {items.map((item, i) => {
                const badge = itemBadge(item);
                const crowded = busy.has(weekOf(item.day));
                return (
                  <li key={`${item.day}-${item.event_key}-${item.rule_id}-${i}`} className={`p-3 ${crowded ? "border-l-4 border-amber-600" : ""} ${item.kind === "event" ? "bg-stone-50" : ""}`}>
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                      <p><time dateTime={item.day} className="font-medium">{formatDay(item.day)}</time>{crowded ? <span className="ml-2 text-xs text-amber-900">(busy week)</span> : null}</p>
                      <StatusBadge state={badge.state} label={badge.label} />
                    </div>
                    <p className={item.kind === "event" ? "font-semibold" : ""}>{item.title}</p>
                    {item.kind !== "event" ? <p className="text-sm text-stone-600">{item.event_name}</p> : null}
                    {item.citation ? <Sources citations={[item.citation]} /> : null}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </Section>

      <Section id="events-heading" title="Each event" intro="Open an event's full packet (every form, approval and deadline) or its money check.">
        <ul className="space-y-3">
          {report.events.map((e) => (
            <li key={e.key} className="rounded-md border border-stone-300 bg-white p-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="font-semibold">{e.name}</p>
                  <p className="text-sm text-stone-600">{e.event_date ? formatDay(e.event_date) : "No date yet"}{e.end_date ? ` to ${formatDay(e.end_date)}` : ""}</p>
                </div>
                <StatusBadge state={e.verdict} label={e.verdict_label} />
              </div>
              <p className="mt-1 text-sm">{e.packet.obligations.filter((o) => !o.superseded_by).length} items in its packet; {e.packet.hard_blocks.length} blocked as described.</p>
              {e.usg_deadlines.map((d) => <p key={d.rule_id} className="mt-1 text-sm"><span className="font-medium">{d.title}: </span>{deadlineText(d)}</p>)}
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" onClick={() => onOpenPacket(e.key)} className="rounded-md bg-cardinal px-3 py-2 text-sm font-medium text-white">Open event packet</button>
                <button type="button" onClick={() => onOpenMoney(e.key)} className="rounded-md border border-stone-400 px-3 py-2 text-sm">Open money check</button>
              </div>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
