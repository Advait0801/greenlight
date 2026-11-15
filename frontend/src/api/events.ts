// Event packet API: shapes from backend/app/schemas/events.py and backend/app/api/events.py.

import type { Citation, Verdict } from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/+$/, "");

export type VenueType = "venue_tes_meeting_room" | "venue_tes_large" | "venue_outdoor" | "venue_classroom" | "venue_off_campus";
export type ObligationStatus = "to_do" | "condition" | "blocked" | "office_decides" | "check_with_office";
export type InputField = "event_date" | "end_date" | "venue" | "headcount" | "attributes";

export const VENUE_LABELS: Record<VenueType, string> = {
  venue_tes_meeting_room: "Tutor Campus Center meeting room (Trojan Event Services)",
  venue_tes_large: "Large venue: Bovard Auditorium, Trojan Grand Ballroom, Tommy's Place or Traditions",
  venue_outdoor: "Outdoor campus space (quad, park, plaza)",
  venue_classroom: "Classroom",
  venue_off_campus: "Off campus",
};

export interface EventFacts {
  name: string | null;
  event_date: string | null;
  end_date: string | null;
  venue: VenueType | null;
  headcount: number | null;
  tent_area_sqft?: number | null;
  attributes: string[];
  possible_attributes: string[];
  needs_officer_input: InputField[];
}

export interface Finding {
  rule_id: string;
  verdict: Verdict;
  message: string;
  fix: string | null;
  citation: Citation;
}

export interface Fallback {
  kind: "move_date" | "change_format" | "other_funding";
  text: string;
  earliest_date: string | null;
}

export interface PacketObligation {
  rule_id: string;
  title: string;
  owner_office: string;
  status: ObligationStatus;
  status_label: string;
  due: string | null;
  due_note: string | null;
  violated: boolean;
  past_due: boolean;
  message: string;
  note: string | null;
  fix: string | null;
  finding: Finding | null;
  citation: Citation;
  link: string;
  triggered_by: string[];
  from_possible_attribute: boolean;
  fallbacks: Fallback[];
  superseded_by: string | null;
  contact_by: string | null;
  contact_by_citation: Citation | null;
}

export interface SourceConflict {
  rules: string[];
  applied: string | null;
  explanation: string;
  citations: Citation[];
}

export interface EventPacket {
  as_of: string;
  event: EventFacts;
  obligations: PacketObligation[];
  timeline: { day: string; rule_id: string; title: string; status: ObligationStatus; past_due: boolean }[];
  source_conflicts: SourceConflict[];
  hard_blocks: string[];
  questions: string[];
  fallbacks: Fallback[];
  counts: Record<ObligationStatus, number>;
  notice: string;
}

export interface ParseResult {
  facts: EventFacts;
  notes: string[];
  sentence_had_instructions: boolean;
}

export interface Detail {
  name: string;
  description: string;
}

export type Outcome<T> = { ok: true; data: T } | { ok: false; error: string };

function errorText(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (detail && typeof detail === "object" && "message" in detail) return String((detail as { message: unknown }).message);
    if (Array.isArray(detail)) return "Some of the details are not valid. Check the dates, the headcount and the venue.";
  }
  return status === 0 ? "Could not reach the Greenlight server." : `The server answered ${status}.`;
}

async function send(path: string, init: RequestInit): Promise<Response | null> {
  try {
    return await fetch(`${BASE}${path}`, init);
  } catch {
    return null;
  }
}

export async function postJson<T>(path: string, body: unknown): Promise<Outcome<T>> {
  const response = await send(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!response) return { ok: false, error: errorText(0, null) };
  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (response.ok && data !== null) return { ok: true, data: data as T };
  return { ok: false, error: errorText(response.status, data) };
}

export async function downloadIcs(event: EventFacts): Promise<Outcome<Blob>> {
  const response = await send("/events/packet.ics", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event }),
  });
  if (!response) return { ok: false, error: errorText(0, null) };
  if (!response.ok) return { ok: false, error: errorText(response.status, null) };
  return { ok: true, data: await response.blob() };
}

export async function getDetails(): Promise<Outcome<Detail[]>> {
  const response = await send("/events/vocabulary", { headers: { Accept: "application/json" } });
  if (!response || !response.ok) return { ok: false, error: errorText(response?.status ?? 0, null) };
  const data = (await response.json()) as { details: Detail[] };
  return { ok: true, data: data.details };
}
