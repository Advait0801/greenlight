import { useEffect, useState } from "react";

import { SourceLink } from "../components/SourceLink";
import { StatusBadge, type BadgeState } from "../components/StatusBadge";
import { checkReadiness, type ItemState, type OfficerStatus, type ReadinessInput, type ReadinessReport } from "./recognitionApi";

const POSITIONS = ["president", "vice president", "secretary", "treasurer", "programming chair"];
const ITEM_BADGE: Record<ItemState, BadgeState> = { done: "green", to_do: "red", check: "yellow", info: "info" };

type OfficerKey = Exclude<keyof OfficerStatus, "position">;
const OFFICER_BOXES: [OfficerKey, string][] = [
  ["named", "Named on the application"],
  ["hazing_prevention", "Hazing Prevention 101 certificate"],
  ["officer_learning_path", "Officer Learning Path certificate"],
  ["commitment_to_community", "Signed Commitment to Community"],
];
type FlagKey = Exclude<keyof ReadinessInput, "officers" | "additional_members">;
const OTHER_BOXES: [FlagKey, string][] = [
  ["advisor_named", "We have a full-time faculty or staff advisor"],
  ["advisor_accepted", "Advisor accepted the position on EngageSC"],
  ["advisor_training", "Advisor sent the RSO Advisor Training certificate"],
  ["advisor_commitment", "Advisor sent the Commitment to Community form"],
  ["constitution_ready", "Constitution is on this year's fillable template"],
  ["accountability_document", "Accountability Document is done"],
  ["positions_accepted", "Everyone accepted their position in EngageSC"],
];

const STORAGE_KEY = "greenlight.recognition.readiness";

function blank(): ReadinessInput {
  return {
    officers: POSITIONS.map((position) => ({
      position,
      named: false,
      hazing_prevention: false,
      officer_learning_path: false,
      commitment_to_community: false,
    })),
    additional_members: 0,
    advisor_named: false,
    advisor_accepted: false,
    advisor_training: false,
    advisor_commitment: false,
    constitution_ready: false,
    accountability_document: false,
    positions_accepted: false,
  };
}

function load(): ReadinessInput {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved) return { ...blank(), ...(JSON.parse(saved) as Partial<ReadinessInput>) };
  } catch {
    // A blocked or corrupt store just means starting from empty boxes.
  }
  return blank();
}

function title(text: string): string {
  return text.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function RecognitionReadiness() {
  const [input, setInput] = useState<ReadinessInput>(load);
  const [report, setReport] = useState<ReadinessReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(input));
    } catch {
      // Not saving the ticks is fine; they are only a convenience on this device.
    }
    let current = true;
    checkReadiness(input).then((outcome) => {
      if (!current) return;
      if (outcome.ok) {
        setReport(outcome.data);
        setError(null);
      } else setError(outcome.error);
    });
    return () => {
      current = false;
    };
  }, [input]);

  const setOfficer = (index: number, key: OfficerKey, value: boolean) =>
    setInput((old) => ({ ...old, officers: old.officers.map((o, i) => (i === index ? { ...o, [key]: value } : o)) }));

  return (
    <section aria-labelledby="readiness-heading" className="space-y-5">
      <div>
        <h2 id="readiness-heading" className="text-2xl font-semibold">
          Application readiness
        </h2>
        <p className="mt-1 text-stone-700">
          Tick what is done. Greenlight cannot see EngageSC, so your ticks are your own record. They are saved only in this browser.
        </p>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] xl:items-start">
        <div className="space-y-5">
      <fieldset className="rounded-lg border border-stone-200 bg-white p-5">
        <legend className="px-1 font-semibold">Officers</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          {input.officers.map((officer, index) => (
            <fieldset key={officer.position} className="rounded border border-stone-200 p-3">
              <legend className="px-1 font-medium">{title(officer.position)}</legend>
              {OFFICER_BOXES.map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 py-0.5 text-sm">
                  <input type="checkbox" checked={officer[key]} onChange={(e) => setOfficer(index, key, e.target.checked)} />
                  {label}
                </label>
              ))}
            </fieldset>
          ))}
        </div>
        <label className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          Other student members besides the officers
          <input
            type="number"
            min={0}
            max={100000}
            inputMode="numeric"
            className="w-24 rounded border border-stone-400 px-2 py-1"
            value={input.additional_members}
            onChange={(e) => {
              const value = Math.max(0, Math.min(100000, Math.trunc(Number(e.target.value) || 0)));
              setInput((old) => ({ ...old, additional_members: value }));
            }}
          />
        </label>
      </fieldset>

      <fieldset className="rounded-lg border border-stone-200 bg-white p-5">
        <legend className="px-1 font-semibold">Advisor and documents</legend>
        {OTHER_BOXES.map(([key, label]) => (
          <label key={key} className="flex items-center gap-2 py-0.5 text-sm">
            <input type="checkbox" checked={input[key]} onChange={(e) => setInput((old) => ({ ...old, [key]: e.target.checked }))} />
            {label}
          </label>
        ))}
      </fieldset>

        </div>
        <div className="space-y-5">
      {report ? (
        <div className="rounded-lg border border-stone-200 bg-white p-5" aria-live="polite">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-medium">{report.message}</p>
            <StatusBadge state={report.overall} label={report.overall === "green" ? "Ready" : report.overall === "red" ? "Not ready" : "Needs a human look"} />
          </div>
          <h3 className="mt-4 font-semibold">Key dates</h3>
          <ul className="mt-2 space-y-3">
            {report.key_dates.map((key) => (
              <li key={key.label} className="text-sm">
                <p>
                  <span className="font-medium">{key.label}:</span> {key.message}
                </p>
                <SourceLink citation={key.citation} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {error ? (
        <p role="alert" className="rounded border border-red-300 bg-white px-4 py-3">
          {error}
        </p>
      ) : null}

      {report
        ? report.groups.map((group) => (
            <section key={group.title} aria-label={`${group.title} checklist`} className="space-y-2">
              <h3 className="text-lg font-semibold">{group.title}</h3>
              <ul className="space-y-2">
                {group.items.map((item) => (
                  <li key={item.id} className="rounded-lg border border-stone-200 bg-white p-4 text-sm">
                    <details open={item.state === "check"}>
                      <summary className="flex cursor-pointer list-none flex-wrap items-start justify-between gap-2">
                        <span className="font-medium">
                          {item.label}
                          {item.days_left !== null && item.state === "to_do" ? (
                            <span className="font-normal text-stone-600">
                              {" "}
                              · due {item.due}
                              {item.days_left >= 0 ? ` (${item.days_left} days left)` : " (passed)"}
                            </span>
                          ) : null}
                        </span>
                        <StatusBadge state={ITEM_BADGE[item.state]} label={item.state_label} />
                      </summary>
                      <p className="mt-2">{item.message}</p>
                      {item.fix ? (
                        <p className="mt-1">
                          <span className="font-medium">To do: </span>
                          {item.fix}
                        </p>
                      ) : null}
                      <SourceLink citation={item.citation} />
                      {item.also_cited.map((citation) => (
                        <SourceLink key={citation.rule_id} citation={citation} />
                      ))}
                    </details>
                  </li>
                ))}
              </ul>
            </section>
          ))
        : null}
        </div>
      </div>
    </section>
  );
}
