import type { EventPacket } from "../api/events";
import { StatusBadge, type BadgeState } from "./StatusBadge";

export function formatDay(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  const value = new Date(Date.UTC(year ?? 1970, (month ?? 1) - 1, day ?? 1));
  return value.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
}

// The dated items of a packet in date order, with the event day marked. Dates come from the backend's deadline calculator.
export function EventTimeline({ packet }: { packet: EventPacket }) {
  const entries = [
    ...packet.timeline.map((entry) => ({ ...entry, kind: "deadline" as const })),
    ...(packet.event.event_date
      ? [{ day: packet.event.event_date, rule_id: "event", title: packet.event.name ?? "The event", status: "to_do" as const, past_due: false, kind: "event" as const }]
      : []),
  ].sort((a, b) => (a.day === b.day ? (a.kind === "event" ? 1 : -1) : a.day < b.day ? -1 : 1));

  if (entries.length === 0) {
    return <p className="text-stone-700">No dates yet. Give the event date to see the timeline.</p>;
  }
  return (
    <ol className="relative space-y-3 border-l-2 border-stone-300 pl-5">
      {entries.map((entry) => {
        const state: BadgeState = entry.past_due ? "red" : entry.status === "office_decides" ? "office_decides" : entry.status === "check_with_office" ? "yellow" : "info";
        const label = entry.kind === "event" ? "Event day" : entry.past_due ? "Passed" : undefined;
        return (
          <li key={`${entry.rule_id}-${entry.day}`} className="relative">
            <span aria-hidden="true" className={`absolute -left-[1.6rem] top-1.5 h-3 w-3 rounded-full ${entry.kind === "event" ? "bg-cardinal" : "bg-gold"}`} />
            <p className="text-sm font-semibold text-stone-700">
              <time dateTime={entry.day}>{formatDay(entry.day)}</time>
            </p>
            <p className="flex flex-wrap items-center gap-2">
              {entry.kind === "event" ? <span className="font-semibold">{entry.title}</span> : <a className="underline underline-offset-2" href={`#ob-${entry.rule_id}`}>{entry.title}</a>}
              {entry.kind === "event" ? <StatusBadge state="info" label="Event day" /> : <StatusBadge state={state} label={label ?? statusText(entry.status)} />}
            </p>
          </li>
        );
      })}
    </ol>
  );
}

export function statusText(status: string): string {
  return (
    { to_do: "To do", condition: "Rule to keep", blocked: "Blocked as described", office_decides: "The office decides", check_with_office: "Check with the office" } as Record<string, string>
  )[status] ?? status;
}
