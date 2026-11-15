// Shapes and calls for the recognition check. Keep in step with backend/app/services/recognition*.py.

import type { Citation, Verdict } from "../api/types";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/+$/, "");

export type ClauseState = "present" | "missing" | "weak" | "contradicts" | "needs_look" | "not_applicable";

export interface Conflict {
  rule_id: string;
  certain: boolean;
  message: string;
  fix: string | null;
  basis: string;
  reason: string;
  terms: string[];
  evidence: string | null;
  citation: Citation;
}

export interface ClauseResult {
  rule_id: string;
  label: string;
  title: string;
  article: string;
  state: ClauseState;
  state_label: string;
  verdict: Verdict | null;
  message: string;
  suggestion: string | null;
  template_text: string;
  document_text: string | null;
  missing_words: string[];
  added_words: string[];
  conflicts: Conflict[];
  citation: Citation;
}

export interface ReportNote {
  kind: string;
  verdict: Verdict | null;
  message: string;
  detail: string[];
  citation: Citation | null;
}

export interface ConstitutionReport {
  notice: string;
  readable: boolean;
  message: string;
  overall: Verdict | null;
  summary: Record<string, number>;
  notes: ReportNote[];
  clauses: ClauseResult[];
  document: { name?: string; kind_label?: string; pages?: number | null; fillable?: boolean | null };
  reader: { used?: boolean; message?: string };
}

export type ItemState = "done" | "to_do" | "check" | "info";

export interface ReadinessItem {
  id: string;
  label: string;
  state: ItemState;
  state_label: string;
  verdict: Verdict | null;
  message: string;
  fix: string | null;
  due: string | null;
  days_left: number | null;
  citation: Citation;
  also_cited: Citation[];
}

export interface ReadinessReport {
  notice: string;
  as_of: string;
  overall: Verdict;
  message: string;
  summary: Record<ItemState, number>;
  positions: string[];
  groups: { title: string; items: ReadinessItem[] }[];
  key_dates: { label: string; day: string; days_left: number; passed: boolean; message: string; citation: Citation }[];
}

export interface OfficerStatus {
  position: string;
  named: boolean;
  hazing_prevention: boolean;
  officer_learning_path: boolean;
  commitment_to_community: boolean;
}

export interface ReadinessInput {
  officers: OfficerStatus[];
  additional_members: number;
  advisor_named: boolean;
  advisor_accepted: boolean;
  advisor_training: boolean;
  advisor_commitment: boolean;
  constitution_ready: boolean;
  accountability_document: boolean;
  positions_accepted: boolean;
}

export type Outcome<T> = { ok: true; data: T } | { ok: false; error: string };

function errorText(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "message" in detail) return String((detail as { message: unknown }).message);
  }
  if (status === 413) return "The file is too large.";
  return `The server answered ${status}.`;
}

async function send<T>(path: string, init: RequestInit): Promise<Outcome<T>> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { ...init, headers: { Accept: "application/json", ...(init.headers ?? {}) } });
  } catch {
    return { ok: false, error: "Could not reach the Greenlight server." };
  }
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (response.ok && body !== null) return { ok: true, data: body as T };
  return { ok: false, error: errorText(response.status, body) };
}

export function checkConstitution(form: FormData): Promise<Outcome<ConstitutionReport>> {
  return send<ConstitutionReport>("/constitution/check", { method: "POST", body: form });
}

export function checkReadiness(input: ReadinessInput): Promise<Outcome<ReadinessReport>> {
  return send<ReadinessReport>("/recognition/readiness", {
    method: "POST",
    body: JSON.stringify(input),
    headers: { "Content-Type": "application/json" },
  });
}

export interface SampleConstitution {
  club_name: string;
  text: string;
  answers: Record<string, string>;
  note: string;
}

export async function getSampleConstitution(): Promise<
  { ok: true; data: SampleConstitution } | { ok: false; error: string }
> {
  try {
    const response = await fetch(`${BASE}/constitution/demo`, { headers: { Accept: "application/json" } });
    if (!response.ok) return { ok: false, error: "The sample constitution could not be loaded." };
    return { ok: true, data: (await response.json()) as SampleConstitution };
  } catch {
    return { ok: false, error: "Could not reach the Greenlight server." };
  }
}
