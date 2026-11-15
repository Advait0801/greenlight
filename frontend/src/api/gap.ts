// Funding gap helper API: shapes from backend/app/services/gap_helper.py, gap_email.py and backend/app/api/gap.py.

import type { Citation } from "./types";
import { postJson, type Finding, type VenueType } from "./events";

export type OptionId =
  | "in_kind_sponsor" | "co_host" | "fundraiser" | "donations" | "ticket_sales" | "free_drawing" | "voluntary_dues" | "other_usc_funds";
export type EmailKind = "in_kind_sponsor" | "co_host";

export interface GapRequest {
  event_name: string;
  event_date: string | null;
  venue: VenueType | null;
  headcount: number | null;
  attributes: string[];
  shortfall_cents: number;
  asks_usg: boolean;
  note: string;
}

export interface OptionStep {
  rule_id: string;
  title: string;
  owner_office: string;
  due: string | null;
  due_note: string | null;
  status_label: string;
  past_due: boolean;
  citation: Citation;
}

export interface GapOption {
  id: OptionId;
  title: string;
  status: "allowed" | "check_first";
  status_label: string;
  message: string;
  citation: Citation;
  conditions: Citation[];
  steps: OptionStep[];
  lead_time: string;
  finding: Finding | null;
  can_draft_email: boolean;
}

export interface BannedOption {
  rule_id: string;
  title: string;
  why: string;
  instead: string | null;
  in_your_note: boolean;
  citation: Citation;
}

export interface GapReport {
  as_of: string;
  event_name: string;
  shortfall_cents: number;
  shortfall_text: string;
  options: GapOption[];
  not_allowed: BannedOption[];
  notes: string[];
  notice: string;
}

export interface EmailRequest {
  kind: EmailKind;
  club_name: string;
  recipient: string;
  event_name: string;
  event_date: string | null;
  description: string;
  ask: string;
}

export interface EmailDraft {
  subject: string;
  text: string;
  notes: string[];
  approved: boolean;
  notice: string;
}

export const gapOptions = (body: GapRequest) => postJson<GapReport>("/gap/options", body);
export const draftEmail = (body: EmailRequest) => postJson<EmailDraft>("/gap/email", body);
export const approveEmail = (subject: string, text: string) =>
  postJson<{ approved: boolean; message: string }>("/gap/email/approve", { subject, text });
