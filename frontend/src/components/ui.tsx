import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

import type { BadgeState } from "./StatusBadge";

// Layout pieces shared by the pages. Display only: no data, wording or logic lives here.

export function PageHeader({ eyebrow, title, children, actions }: { eyebrow?: string; title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="relative overflow-hidden rounded-2xl bg-white px-5 py-6 shadow-[var(--shadow-card)] ring-1 ring-stone-200 sm:px-8 sm:py-8">
      <span aria-hidden="true" className="absolute inset-y-0 left-0 w-1.5 bg-gradient-to-b from-cardinal to-gold" />
      {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cardinal">{eyebrow}</p> : null}
      <h1 className="mt-1 font-display text-3xl font-semibold tracking-tight text-stone-950 sm:text-4xl">{title}</h1>
      {children ? <div className="mt-3 max-w-3xl space-y-2 text-stone-700">{children}</div> : null}
      {actions ? <div className="mt-5 flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  );
}

const TONE: Record<BadgeState, string> = {
  red: "border-red-200 bg-red-50 text-red-900",
  yellow: "border-amber-200 bg-amber-50 text-amber-950",
  green: "border-green-200 bg-green-50 text-green-900",
  office_decides: "border-sky-200 bg-sky-50 text-sky-950",
  info: "border-stone-200 bg-white text-stone-900",
};
const ICON: Record<BadgeState, string> = { red: "✕", yellow: "!", green: "✓", office_decides: "?", info: "i" };

export interface Stat {
  label: string;
  value: ReactNode;
  tone?: BadgeState;
  hint?: string;
}

// The verdict and counts at the top of a result. Each tile carries an icon and words, never colour alone.
export function SummaryStats({ stats }: { stats: Stat[] }) {
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {stats.map((s) => {
        const tone = s.tone ?? "info";
        return (
          <div key={s.label} className={`rounded-xl border px-4 py-3 ${TONE[tone]}`}>
            <dt className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide opacity-90">
              {s.tone && s.tone !== "info" ? <span aria-hidden="true">{ICON[tone]}</span> : null}
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

// WAI-ARIA tabs. Inactive panels stay in the page (hidden), so nothing is removed, only collapsed.
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
      <div className="z-10 -mx-1 sm:sticky sm:top-16 overflow-x-auto bg-[#f7f5f2]/95 px-1 pb-2 pt-1 backdrop-blur">
        <div role="tablist" aria-label={label} className="inline-flex min-w-full gap-1 rounded-xl bg-stone-200/70 p-1 sm:min-w-0">
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
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  selected ? "bg-white text-cardinal shadow-sm ring-1 ring-stone-200" : "text-stone-700 hover:bg-white/60 hover:text-stone-950"
                }`}
              >
                {t.label}
                {t.count !== undefined ? (
                  <span className={`ml-1.5 rounded-full px-1.5 py-0.5 text-xs tabular-nums ${selected ? "bg-cardinal text-white" : "bg-stone-300/80 text-stone-800"}`}>{t.count}</span>
                ) : null}
              </button>
            );
          })}
        </div>
      </div>
      {tabs.map((t) => (
        <div
          key={t.id}
          role="tabpanel"
          id={`${base}-panel-${t.id}`}
          aria-labelledby={`${base}-tab-${t.id}`}
          hidden={t.id !== active}
          tabIndex={0}
          className="pt-4 focus-visible:outline-offset-4"
        >
          {t.content}
        </div>
      ))}
    </div>
  );
}

// A visual step flow for multi-step pages: numbered, with the current and done steps stated in words.
export function Steps({ steps, current }: { steps: { label: string; href?: string }[]; current: number }) {
  return (
    <nav aria-label="Steps">
      <ol className="flex gap-2 overflow-x-auto pb-1">
        {steps.map((s, i) => {
          const state = i < current ? "done" : i === current ? "current" : "todo";
          const body = (
            <>
              <span
                aria-hidden="true"
                className={`grid h-7 w-7 flex-none place-items-center rounded-full text-sm font-bold ${
                  state === "done" ? "bg-cardinal text-white" : state === "current" ? "bg-gold text-stone-950 ring-2 ring-cardinal" : "bg-stone-200 text-stone-700"
                }`}
              >
                {state === "done" ? "✓" : i + 1}
              </span>
              <span className={`text-sm ${state === "current" ? "font-semibold text-stone-950" : "text-stone-700"}`}>{s.label}</span>
              <span className="sr-only">{state === "done" ? " (done)" : state === "current" ? " (current step)" : ""}</span>
            </>
          );
          return (
            <li key={s.label} className="flex flex-none items-center gap-2" aria-current={state === "current" ? "step" : undefined}>
              {s.href ? <a href={s.href} className="flex items-center gap-2 rounded-lg px-1 py-1 no-underline hover:bg-white">{body}</a> : <span className="flex items-center gap-2 px-1 py-1">{body}</span>}
              {i < steps.length - 1 ? <span aria-hidden="true" className="h-px w-6 flex-none bg-stone-300" /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

// A titled card section, collapsible when `collapsible` is set (open by default unless `closed`).
export function Panel({ id, title, children, intro, collapsible, closed, aside }: {
  id?: string; title: string; children: ReactNode; intro?: ReactNode; collapsible?: boolean; closed?: boolean; aside?: ReactNode;
}) {
  if (collapsible) {
    return (
      <details id={id} open={!closed} className="group rounded-2xl bg-white p-5 shadow-[var(--shadow-card)] ring-1 ring-stone-200 sm:p-6">
        <summary className="cursor-pointer select-none">
          <span className="font-display text-xl font-semibold text-stone-950">{title}</span>
          {aside ? <span className="ml-auto">{aside}</span> : null}
        </summary>
        {intro ? <div className="mt-2 text-sm text-stone-700">{intro}</div> : null}
        <div className="mt-4">{children}</div>
      </details>
    );
  }
  return (
    <section id={id} aria-labelledby={id ? `${id}-title` : undefined} className="rounded-2xl bg-white p-5 shadow-[var(--shadow-card)] ring-1 ring-stone-200 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 id={id ? `${id}-title` : undefined} className="font-display text-xl font-semibold text-stone-950">{title}</h2>
        {aside}
      </div>
      {intro ? <div className="mt-1 text-sm text-stone-700">{intro}</div> : null}
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

// A step-by-step flow: a clickable step indicator, one step on screen at a time, Back and Next at the foot.
export function Wizard({ steps, step, onStep, label }: { steps: WizardStep[]; step: number; onStep: (i: number) => void; label: string }) {
  const current = steps[step] ?? steps[0]!;
  const go = (i: number) => {
    onStep(i);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const next = steps[step + 1];
  const prev = steps[step - 1];
  return (
    <div className="space-y-5">
      <nav aria-label={label} className="rounded-2xl bg-white p-2 shadow-[var(--shadow-card)] ring-1 ring-stone-200">
        <ol className="flex gap-1 overflow-x-auto">
          {steps.map((s, i) => {
            const state = i === step ? "current" : i < step ? "done" : "todo";
            return (
              <li key={s.id} className="flex-1">
                <button
                  type="button"
                  onClick={() => go(i)}
                  aria-current={state === "current" ? "step" : undefined}
                  className={`flex w-full min-w-max items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition ${
                    state === "current" ? "bg-cardinal text-white shadow" : "text-stone-800 hover:bg-cardinal-50"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`grid h-7 w-7 flex-none place-items-center rounded-full text-xs font-bold ${
                      state === "current" ? "bg-gold text-stone-950" : state === "done" ? "bg-cardinal text-white" : "bg-stone-200 text-stone-700"
                    }`}
                  >
                    {state === "done" ? "✓" : i + 1}
                  </span>
                  <span className="font-semibold">{s.label}</span>
                  {s.count !== undefined ? (
                    <span className={`rounded-full px-1.5 text-xs tabular-nums ${state === "current" ? "bg-white/20" : "bg-stone-200"}`}>{s.count}</span>
                  ) : null}
                  <span className="sr-only">{state === "done" ? " (before this step)" : state === "current" ? " (current step)" : ""}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>
      <div>
        {current.locked ? (
          <div className="rounded-2xl border-2 border-dashed border-stone-300 bg-white/60 p-8 text-center text-stone-700">{current.locked}</div>
        ) : current.content}
      </div>
      <div className="flex items-center justify-between gap-3 border-t border-stone-200 pt-4">
        {prev ? (
          <button type="button" onClick={() => go(step - 1)} className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-semibold text-stone-800 hover:border-cardinal hover:bg-cardinal-50">
            ← Back: {prev.label}
          </button>
        ) : <span />}
        {next ? (
          <button type="button" onClick={() => go(step + 1)} className="rounded-lg bg-cardinal px-4 py-2 text-sm font-semibold text-white shadow hover:bg-cardinal-dark">
            Next: {next.label} →
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
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(16rem,22rem)_1fr]">
      <ul aria-label={label} className="space-y-2 lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:self-start lg:overflow-y-auto lg:pr-1">
        {items.map((t) => {
          const k = itemKey(t);
          const active = k === chosenKey;
          return (
            <li key={k}>
              <button
                type="button"
                onClick={() => onSelect(k)}
                aria-pressed={active}
                className={`w-full rounded-xl border p-3 text-left transition ${
                  active ? "border-cardinal bg-white shadow-[var(--shadow-lift)] ring-2 ring-gold" : "border-stone-200 bg-white hover:border-cardinal/50 hover:shadow-[var(--shadow-card)]"
                }`}
              >
                {renderItem(t, active)}
              </button>
            </li>
          );
        })}
      </ul>
      <div className="min-w-0 rounded-2xl bg-white p-5 shadow-[var(--shadow-card)] ring-1 ring-stone-200 sm:p-6">{renderDetail(chosen)}</div>
    </div>
  );
}
