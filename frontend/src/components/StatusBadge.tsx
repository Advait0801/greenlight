// A verdict is always shown with an icon and a text label, never by colour alone.

export type BadgeState = "green" | "yellow" | "red" | "office_decides" | "info";

const STYLES: Record<BadgeState, { label: string; icon: string; className: string }> = {
  green: { label: "Meets the rule", icon: "✓", className: "bg-green-50 text-green-900 ring-green-700" },
  yellow: { label: "Needs a human look", icon: "!", className: "bg-amber-50 text-amber-950 ring-amber-700" },
  red: { label: "Breaks the rule", icon: "✕", className: "bg-red-50 text-red-900 ring-red-700" },
  office_decides: { label: "The office decides", icon: "?", className: "bg-sky-50 text-sky-950 ring-sky-700" },
  info: { label: "Good to know", icon: "i", className: "bg-stone-100 text-stone-900 ring-stone-500" },
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
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-sm font-medium ring-1 ring-inset ${style.className}`}
    >
      <span aria-hidden="true" className="font-bold">
        {style.icon}
      </span>
      <span>{label ?? style.label}</span>
    </span>
  );
}
