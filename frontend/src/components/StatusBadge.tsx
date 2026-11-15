// A verdict is always shown with an icon and a text label, never by colour alone.

export type BadgeState = "green" | "yellow" | "red" | "office_decides" | "info";

const STYLES: Record<BadgeState, { label: string; icon: string; className: string }> = {
  green: { label: "Meets the rule", icon: "✓", className: "bg-green-100 text-green-900 ring-green-600/40 [--dot:var(--color-green-700)]" },
  yellow: { label: "Needs a human look", icon: "!", className: "bg-amber-100 text-amber-950 ring-amber-600/50 [--dot:var(--color-amber-600)]" },
  red: { label: "Breaks the rule", icon: "✕", className: "bg-red-100 text-red-900 ring-red-600/40 [--dot:var(--color-red-700)]" },
  office_decides: { label: "The office decides", icon: "?", className: "bg-sky-100 text-sky-950 ring-sky-600/40 [--dot:var(--color-sky-700)]" },
  info: { label: "Good to know", icon: "i", className: "bg-stone-100 text-stone-800 ring-stone-400/60 [--dot:var(--color-stone-500)]" },
};

interface Props {
  state: BadgeState;
  /** Overrides the default label, e.g. "Loaded" instead of "Meets the rule". */
  label?: string;
}

export function StatusBadge({ state, label }: Props) {
  const style = STYLES[state];
  return (
    <span
      className={`inline-flex flex-none items-center gap-1.5 rounded-full py-0.5 pl-1 pr-2.5 text-sm font-semibold ring-1 ring-inset ${style.className}`}
    >
      <span aria-hidden="true" className="grid h-5 w-5 place-items-center rounded-full bg-[var(--dot)] text-[0.7rem] font-bold leading-none text-white">
        {style.icon}
      </span>
      <span>{label ?? style.label}</span>
    </span>
  );
}
