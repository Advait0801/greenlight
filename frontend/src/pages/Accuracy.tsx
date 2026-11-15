import { useEffect, useState } from "react";

import { getJson } from "../api/client";
import { PrecheckNotice } from "../components/PrecheckNotice";
import { PageHeader } from "../components/ui";

interface SetResult {
  set: string;
  cases: number;
  status: string;
  caught?: number;
  missed?: number;
  wrongly_flagged?: number;
  notes?: string;
  about: string;
}

interface AccuracyReport {
  sets: SetResult[];
  method: string;
  limits: string;
}

const SET_LABELS: Record<string, string> = {
  events: "Event approvals",
  budgets: "Money check (USG funding)",
  constitutions: "Recognition check (constitutions)",
  year_plans: "Year plan",
};

export function Accuracy() {
  const [report, setReport] = useState<AccuracyReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getJson<AccuracyReport>("/accuracy", controller.signal)
      .then((result) => (result.ok ? setReport(result.data) : setError(result.error)))
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Trust" title="How accurate is Greenlight?">
        <p>
          Measured on test sets with known answers. <strong>Caught</strong>: problems and obligations Greenlight found.{" "}
          <strong>Missed</strong>: ones it did not find. <strong>Wrongly flagged</strong>: problems it reported that are not
          there.
        </p>
        <PrecheckNotice />
      </PageHeader>

      {error ? (
        <p role="alert" className="rounded border border-red-300 px-3 py-2 text-red-900">
          {error}
        </p>
      ) : null}
      {!report && !error ? <p role="status">Loading…</p> : null}

      {report ? (
        <>
          <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white shadow-sm">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <caption className="sr-only">Results on each test set</caption>
              <thead className="border-b border-stone-200 bg-stone-50">
                <tr>
                  <th scope="col" className="px-3 py-2">Test set</th>
                  <th scope="col" className="px-3 py-2 text-right">Cases</th>
                  <th scope="col" className="px-3 py-2 text-right">Caught</th>
                  <th scope="col" className="px-3 py-2 text-right">Missed</th>
                  <th scope="col" className="px-3 py-2 text-right">Wrongly flagged</th>
                </tr>
              </thead>
              <tbody>
                {report.sets.map((row) => (
                  <tr key={row.set} className="border-b border-stone-100 align-top last:border-b-0">
                    <th scope="row" className="px-3 py-2 font-medium">
                      {SET_LABELS[row.set] ?? row.set}
                      <span className="block font-normal text-stone-600">{row.about}</span>
                      {row.notes ? <span className="mt-1 block text-xs font-normal text-stone-600">{row.notes}</span> : null}
                    </th>
                    <td className="px-3 py-2 text-right">{row.cases}</td>
                    <td className="px-3 py-2 text-right">{row.caught ?? "not measured"}</td>
                    <td className="px-3 py-2 text-right">{row.missed ?? "not measured"}</td>
                    <td className="px-3 py-2 text-right">{row.wrongly_flagged ?? "not measured"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <section aria-labelledby="method-heading" className="max-w-2xl space-y-2 text-stone-700">
            <h2 id="method-heading" className="text-xl font-semibold text-stone-900">
              How this was measured
            </h2>
            <p>{report.method}</p>
            <p>{report.limits}</p>
          </section>
        </>
      ) : null}
    </div>
  );
}
