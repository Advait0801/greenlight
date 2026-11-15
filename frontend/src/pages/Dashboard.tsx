import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getJson } from "../api/client";
import { dollars } from "../api/money";
import { computePlan, getDemoPlan, type YearPlanReport } from "../api/plans";
import type { Health } from "../api/types";
import { formatDay } from "../components/EventTimeline";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { SourceLink } from "../components/SourceLink";
import { StatusBadge } from "../components/StatusBadge";
import { Icon } from "../components/Icon";
import { Panel, SummaryStats } from "../components/ui";
import { STORAGE_KEY, fromRequest, loadSaved, toRequest } from "./YearPlan";
import { planStats } from "./YearPlanResults";

// The home dashboard. Everything on it comes from the same routes the tools use; no figure is worked out here.

const TOOLS: { to: string; title: string; text: string; icon: string }[] = [
  { to: "/recognition", title: "Recognition", text: "Check the constitution", icon: "document" },
  { to: "/plan", title: "Year plan", text: "Calendar, budget and USG asks", icon: "calendar" },
  { to: "/events/packet", title: "Events", text: "One event's forms and deadlines", icon: "event" },
  { to: "/money/check", title: "Money check", text: "A budget against USG's rules", icon: "money" },
  { to: "/money/gap", title: "Gap helper", text: "Close a funding gap", icon: "gap" },
  { to: "/usg", title: "USG screen", text: "For USG reviewers", icon: "flag" },
  { to: "/accuracy", title: "Accuracy", text: "How often it is right", icon: "accuracy" },
  { to: "/handover", title: "Handover", text: "Pass the year on", icon: "handover" },
];

type PlanState = { state: "none" } | { state: "loading" } | { state: "ready"; report: YearPlanReport } | { state: "failed"; message: string };

export function Dashboard() {
  const [club, setClub] = useState(() => loadSaved().club_name);
  const [plan, setPlan] = useState<PlanState>({ state: "loading" });
  const [health, setHealth] = useState<Health | null>(null);

  async function refresh() {
    const saved = loadSaved();
    setClub(saved.club_name);
    const { body } = toRequest(saved);
    if (!body || body.events.length === 0) {
      setPlan({ state: "none" });
      return;
    }
    setPlan({ state: "loading" });
    const result = await computePlan(body);
    setPlan(result.ok ? { state: "ready", report: result.data } : { state: "failed", message: result.error });
  }

  useEffect(() => {
    void refresh();
    const controller = new AbortController();
    getJson<Health>("/health", controller.signal).then((r) => setHealth(r.data ?? null)).catch(() => undefined);
    return () => controller.abort();
  }, []);

  async function loadDemo() {
    setPlan({ state: "loading" });
    const result = await getDemoPlan();
    if (!result.ok) {
      setPlan({ state: "failed", message: result.error });
      return;
    }
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(fromRequest(result.data)));
    } catch {
      // Not saved in this browser; the dashboard still shows the demo below.
    }
    const computed = await computePlan(result.data);
    setClub(result.data.club_name);
    setPlan(computed.ok ? { state: "ready", report: computed.data } : { state: "failed", message: computed.error });
  }

  const report = plan.state === "ready" ? plan.report : null;
  const upcoming = report ? report.calendar.filter((c) => c.kind !== "event" && c.day >= report.as_of).slice(0, 5) : [];
  const firstProblems = report ? [...report.problems].sort((a, b) => (a.severity === "red" ? -1 : 0) - (b.severity === "red" ? -1 : 0)).slice(0, 5) : [];
  const names = report ? Object.fromEntries(report.events.map((e) => [e.key, e.name])) : {};

  return (
    <div className="space-y-10">
      <header className="flex flex-col gap-4 border-b border-stone-200 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-cardinal">{club.trim() ? club : "Greenlight for USC clubs"}</p>
          <h1 className="mt-1 max-w-3xl font-display text-3xl font-semibold tracking-tight text-stone-950 sm:text-4xl">
            Plan your club's year, and know every rule before USC tells you no.
          </h1>
          <details className="mt-2 text-stone-700">
            <summary className="cursor-pointer text-sm font-medium text-cardinal">How it works</summary>
            <p className="mt-2">
              Greenlight checks event plans, budgets and constitutions against USC's published rules, and shows the rule text and
              source for every result. The AI reads documents and drafts text; code works out every date, sum and verdict; a person
              approves every draft. Nothing is sent for you.
            </p>
          </details>
        </div>
        <div className="flex flex-wrap gap-2">
          {report ? (
            <Link to="/plan" className="rounded-md bg-cardinal px-4 py-2 font-medium text-white hover:bg-cardinal-dark">Open the year plan</Link>
          ) : (
            <button type="button" onClick={loadDemo} className="rounded-md bg-cardinal px-4 py-2 font-medium text-white">Load the demo club</button>
          )}
          <Link to="/recognition" className="rounded-md border border-stone-300 px-4 py-2 font-medium text-stone-800 hover:border-cardinal">Check a constitution</Link>
        </div>
      </header>

      <PrecheckNotice {...(health ? { text: health.notice } : {})} />

      <div aria-live="polite">
        {plan.state === "loading" ? <p className="flex items-center gap-2 text-stone-700"><span aria-hidden="true" className="h-3 w-3 animate-pulse rounded-full bg-gold" />Working out the plan…</p> : null}
        {plan.state === "failed" ? <p role="alert" className="rounded-xl border border-red-300 bg-red-50 p-3 text-red-900">{plan.message}</p> : null}
      </div>

      {report ? (
        <>
          <SummaryStats stats={planStats(report)} />
          <div className="grid gap-12 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
            <section aria-labelledby="coming-heading">
              <div className="flex items-baseline justify-between border-b border-stone-200 pb-2">
                <h2 id="coming-heading" className="text-lg font-semibold">Coming up</h2>
                <Link to="/plan" className="text-sm text-cardinal hover:underline">Full calendar</Link>
              </div>
              {upcoming.length === 0 ? <p className="py-6 text-stone-600">Nothing dated is coming up.</p> : (
                <ul className="divide-y divide-stone-200">
                  {upcoming.map((item, i) => (
                    <li key={`${item.day}-${item.rule_id}-${i}`} className="grid grid-cols-[8.5rem_1fr] gap-4 py-3">
                      <time dateTime={item.day} className="whitespace-nowrap text-sm font-medium text-stone-900">{formatDay(item.day)}</time>
                      <div className="min-w-0">
                        {item.citation ? (
                          <details>
                            <summary className="cursor-pointer">{item.title}</summary>
                            <SourceLink citation={item.citation} />
                          </details>
                        ) : <p>{item.title}</p>}
                        <p className="text-sm text-stone-600">{item.event_name}{item.unconfirmed ? " · unconfirmed date" : ""}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section aria-labelledby="problems-dash-heading">
              <div className="flex items-baseline justify-between border-b border-stone-200 pb-2">
                <h2 id="problems-dash-heading" className="text-lg font-semibold">Fix first</h2>
                <Link to="/plan" className="text-sm text-cardinal hover:underline">All {report.problems.length} problems</Link>
              </div>
              {firstProblems.length === 0 ? <p className="py-6 text-stone-600">No problems found across the plan.</p> : (
                <ul className="divide-y divide-stone-200">
                  {firstProblems.map((p, i) => (
                    <li key={`${p.rule_id}-${i}`} className="py-3">
                      <details>
                        <summary className="flex cursor-pointer items-center justify-between gap-3">
                          <span className="min-w-0 flex-1 truncate text-left">{p.events.length > 2 ? `${p.events.length} events` : p.events.map((k) => names[k] ?? k).join(", ")}</span>
                          <StatusBadge state={p.severity} label={p.severity_label} />
                        </summary>
                        <p className="mt-2 text-sm">{p.note}</p>
                        {p.citation ? <SourceLink citation={p.citation} /> : null}
                      </details>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
          <Panel title="Your events" aside={<Link to="/plan" className="text-sm font-medium text-cardinal underline underline-offset-2">Edit the plan</Link>}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[36rem] text-left">
                <caption className="sr-only">Events in the year plan</caption>
                <thead><tr className="border-b border-stone-200 text-sm text-stone-600"><th scope="col" className="py-3 pr-4 font-medium">Event</th><th scope="col" className="py-3 pr-4 font-medium">Date</th><th scope="col" className="py-3 pr-4 text-right font-medium">Still to find</th><th scope="col" className="py-3 font-medium">Status</th></tr></thead>
                <tbody className="divide-y divide-stone-200">
                  {report.events.map((e) => (
                    <tr key={e.key}>
                      <th scope="row" className="py-3 pr-4 font-medium">{e.name}</th>
                      <td className="py-3 pr-4 text-stone-700">{e.event_date ? formatDay(e.event_date) : "No date yet"}</td>
                      <td className="py-3 pr-4 text-right tabular-nums">{dollars(e.budget.shortfall_cents)}</td>
                      <td className="py-3"><StatusBadge state={e.verdict} label={e.verdict_label} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      ) : plan.state === "none" ? (
        <div className="border-y border-stone-200 py-12 text-center">
          <p className="text-lg font-semibold">No year plan in this browser yet</p>
          <p className="mt-1 text-stone-700">Load the demo club to see a full year, or start your own plan.</p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <button type="button" onClick={loadDemo} className="rounded-md bg-cardinal px-4 py-2 font-medium text-white">Load the demo club</button>
            <Link to="/plan" className="rounded-md border border-stone-400 bg-white px-4 py-2 font-medium hover:border-cardinal">Start a year plan</Link>
          </div>
        </div>
      ) : null}

      <section aria-labelledby="tools-heading">
        <h2 id="tools-heading" className="border-b border-stone-200 pb-2 text-lg font-semibold">Tools</h2>
        <ul className="grid sm:grid-cols-2 xl:grid-cols-4">
          {TOOLS.map((t) => (
            <li key={t.to} className="border-b border-stone-200">
              <Link to={t.to} className="group flex items-center gap-3 py-4 pr-4 hover:text-cardinal">
                <Icon name={t.icon} className="h-5 w-5 flex-none text-cardinal" />
                <span>
                  <span className="block font-medium text-stone-950 group-hover:text-cardinal">{t.title}</span>
                  <span className="block text-sm text-stone-600">{t.text}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      {health ? (
        <Link to="/status" className="flex flex-wrap items-center gap-3 text-sm hover:text-cardinal">
          <span className="font-semibold">System status</span>
          <StatusBadge state={health.rules.loaded ? "green" : "red"} label={health.rules.loaded ? `${health.rules.count} rules loaded` : "Rules did not load"} />
          <StatusBadge state={health.calendar.verified === "read" ? "green" : "yellow"} label={health.calendar.verified === "read" ? "Calendar confirmed" : "Calendar not yet confirmed"} />
          <StatusBadge state="yellow" label={`${health.rules.by_verification?.unverified ?? 0} rules not verified`} />
          <span className="font-medium text-cardinal underline underline-offset-2">Details</span>
        </Link>
      ) : null}
    </div>
  );
}
