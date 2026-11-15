import { useEffect, useState } from "react";

import { getJson } from "../api/client";
import type { Health, Rule, RuleList } from "../api/types";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { PageHeader } from "../components/ui";
import { SourceLink } from "../components/SourceLink";
import { StatusBadge, type BadgeState } from "../components/StatusBadge";

type Load<T> = { state: "loading" } | { state: "ready"; data: T } | { state: "failed"; message: string; data: T | null };

const DOMAIN_LABELS: Record<string, string> = {
  funding: "Undergraduate Student Government (USG) funding",
  events: "Event approvals",
  outside_money: "Money from outside USG",
  recognition: "Club recognition",
};

function StatusRow({ name, state, label, detail }: { name: string; state: BadgeState; label: string; detail?: string }) {
  return (
    <li className="flex flex-col gap-1 border-b border-stone-200 py-3 last:border-b-0 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p className="font-medium">{name}</p>
        {detail ? <p className="text-sm text-stone-600">{detail}</p> : null}
      </div>
      <StatusBadge state={state} label={label} />
    </li>
  );
}

export function Home() {
  const [health, setHealth] = useState<Load<Health>>({ state: "loading" });
  const [rules, setRules] = useState<Load<RuleList>>({ state: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getJson<Health>("/health", controller.signal)
      .then((result) =>
        setHealth(result.ok ? { state: "ready", data: result.data } : { state: "failed", message: result.error, data: result.data }),
      )
      .catch(() => undefined);
    getJson<RuleList>("/rules", controller.signal)
      .then((result) =>
        setRules(result.ok ? { state: "ready", data: result.data } : { state: "failed", message: result.error, data: null }),
      )
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  const body = health.state === "ready" ? health.data : health.state === "failed" ? health.data : null;
  const unverified: Rule[] = rules.state === "ready" ? rules.data.rules.filter((rule) => rule.verified !== "read") : [];

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Trust" title="System status"
        lede="Whether the rules and calendar loaded, and what still needs a person to confirm.">
        <p>
          Greenlight checks event plans, budgets and constitutions against USC's published rules, and shows the rule text and
          source for every result. This page shows whether the rule table and calendar loaded.
        </p>
      </PageHeader>
      <PrecheckNotice {...(body ? { text: body.notice } : {})} />

      <section aria-labelledby="status-heading" className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <h2 id="status-heading" className="text-xl font-semibold">
          System status
        </h2>
        <div aria-live="polite">
          {health.state === "loading" ? <p className="mt-3 text-stone-600">Checking the server…</p> : null}
          {health.state === "failed" && !body ? (
            <ul className="mt-2">
              <StatusRow name="Server" state="red" label="Not reachable" detail={health.message} />
            </ul>
          ) : null}
          {body ? (
            <ul className="mt-2">
              <StatusRow
                name="Server"
                state={body.status === "ok" ? "green" : "red"}
                label={body.status === "ok" ? "Running" : "Something did not load"}
              />
              <StatusRow
                name="Rule table"
                state={body.rules.loaded ? "green" : "red"}
                label={body.rules.loaded ? `${body.rules.count} rules loaded` : "Did not load"}
                detail={
                  body.rules.loaded
                    ? Object.entries(body.rules.by_domain ?? {})
                        .map(([domain, count]) => `${DOMAIN_LABELS[domain] ?? domain}: ${count}`)
                        .join(" · ")
                    : body.rules.problems.slice(0, 3).join(" ")
                }
              />
              {body.rules.loaded ? (
                <StatusRow
                  name="Rules waiting for a person to confirm them"
                  state="yellow"
                  label={`${body.rules.by_verification?.unverified ?? 0} not verified`}
                  detail={`${body.rules.shown_yellow_until_verified ?? 0} rules are shown as "needs a human look" until these are confirmed.`}
                />
              ) : null}
              <StatusRow
                name="Academic calendar"
                state={!body.calendar.loaded ? "red" : body.calendar.verified === "read" ? "green" : "yellow"}
                label={!body.calendar.loaded ? "Did not load" : body.calendar.verified === "read" ? "Confirmed" : "Not yet confirmed"}
                detail={body.calendar.loaded ? (body.calendar.terms ?? []).join(" · ") : body.calendar.problems.join(" ")}
              />
              <StatusRow
                name="AI reading"
                state="info"
                label={body.ai_mode === "live" ? "Live" : body.ai_mode === "record" ? "Live (saving responses)" : "Saved responses"}
                detail="The AI only reads documents and drafts text. Every date, sum and verdict comes from code."
              />
            </ul>
          ) : null}
        </div>
      </section>

      {unverified.length > 0 ? (
        <section aria-labelledby="unverified-heading" className="space-y-4">
          <h2 id="unverified-heading" className="text-xl font-semibold">
            Open questions for USC offices
          </h2>
          <ul className="grid gap-4 xl:grid-cols-2">
            {unverified.map((rule) => (
              <li key={rule.id} className="rounded-lg border border-stone-200 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-medium">{rule.title}</h3>
                  <StatusBadge state={rule.display_severity} />
                </div>
                <p className="mt-1 text-sm text-stone-700">{rule.message}</p>
                {rule.verification_note ? (
                  <p className="mt-1 text-sm text-stone-600">
                    <span className="font-medium">Why it needs a check: </span>
                    {rule.verification_note}
                  </p>
                ) : null}
                <SourceLink citation={rule.citation} />
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
