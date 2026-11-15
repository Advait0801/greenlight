// Year plan API: shapes from backend/app/schemas/plans.py and backend/app/api/plans.py.

import { postJson, type EventFacts, type EventPacket, type Finding, type ObligationStatus, type Outcome, type VenueType } from "./events";
import type { FundId } from "./money";
import type { Citation, Verdict } from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/+$/, "");

export interface PlanEvent {
  key: string;
  name: string;
  event_date: string | null;
  end_date: string | null;
  venue: VenueType | null;
  headcount: number | null;
  attributes: string[];
  possible_attributes: string[];
  estimated_cost_cents: number;
  usg_request_cents: number;
  fund: FundId | null;
}

export interface YearPlanRequest {
  club_name: string;
  mission: string;
  level: "undergraduate" | "graduate" | null;
  money_on_hand_cents: number;
  expected_income_cents: number;
  usg_received_this_year_cents: number | null;
  unavailable_dates: string[];
  events: PlanEvent[];
}

export interface PlanProblem {
  type: string;
  rule_id: string | null;
  severity: Verdict;
  severity_label: string;
  events: string[];
  note: string;
  fix: string | null;
  citation: Citation | null;
  finding: Finding | null;
  also_cites: Citation[];
}

export interface TableDeadline {
  rule_id: string;
  title: string;
  column: "6_week" | "9_week";
  weeks: number;
  latest_possible: string;
  latest_possible_in: string;
  table_status: "date" | "no_deadline" | "not_applicable" | "not_in_table";
  table_date: string | null;
  table_row_to_confirm: boolean;
  before_semester: boolean;
  passed_per_table: boolean;
  citation: Citation;
  table_citation: Citation;
}

export interface EventBudget {
  key: string;
  name: string;
  cost_cents: number;
  usg_requested_cents: number;
  usg_planned_cents: number;
  club_money_cents: number;
  shortfall_cents: number;
}

export interface BudgetSummary {
  total_cost_cents: number;
  funds_available_cents: number;
  gap_before_usg_cents: number;
  usg_requested_cents: number;
  usg_requested_over_yearly_cap_cents: number | null;
  yearly_cap_cents: number;
  usg_planned_cents: number;
  club_money_cents: number;
  shortfall_cents: number;
  unallocated_cents: number;
  rows: EventBudget[];
  explanation: string[];
  citation: Citation;
}

export interface PlanFund {
  fund: FundId | null;
  fund_name: string | null;
  status: "officer_chose" | "matched" | "unsure";
  verdict: Verdict | null;
  candidates: FundId[];
  explanation: string;
  citations: Citation[];
}

export interface FundingStep {
  order: number;
  key: string;
  name: string;
  term: string | null;
  requested_cents: number;
  planned_cents: number;
  status: "apply" | "apply_partly";
  fund: PlanFund;
  apply_by: TableDeadline | null;
  note: string;
}

export interface NotPlanned {
  key: string;
  name: string;
  requested_cents: number;
  reason: string;
  severity: Verdict;
  citation: Citation | null;
}

export interface FundingStrategy {
  steps: FundingStep[];
  not_planned: NotPlanned[];
  semester_cap: number;
  yearly_cap_cents: number;
  explanation: string[];
  citations: Citation[];
}

export interface CalendarItem {
  day: string;
  kind: "event" | "due" | "contact_by" | "usg_table";
  event_key: string;
  event_name: string;
  rule_id: string | null;
  title: string;
  status: ObligationStatus | null;
  status_label: string;
  past_due: boolean;
  unconfirmed: boolean;
  citation: Citation | null;
}

export interface CrowdedWeek {
  week_start: string;
  week_end: string;
  count: number;
  events: string[];
}

export interface PlanEventResult {
  key: string;
  name: string;
  event_date: string | null;
  end_date: string | null;
  term: string | null;
  asks_usg: boolean;
  verdict: Verdict;
  verdict_label: string;
  packet: EventPacket;
  usg_deadlines: TableDeadline[];
  budget: EventBudget;
}

export interface YearPlanReport {
  as_of: string;
  club_name: string;
  events: PlanEventResult[];
  calendar: CalendarItem[];
  crowded_weeks: CrowdedWeek[];
  budget: BudgetSummary;
  strategy: FundingStrategy;
  problems: PlanProblem[];
  this_week: CalendarItem[];
  questions: string[];
  counts: Record<string, number>;
  notice: string;
}

export interface ReadRow {
  line: number;
  text: string;
  facts: EventFacts | null;
  notes: string[];
  error: string | null;
  had_instructions: boolean;
}

export const computePlan = (plan: YearPlanRequest) => postJson<YearPlanReport>("/plans/plan", plan);
export const readEvents = (text: string) => postJson<{ rows: ReadRow[] }>("/plans/read-events", { text });

export async function getDemoPlan(): Promise<Outcome<YearPlanRequest>> {
  try {
    const response = await fetch(`${BASE}/plans/demo`, { headers: { Accept: "application/json" } });
    if (!response.ok) return { ok: false, error: `The server answered ${response.status}.` };
    return { ok: true, data: (await response.json()) as YearPlanRequest };
  } catch {
    return { ok: false, error: "Could not reach the Greenlight server." };
  }
}

export async function downloadPlanIcs(plan: YearPlanRequest): Promise<Outcome<Blob>> {
  try {
    const response = await fetch(`${BASE}/plans/calendar.ics`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(plan),
    });
    if (!response.ok) return { ok: false, error: `The server answered ${response.status}.` };
    return { ok: true, data: await response.blob() };
  } catch {
    return { ok: false, error: "Could not reach the Greenlight server." };
  }
}
