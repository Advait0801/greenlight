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
import { Panel, SummaryStats } from "../components/ui";
import { STORAGE_KEY, fromRequest, loadSaved, toRequest } from "./YearPlan";
import { planStats } from "./YearPlanResults";

// The home dashboard. Everything on it comes from the same routes the tools use; no figure is worked out here.

const TOOLS: { to: string; title: string; text: string; icon: string }[] = [
  { to: "/recognition", title: "Recognition", text: "Check the constitution and see what is due for re-recognition.", icon: "✎" },
  { to: "/plan", title: "Year plan", text: "Every event's deadlines on one calendar, the budget and what to ask USG for.", icon: "▦" },
  { to: "/events/packet", title: "Events", text: "One event's forms, approvals and dated timeline, with sources.", icon: "✦" },
  { to: "/money/check", title: "Money check", text: "Check a budget against USG's funding rules before you apply.", icon: "$" },
  { to: "/money/gap", title: "Gap helper", text: "The ways USC allows to close a funding gap, and the ones it does not.", icon: "⇄" },
  { to: "/usg", title: "USG screen", text: "For USG reviewers: pre-checked applications and drafted reasons.", icon: "⚑" },
  { to: "/accuracy", title: "Accuracy", text: "Caught, missed and wrongly flagged on the test sets.", icon: "◎" },
  { to: "/handover", title: "Handover", text: "Pass the year on to next year's officers.", icon: "↻" },
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
  const upcoming = report ? report.calendar.filter((c) => c.kind !== "event" && c.day >= report.as_of).slice(0, 6) : [];
  const firstProblems = report ? [...report.problems].sort((a, b) => (a.severity === "red" ? -1 : 0) - (b.severity === "red" ? -1 : 0)).slice(0, 4) : [];
  const names = report ? Object.fromEntries(report.events.map((e) => [e.key, e.name])) : {};

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-3xl bg-cardinal px-6 py-8 text-white shadow-[var(--shadow-lift)] sm:px-10 sm:py-12">
        <div aria-hidden="true" className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-gold/25 blur-3xl" />
        <div aria-hidden="true" className="absolute -bottom-32 right-24 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
        <div className="relative grid gap-8 lg:grid-cols-[minmax(0,3fr)_minmax(16rem,2fr)] lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold">{club.trim() ? club : "Greenlight for USC clubs"}</p>
            <h1 className="mt-2 font-display text-3xl font-semibold leading-tight tracking-tight sm:text-5xl">
              Plan your club's year, and know every rule before USC tells you no.
            </h1>
            <p className="mt-4 max-w-2xl text-white/90">
              Greenlight checks event plans, budgets and constitutions against USC's published rules, and shows the rule text and
              source for every result.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              {report ? (
                <Link to="/plan" className="rounded-lg bg-gold px-5 py-2.5 font-semibold text-stone-950 shadow hover:bg-[#ffd633]">Open the year plan →</Link>
              ) : (
                <button type="button" onClick={loadDemo} className="rounded-lg bg-gold px-5 py-2.5 font-semibold text-stone-950 shadow hover:bg-[#ffd633]">Load the demo club</button>
              )}
              <Link to="/recognition" className="rounded-lg px-5 py-2.5 font-semibold text-white ring-1 ring-white/60 hover:bg-white/10">Check a constitution</Link>
            </div>
          </div>
          <ul className="grid grid-cols-3 gap-3 text-center lg:grid-cols-1 lg:text-left">
            {[
              ["AI reads", "documents and drafts text"],
              ["Code checks", "every date, sum and verdict"],
              ["A person approves", "nothing is sent for you"],
            ].map(([a, b]) => (
              <li key={a} className="rounded-2xl bg-white/10 px-3 py-3 ring-1 ring-white/20 lg:flex lg:items-baseline lg:gap-2 lg:px-4">
                <span className="block font-display text-lg font-semibold text-gold">{a}</span>
                <span className="block text-xs text-white/85 lg:text-sm">{b}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <PrecheckNotice {...(health ? { text: health.notice } : {})} />

      <div aria-live="polite">
        {plan.state === "loading" ? <p className="flex items-center gap-2 text-stone-700"><span aria-hidden="true" className="h-3 w-3 animate-pulse rounded-full bg-gold" />Working out the plan…</p> : null}
        {plan.state === "failed" ? <p role="alert" className="rounded-xl border border-red-300 bg-red-50 p-3 text-red-900">{plan.message}</p> : null}
      </div>

      {report ? (
        <>
          <SummaryStats stats={planStats(report)} />
          <div className="grid gap-5 xl:grid-cols-3">
            <Panel title="Next things to do" intro={`As of ${formatDay(report.as_of)}.`} aside={<Link to="/plan" className="text-sm font-semibold text-cardinal underline underline-offset-2">Year plan</Link>}>
              {report.this_week.length === 0 ? <p className="text-stone-700">Nothing dated is coming up.</p> : (
                <ol className="space-y-3">
                  {report.this_week.map((item, i) => (
                    <li key={`${item.day}-${item.rule_id}-${i}`} className="flex gap-3">
                      <span aria-hidden="true" className="grid h-7 w-7 flex-none place-items-center rounded-full bg-cardinal text-xs font-bold text-white">{i + 1}</span>
                      <div className="min-w-0">
                        <p className="font-semibold"><time dateTime={item.day}>{formatDay(item.day)}</time></p>
                        <p>{item.title}</p>
                        <p className="text-sm text-stone-600">{item.event_name}</p>
                        {item.citation ? <details className="mt-1"><summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Rule text and source</summary><SourceLink citation={item.citation} /></details> : null}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </Panel>
            <Panel title="Upcoming deadlines" aside={<Link to="/plan" className="text-sm font-semibold text-cardinal underline underline-offset-2">Calendar</Link>}>
              {upcoming.length === 0 ? <p className="text-stone-700">Nothing dated is coming up.</p> : (
                <ul className="divide-y divide-stone-200">
                  {upcoming.map((item, i) => (
                    <li key={`${item.day}-${item.rule_id}-${i}`} className="py-2.5">
                      <p className="text-sm font-semibold text-cardinal"><time dateTime={item.day}>{formatDay(item.day)}</time></p>
                      <p className="text-sm">{item.title}</p>
                      <p className="text-xs text-stone-600">{item.event_name}{item.unconfirmed ? " · from an unconfirmed copy of USG's deadline table" : ""}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
            <Panel title="Problems to fix first" aside={<Link to="/plan" className="text-sm font-semibold text-cardinal underline underline-offset-2">All {report.problems.length}</Link>}>
              {firstProblems.length === 0 ? <p className="text-stone-700">No problems found across the plan.</p> : (
                <ul className="space-y-3">
                  {firstProblems.map((p, i) => (
                    <li key={`${p.rule_id}-${i}`} className="rounded-xl border border-stone-200 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold">{p.events.map((k) => names[k] ?? k).join(", ")}</p>
                        <StatusBadge state={p.severity} label={p.severity_label} />
                      </div>
                      <p className="mt-1 text-sm">{p.note}</p>
                      {p.citation ? <details className="mt-1"><summary className="cursor-pointer text-sm text-cardinal underline underline-offset-2">Rule text and source</summary><SourceLink citation={p.citation} /></details> : null}
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
          <Panel title="Your events" aside={<Link to="/plan" className="text-sm font-semibold text-cardinal underline underline-offset-2">Edit the plan</Link>}>
            <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              {report.events.map((e) => (
                <li key={e.key} className="rounded-xl border border-stone-200 p-3">
                  <p className="font-semibold">{e.name}</p>
                  <p className="text-sm text-stone-600">{e.event_date ? formatDay(e.event_date) : "No date yet"}</p>
                  <p className="mt-1 text-sm tabular-nums">Still to find: {dollars(e.budget.shortfall_cents)}</p>
                  <div className="mt-2"><StatusBadge state={e.verdict} label={e.verdict_label} /></div>
                </li>
              ))}
            </ul>
          </Panel>
        </>
      ) : plan.state === "none" ? (
        <div className="rounded-2xl border-2 border-dashed border-stone-300 bg-white p-8 text-center">
          <p className="font-display text-xl font-semibold">No year plan in this browser yet</p>
          <p className="mt-1 text-stone-700">Load the demo club to see a full year, or start your own plan.</p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <button type="button" onClick={loadDemo} className="rounded-md bg-cardinal px-4 py-2 font-medium text-white">Load the demo club</button>
            <Link to="/plan" className="rounded-md border border-stone-400 bg-white px-4 py-2 font-medium hover:border-cardinal">Start a year plan</Link>
          </div>
        </div>
      ) : null}

      <section aria-labelledby="tools-heading" className="space-y-3">
        <h2 id="tools-heading" className="font-display text-xl font-semibold">Tools</h2>
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {TOOLS.map((t) => (
            <li key={t.to}>
              <Link to={t.to} className="group flex h-full gap-3 rounded-2xl bg-white p-4 shadow-[var(--shadow-card)] ring-1 ring-stone-200 transition hover:-translate-y-0.5 hover:shadow-[var(--shadow-lift)] hover:ring-cardinal/40">
                <span aria-hidden="true" className="grid h-10 w-10 flex-none place-items-center rounded-xl bg-cardinal-50 text-lg text-cardinal group-hover:bg-cardinal group-hover:text-gold">{t.icon}</span>
                <span>
                  <span className="block font-semibold text-stone-950">{t.title} <span aria-hidden="true" className="text-cardinal">→</span></span>
                  <span className="mt-0.5 block text-sm text-stone-600">{t.text}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      {health ? (
        <Link to="/status" className="flex flex-wrap items-center gap-3 rounded-2xl bg-white px-4 py-3 text-sm shadow-[var(--shadow-card)] ring-1 ring-stone-200 hover:ring-cardinal/40">
          <span className="font-semibold">System status</span>
          <StatusBadge state={health.rules.loaded ? "green" : "red"} label={health.rules.loaded ? `${health.rules.count} rules loaded` : "Rules did not load"} />
          <StatusBadge state={health.calendar.verified === "read" ? "green" : "yellow"} label={health.calendar.verified === "read" ? "Calendar confirmed" : "Calendar not yet confirmed"} />
          <StatusBadge state="yellow" label={`${health.rules.by_verification?.unverified ?? 0} rules not verified`} />
          <span className="ml-auto font-semibold text-cardinal">Details →</span>
        </Link>
      ) : null}
    </div>
  );
}
