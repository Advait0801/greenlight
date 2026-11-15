import { useMemo, useState } from "react";

import type { Verdict } from "../api/types";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { SourceLink } from "../components/SourceLink";
import { StatusBadge, type BadgeState } from "../components/StatusBadge";
import { MasterDetail, SummaryStats } from "../components/ui";
import type { ClauseResult, ClauseState, ConstitutionReport } from "./recognitionApi";

const STATE_BADGE: Record<ClauseState, BadgeState> = {
  present: "green",
  missing: "red",
  weak: "red",
  contradicts: "red",
  needs_look: "yellow",
  not_applicable: "info",
};

const OVERALL_LABEL: Record<Verdict, string> = {
  red: "Needs fixing",
  yellow: "Needs a human look",
  green: "No problems found",
  office_decides: "The office decides",
};

type Filter = "problems" | "all";

export function ClauseBody({ result }: { result: ClauseResult }) {
  return (
<div className="space-y-3 text-sm">
      <p>{result.message}</p>
      {result.suggestion ? (
        <p>
          <span className="font-medium">Suggested fix: </span>
          {result.suggestion}
        </p>
      ) : null}
      {result.document_text && result.state !== "present" ? (
        <div>
          <p className="font-medium">Your document says</p>
          <p className="mt-1 whitespace-pre-wrap rounded bg-stone-100 px-3 py-2 text-stone-800">{result.document_text}</p>
        </div>
      ) : null}
      <div>
        <p className="font-medium">Template wording (blanks shown as ________)</p>
        <SourceLink citation={{ ...result.citation, source_text: result.template_text }} />
      </div>
      {result.conflicts.map((conflict) => (
        <div key={conflict.rule_id} className="rounded border border-stone-200 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-medium">{conflict.message}</p>
            <StatusBadge
              state={conflict.certain ? "red" : "yellow"}
              label={conflict.certain ? "Breaks the rule" : "Check against this rule"}
            />
          </div>
          {conflict.evidence ? <p className="mt-1 text-stone-700">Your words: “{conflict.evidence}”</p> : null}
          <SourceLink citation={conflict.citation} />
        </div>
      ))}
    </div>
  );
}

function ClauseCard({ result }: { result: ClauseResult }) {
  const open = result.state !== "present" && result.state !== "not_applicable";
  return (
    <li className="rounded-lg border border-stone-200 bg-white p-4">
      <details open={open}>
        <summary className="flex cursor-pointer list-none flex-wrap items-start justify-between gap-2">
          <span>
            <span className="font-medium">{result.label}</span>
            <span className="text-stone-600"> · {result.title}</span>
          </span>
          <StatusBadge state={STATE_BADGE[result.state]} label={result.state_label} />
        </summary>
        <div className="mt-3"><ClauseBody result={result} /></div>
      </details>
    </li>
  );
}

export function RecognitionReport({ report, view = "report" }: { report: ConstitutionReport; view?: "findings" | "report" }) {
  const [filter, setFilter] = useState<Filter>("problems");
  const [selected, setSelected] = useState<string | null>(null);
  const groups = useMemo(() => {
    const shown = report.clauses.filter(
      (clause) => filter === "all" || (clause.state !== "present" && clause.state !== "not_applicable"),
    );
    const byArticle = new Map<string, ClauseResult[]>();
    for (const clause of shown) byArticle.set(clause.article, [...(byArticle.get(clause.article) ?? []), clause]);
    return [...byArticle.entries()];
  }, [report, filter]);

  if (!report.readable) {
    return (
      <section aria-labelledby="report-heading" className="rounded-lg border border-red-300 bg-white p-5" role="alert">
        <h2 id="report-heading" className="flex flex-wrap items-center gap-3 text-xl font-semibold" tabIndex={-1}>
          Could not check this file <StatusBadge state="red" label="Not checked" />
        </h2>
        <p className="mt-2">{report.message}</p>
        <p className="mt-2 text-sm text-stone-600">Nothing was marked as present. Try another file or paste the text.</p>
      </section>
    );
  }

  const s = report.summary;
  const counts: [string, number, BadgeState][] = [
    ["Missing", s.missing ?? 0, "red"],
    ["Wording changed", s.weak ?? 0, "red"],
    ["Conflicts with a rule", s.contradicts ?? 0, "red"],
    ["Needs a human look", s.needs_look ?? 0, "yellow"],
    ["Present", s.present ?? 0, "green"],
    ["Not required for your club", s.not_applicable ?? 0, "info"],
  ];

  return (
    <section aria-labelledby="report-heading" className="space-y-5">
      <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <h2 id="report-heading" className="flex flex-wrap items-center gap-3 text-xl font-semibold" tabIndex={-1}>
          Constitution check
          {report.overall ? <StatusBadge state={report.overall} label={OVERALL_LABEL[report.overall]} /> : null}
        </h2>
        <p className="mt-2">{report.message}</p>
        {report.document.kind_label ? (
          <p className="mt-1 text-sm text-stone-600">
            Checked {report.document.kind_label}
            {report.document.pages ? `, ${report.document.pages} pages` : ""}, against {s.total ?? 0} clauses of the template.
          </p>
        ) : null}
        <div className="mt-4">
          <SummaryStats stats={counts.map(([label, count, state]) => ({ label, value: count, tone: state }))} />
        </div>
        {report.reader.message ? <p className="mt-3 text-sm text-stone-600">{report.reader.message}</p> : null}
      </div>

      <PrecheckNotice text={report.notice} />

      {report.notes.length > 0 ? (
        <ul className="space-y-3">
          {report.notes.map((note) => (
            <li key={note.kind} className="rounded-lg border border-stone-200 bg-white p-4 text-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p>{note.message}</p>
                <StatusBadge state={note.verdict ?? "info"} />
              </div>
              {note.detail.length > 0 ? (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-stone-700">
                  {note.detail.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              ) : null}
              {note.citation ? <SourceLink citation={note.citation} /> : null}
            </li>
          ))}
        </ul>
      ) : null}

      <fieldset className="flex flex-wrap gap-2 rounded-xl bg-white p-2 ring-1 ring-stone-200">
        <legend className="sr-only">Which clauses to show</legend>
        {(["problems", "all"] as const).map((value) => (
          <label key={value} className={`flex cursor-pointer items-center gap-2 rounded-lg px-3 py-1.5 text-sm ${filter === value ? "bg-cardinal-50 text-cardinal" : ""}`}>
            <input type="radio" name={`clause-filter-${view}`} checked={filter === value} onChange={() => setFilter(value)} />
            {value === "problems" ? "Only clauses that need attention" : "Every clause"}
          </label>
        ))}
      </fieldset>

      {groups.length === 0 ? <p className="text-stone-700">No clause needs attention.</p> : null}
      {view === "findings" ? (
        <MasterDetail
          label="Clauses"
          items={groups.flatMap(([, clauses]) => clauses)}
          selected={selected}
          onSelect={setSelected}
          itemKey={(c) => c.rule_id}
          renderItem={(c) => (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-600">{c.article}</p>
              <p className="font-medium">{c.label} <span className="font-normal text-stone-600">· {c.title}</span></p>
              <StatusBadge state={STATE_BADGE[c.state]} label={c.state_label} />
            </div>
          )}
          renderDetail={(c) => (
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-cardinal">{c.article}</p>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="font-display text-xl font-semibold">{c.label} · {c.title}</h3>
                <StatusBadge state={STATE_BADGE[c.state]} label={c.state_label} />
              </div>
              <ClauseBody result={c} />
            </div>
          )}
        />
      ) : groups.map(([article, clauses]) => (
        <section key={article} aria-label={article} className="space-y-3">
          <h3 className="text-lg font-semibold">{article}</h3>
          <ul className="space-y-3">
            {clauses.map((clause) => (
              <ClauseCard key={clause.rule_id} result={clause} />
            ))}
          </ul>
        </section>
      ))}
    </section>
  );
}
