// Money check API: shapes from backend/app/schemas/money.py and backend/app/api/money.py.

import type { Citation, Verdict } from "./types";
import { postJson, type Finding, type Outcome, type PacketObligation, type VenueType } from "./events";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/+$/, "");

export type PurchaseChannel = "vendor_quote" | "online_cart" | "amazon";
export type FundId =
  | "usg-fund-professional-academic"
  | "usg-fund-philanthropy"
  | "usg-fund-social-recreation-startup"
  | "usg-fund-performing-visual-arts";

export interface BudgetLine {
  line: number;
  vendor: string;
  item: string;
  category: string | null;
  category_sure: boolean;
  quantity: number;
  unit_price_cents: number;
  amount_cents: number;
  nights: number | null;
  has_quote: boolean;
  purchase_channel: PurchaseChannel;
  has_cart_screenshot: boolean | null;
  has_wish_list_link: boolean | null;
  document: number | null;
}

export interface BudgetEvent {
  name: string;
  description: string;
  event_date: string | null;
  end_date: string | null;
  expected_attendance: number | null;
  venue: VenueType | null;
  ticketed: boolean | null;
  open_to_all_students: boolean | null;
  attributes: string[];
}

export interface ClubMoney {
  usg_received_this_year_cents: number | null;
  usg_funded_events_this_semester: number | null;
  first_registered: string | null;
}

export interface ReadLine {
  item: string;
  category: string | null;
  category_sure: boolean;
  quantity: number | null;
  unit_price_cents: number | null;
  amount_cents: number | null;
  nights: number | null;
  is_fee: boolean;
  unsure: string[];
  evidence: string | null;
}

export interface QuoteDocument {
  index: number;
  name: string;
  readable: boolean;
  vendor: string | null;
  vendor_sure: boolean;
  kind: string;
  currency_ok: boolean;
  currency_text: string | null;
  lines: ReadLine[];
  stated_total_cents: number | null;
  read_total_cents: number | null;
  contains_instructions: boolean;
  notes: string[];
}

export interface FundReading {
  fund: FundId | null;
  confidence: "high" | "medium" | "low";
  also_fits: FundId[];
  evidence: string | null;
  contains_instructions: boolean;
}

export interface MoneyCheckRequest {
  event: BudgetEvent;
  club: ClubMoney;
  attachments: string[];
  lines: BudgetLine[];
  documents: QuoteDocument[];
  fund: FundId | null;
  fund_reading: FundReading | null;
}

export type Reason = "rule" | "category_unclear" | "duplicate_line" | "totals_mismatch" | "cannot_compute" | "not_read";

export interface MoneyFinding {
  reason: Reason;
  finding: Finding;
}

export interface LineReport {
  line: number;
  vendor: string;
  item: string;
  category: string | null;
  category_label: string | null;
  amount_cents: number;
  verdict: Verdict;
  verdict_label: string;
  findings: MoneyFinding[];
  passed: Finding[];
  vendor_check: { status: string; listed_name: string | null; list_note: string | null; finding: Finding };
}

export interface MoneyReport {
  as_of: string;
  verdict: Verdict;
  verdict_label: string;
  lines: LineReport[];
  application: MoneyFinding[];
  application_passed: Finding[];
  dates: PacketObligation[];
  fund: {
    fund: FundId | null;
    fund_name: string | null;
    status: "officer_chose" | "matched" | "unsure";
    verdict: Verdict | null;
    candidates: FundId[];
    explanation: string;
    citations: Citation[];
  };
  totals: {
    total_cents: number;
    food_total_cents: number;
    food_per_person_cents: number | null;
    food_per_person_text: string | null;
    venue_personnel_cents: number;
    usg_year_total_cents: number | null;
    ineligible_cents: number;
  };
  documents: QuoteDocument[];
  counts: Record<string, number>;
  draft_allowed: boolean;
  draft_blocked_by: string[];
  questions: string[];
  notice: string;
}

export interface Named {
  name: string;
  description: string;
}

export interface MoneyVocabulary {
  categories: Named[];
  attachments: Named[];
  funds: { id: FundId; name: string; description: string }[];
  event_details: Named[];
}

export interface SuggestedLine extends Omit<BudgetLine, "line" | "quantity" | "unit_price_cents" | "amount_cents"> {
  quantity: number | null;
  unit_price_cents: number | null;
  amount_cents: number | null;
  unsure: string[];
}

export interface ReadResult {
  documents: QuoteDocument[];
  suggested_lines: SuggestedLine[];
  problems: { name: string; message: string }[];
}

export interface DraftResult {
  text: string;
  notes: string[];
  approved: boolean;
  notice: string;
}

export function dollars(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  return `${sign}$${Math.floor(abs / 100).toLocaleString("en-US")}.${String(abs % 100).padStart(2, "0")}`;
}

/** "1,234.5" -> 123450. Null for anything that is not a plain dollar amount. */
export function toCents(text: string): number | null {
  const cleaned = text.replace(/[$,\s]/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  const [whole, part = ""] = cleaned.split(".");
  return Number(whole) * 100 + Number(part.padEnd(2, "0"));
}

export async function getVocabulary(): Promise<Outcome<MoneyVocabulary>> {
  try {
    const response = await fetch(`${BASE}/money/vocabulary`, { headers: { Accept: "application/json" } });
    if (!response.ok) return { ok: false, error: `The server answered ${response.status}.` };
    return { ok: true, data: (await response.json()) as MoneyVocabulary };
  } catch {
    return { ok: false, error: "Could not reach the Greenlight server." };
  }
}

export async function readDocuments(files: File[], text: string): Promise<Outcome<ReadResult>> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  form.append("text", text);
  try {
    const response = await fetch(`${BASE}/money/read`, { method: "POST", body: form });
    const data: unknown = await response.json().catch(() => null);
    if (response.ok && data) return { ok: true, data: data as ReadResult };
    const detail = (data as { detail?: { message?: string } } | null)?.detail;
    return { ok: false, error: detail?.message ?? `The server answered ${response.status}.` };
  } catch {
    return { ok: false, error: "Could not reach the Greenlight server." };
  }
}

export const readFund = (name: string, description: string) =>
  postJson<{ reading: FundReading }>("/money/fund", { name, description });
export const checkBudget = (body: MoneyCheckRequest) => postJson<MoneyReport>("/money/check", body);
export const draftApplication = (check: MoneyCheckRequest, purpose: string) =>
  postJson<DraftResult>("/money/draft", { check, purpose });
export const approveDraft = (text: string, eventName: string) =>
  postJson<{ approved: boolean; message: string }>("/money/draft/approve", { text, event_name: eventName });
