import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

import type { BadgeState } from "./StatusBadge";

// Layout pieces shared by the pages. Display only: no data, rule or verdict wording lives here.
// Plain sections, hairline rules and whitespace; cards only for the dashboard's summary tiles.

export function PageHeader({ title, lede, children, actions }: {
  eyebrow?: string; title: string; lede?: ReactNode; children?: ReactNode; actions?: ReactNode;
}) {
  // The top bar already names the section, so the header is just the title, one line and the actions.
  return (
    <header className="flex flex-col gap-4 border-b border-stone-200 pb-6 lg:flex-row lg:items-end lg:justify-between">
      <div className="min-w-0">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-stone-950">{title}</h1>
        {lede ? <p className="mt-1 text-stone-600">{lede}</p> : null}
        {children ? (
          <details className="mt-1 text-stone-700">
            <summary className="cursor-pointer text-sm text-cardinal">About this page</summary>
            <div className="mt-2 space-y-2">{children}</div>
          </details>
        ) : null}
      </div>
      {actions ? <div className="flex flex-none flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}

const TONE_TILE: Record<BadgeState, string> = {
  red: "ring-red-200 bg-red-50 text-red-900",
  yellow: "ring-amber-200 bg-amber-50 text-amber-950",
  green: "ring-green-200 bg-green-50 text-green-900",
  office_decides: "ring-sky-200 bg-sky-50 text-sky-950",
  info: "ring-stone-200 bg-white text-stone-900",
};
const ICON: Record<BadgeState, string> = { red: "✕", yellow: "!", green: "✓", office_decides: "?", info: "" };

export interface Stat {
  label: string;
  value: ReactNode;
  tone?: BadgeState;
  hint?: string;
}

// The verdict and counts at the top of a result: a plain row of figures (tiles only on the dashboard).
// Each figure carries a word label and an icon, never colour alone.
const COLS: Record<number, string> = { 3: "lg:grid-cols-3", 4: "lg:grid-cols-4", 5: "lg:grid-cols-5", 6: "lg:grid-cols-3 2xl:grid-cols-6" };

export function SummaryStats({ stats }: { stats: Stat[]; tiles?: boolean }) {
  return (
    <dl className={`grid grid-cols-2 gap-3 sm:grid-cols-3 ${COLS[stats.length] ?? "lg:grid-cols-4"}`}>
      {stats.map((s) => {
        const tone = s.tone ?? "info";
        return (
          <div key={s.label} className={`rounded-xl px-4 py-3 ring-1 ring-inset ${TONE_TILE[tone]} ${tone === "info" ? "shadow-[var(--shadow-card)]" : ""}`}>
            <dt className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide opacity-90">
              {ICON[tone] ? <span aria-hidden="true">{ICON[tone]}</span> : null}
              {s.label}
            </dt>
            <dd className="mt-1 font-display text-2xl font-semibold tabular-nums">{s.value}</dd>
            {s.hint ? <dd className="mt-0.5 text-xs opacity-80">{s.hint}</dd> : null}
          </div>
        );
      })}
    </dl>
  );
}

export interface TabSpec {
  id: string;
  label: string;
  count?: number;
  content: ReactNode;
}

// WAI-ARIA tabs (underlined). Inactive panels stay in the page (hidden), so nothing is removed, only collapsed.
export function Tabs({ tabs, label, initial }: { tabs: TabSpec[]; label: string; initial?: string }) {
  const base = useId();
  const [active, setActive] = useState(initial ?? tabs[0]?.id ?? "");
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    let next = -1;
    if (e.key === "ArrowRight") next = (i + 1) % tabs.length;
    if (e.key === "ArrowLeft") next = (i - 1 + tabs.length) % tabs.length;
    if (e.key === "Home") next = 0;
    if (e.key === "End") next = tabs.length - 1;
    if (next < 0) return;
    e.preventDefault();
    setActive(tabs[next]!.id);
    refs.current[next]?.focus();
  };
  return (
    <div>
      <div role="tablist" aria-label={label} className="relative flex gap-6 overflow-x-auto border-b border-stone-200">
        {tabs.map((t, i) => {
          const selected = t.id === active;
          return (
            <button
              key={t.id}
              ref={(el) => { refs.current[i] = el; }}
              type="button"
              role="tab"
              id={`${base}-tab-${t.id}`}
              aria-selected={selected}
              aria-controls={`${base}-panel-${t.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(t.id)}
              onKeyDown={(e) => onKey(e, i)}
              className={`-mb-px whitespace-nowrap border-b-2 py-3 text-base font-medium ${
                selected ? "border-cardinal text-cardinal" : "border-transparent text-stone-600 hover:border-stone-300 hover:text-stone-900"
              }`}
            >
              {t.label}
              {t.count !== undefined ? <span className="ml-1.5 text-sm tabular-nums text-stone-500">{t.count}</span> : null}
            </button>
          );
        })}
      </div>
      {tabs.map((t) => (
        <div
          key={t.id}
          role="tabpanel"
          id={`${base}-panel-${t.id}`}
          aria-labelledby={`${base}-tab-${t.id}`}
          hidden={t.id !== active}
          tabIndex={0}
          className="pt-6"
        >
          {t.content}
        </div>
      ))}
    </div>
  );
}

// A titled section: heading over a hairline, no box. Collapsible when `collapsible` is set.
export function Panel({ id, title, children, intro, collapsible, closed, aside }: {
  id?: string; title: string; children: ReactNode; intro?: ReactNode; collapsible?: boolean; closed?: boolean; aside?: ReactNode;
}) {
  if (collapsible) {
    return (
      <details id={id} open={!closed} className="border-t border-stone-200 pt-4">
        <summary className="cursor-pointer select-none text-lg font-semibold text-stone-950">{title}</summary>
        {intro ? <p className="mt-1 text-sm text-stone-600">{intro}</p> : null}
        <div className="mt-4">{children}</div>
      </details>
    );
  }
  return (
    <section id={id} aria-labelledby={id ? `${id}-title` : undefined} className="min-w-0">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-stone-200 pb-2">
        <h2 id={id ? `${id}-title` : undefined} className="text-lg font-semibold text-stone-950">{title}</h2>
        {aside}
      </div>
      {intro ? <p className="mt-2 text-sm text-stone-600">{intro}</p> : null}
      <div className="mt-4">{children}</div>
    </section>
  );
}

export interface WizardStep {
  id: string;
  label: string;
  content: ReactNode;
  /** Shown instead of the step when it cannot be opened yet. */
  locked?: string;
  count?: number;
}

// A step-by-step flow: a numbered step bar, one step on screen at a time, Back and Next at the foot.
export function Wizard({ steps, step, onStep, label }: { steps: WizardStep[]; step: number; onStep: (i: number) => void; label: string }) {
  const current = steps[step] ?? steps[0]!;
  const bar = useRef<HTMLOListElement>(null);
  useEffect(() => {
    // Keep the current step visible when the step bar scrolls sideways (phones).
    const el = bar.current?.querySelector<HTMLElement>('[aria-current="step"]');
    const list = bar.current;
    if (el && list) list.scrollLeft = el.offsetLeft - list.clientWidth / 2 + el.clientWidth / 2;
  }, [step]);
  const content = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  useEffect(() => {
    // After a step change, move keyboard focus to the new step so it is not lost on the page body.
    if (first.current) {
      first.current = false;
      return;
    }
    content.current?.focus({ preventScroll: true });
  }, [step]);
  const go = (i: number) => {
    onStep(i);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const next = steps[step + 1];
  const prev = steps[step - 1];
  return (
    <div className="space-y-8">
      <nav aria-label={label}>
        <ol ref={bar} className="relative flex overflow-x-auto border-b border-stone-200">
          {steps.map((s, i) => {
            const state = i === step ? "current" : i < step ? "done" : "todo";
            return (
              <li key={s.id} className="flex-none">
                <button
                  type="button"
                  onClick={() => go(i)}
                  aria-current={state === "current" ? "step" : undefined}
                  className={`-mb-px flex items-center gap-2 border-b-2 px-4 py-3 text-base first:pl-0 ${
                    state === "current" ? "border-cardinal font-semibold text-stone-950" : "border-transparent text-stone-600 hover:text-stone-950"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`grid h-6 w-6 flex-none place-items-center rounded-full text-xs font-semibold ${
                      state === "current" ? "bg-cardinal text-white" : state === "done" ? "bg-stone-800 text-white" : "border border-stone-400 text-stone-600"
                    }`}
                  >
                    {state === "done" ? "✓" : i + 1}
                  </span>
                  {s.label}
                  {s.count !== undefined ? <span className="text-sm tabular-nums text-stone-500">{s.count}</span> : null}
                  <span className="sr-only">{state === "done" ? " (before this step)" : state === "current" ? " (current step)" : ""}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>
      <div ref={content} tabIndex={-1} aria-label={`Step ${step + 1}: ${current.label}`} className="outline-none">
        {current.locked ? <p className="py-12 text-center text-stone-600">{current.locked}</p> : current.content}
      </div>
      <div className="flex items-center justify-between gap-4 border-t border-stone-200 pt-6">
        {prev ? (
          <button type="button" onClick={() => go(step - 1)} className="rounded-md border border-stone-300 bg-white px-4 py-2 font-medium text-stone-800">
            ← {prev.label}
          </button>
        ) : <span />}
        {next ? (
          <button type="button" onClick={() => go(step + 1)} className="rounded-md bg-cardinal px-4 py-2 font-medium text-white">
            {next.label} →
          </button>
        ) : null}
      </div>
    </div>
  );
}

// Master–detail: a selectable list on the left, the chosen item's detail on the right (stacked on phones).
export function MasterDetail<T>({ items, selected, onSelect, itemKey, renderItem, renderDetail, label, empty }: {
  items: T[]; selected: string | null; onSelect: (key: string) => void; itemKey: (t: T) => string;
  renderItem: (t: T, active: boolean) => ReactNode; renderDetail: (t: T) => ReactNode; label: string; empty?: ReactNode;
}) {
  if (!items.length) return <>{empty ?? null}</>;
  const chosen = items.find((t) => itemKey(t) === selected) ?? items[0]!;
  const chosenKey = itemKey(chosen);
  const detail = useRef<HTMLDivElement>(null);
  const pick = (k: string) => {
    onSelect(k);
    // Stacked layout (phones): bring the detail into view.
    if (window.matchMedia("(max-width: 1023px)").matches) window.setTimeout(() => detail.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };
  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(15rem,20rem)_1fr]">
      <ul aria-label={label} className="divide-y divide-stone-200 border-y border-stone-200 lg:sticky lg:top-24 lg:max-h-[calc(100vh-8rem)] lg:self-start lg:overflow-y-auto">
        {items.map((t) => {
          const k = itemKey(t);
          const active = k === chosenKey;
          return (
            <li key={k}>
              <button
                type="button"
                onClick={() => pick(k)}
                aria-pressed={active}
                className={`w-full border-l-[3px] px-4 py-3 text-left ${active ? "border-cardinal bg-cardinal-50" : "border-transparent hover:bg-stone-100"}`}
              >
                {renderItem(t, active)}
              </button>
            </li>
          );
        })}
      </ul>
      <div ref={detail} className="min-w-0 scroll-mt-24 lg:border-l lg:border-stone-200 lg:pl-8">{renderDetail(chosen)}</div>
    </div>
  );
}
