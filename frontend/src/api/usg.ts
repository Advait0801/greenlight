// USG screen API: shapes from backend/app/services/usg_screen.py and backend/app/api/usg.py.

import type { Citation, Verdict } from "./types";
import { postJson, type Outcome } from "./events";
import type { MoneyCheckRequest } from "./money";

const BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/+$/, "");

export interface Reason {
  rule_id: string;
  verdict: Verdict;
  verdict_label: string;
  where: string;
  message: string;
  fix: string | null;
  citation: Citation;
}

export interface QueueItem {
  id: number;
  reference: string;
  club_name: string;
  event_name: string;
  event_date: string | null;
  sent_at: string;
  verdict: Verdict;
  verdict_label: string;
  total_text: string;
  counts: Record<string, number>;
  denial_status: "none" | "draft" | "approved";
}

export interface ApplicationDetail extends QueueItem {
  fund_name: string | null;
  lines: { line: number; item: string; vendor: string; category_label: string | null; amount_text: string; verdict: Verdict; verdict_label: string }[];
  reasons: Reason[];
  denial_rule_ids: string[];
  denial_draft: string | null;
  denial_approved_text: string | null;
  denial_approved_by: string | null;
  notice: string;
}

export interface FailureStats {
  applications: number;
  rows: { rule_id: string; title: string; applications: number; citation: Citation | null }[];
  approved_denials: number;
  note: string;
}

export interface SendResult {
  reference: string;
  club_token: string;
  verdict: Verdict;
  message: string;
}

export interface ClubStatus {
  reference: string;
  event_name: string;
  status: "sent" | "withdrawn";
  sent_at: string;
  verdict: Verdict;
  reviewer_message: string | null;
  note: string;
}

function message(status: number, data: unknown): string {
  const detail = (data as { detail?: { message?: string } } | null)?.detail;
  if (detail?.message) return detail.message;
  return status === 0 ? "Could not reach the Greenlight server." : `The server answered ${status}.`;
}

async function reviewer<T>(path: string, key: string, body?: unknown): Promise<Outcome<T>> {
  try {
    const response = await fetch(`${BASE}${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: { Accept: "application/json", "X-Reviewer-Key": key, ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
      body: body === undefined ? null : JSON.stringify(body),
    });
    const data: unknown = await response.json().catch(() => null);
    if (response.ok && data) return { ok: true, data: data as T };
    return { ok: false, error: message(response.status, data) };
  } catch {
    return { ok: false, error: message(0, null) };
  }
}

export const getQueue = (key: string) => reviewer<{ applications: QueueItem[]; note: string }>("/usg/queue", key);
export const getApplication = (key: string, id: number) => reviewer<ApplicationDetail>(`/usg/applications/${id}`, key);
export const getStats = (key: string) => reviewer<FailureStats>("/usg/stats", key);
export const draftDenial = (key: string, id: number, ruleIds: string[]) =>
  reviewer<{ text: string; notes: string[]; notice: string }>(`/usg/applications/${id}/denial-draft`, key, { rule_ids: ruleIds });
export const approveDenial = (key: string, id: number, text: string, reviewerName: string) =>
  reviewer<{ approved: boolean; message: string }>(`/usg/applications/${id}/denial-approve`, key, { text, reviewer_name: reviewerName });

export const sendToUsg = (clubName: string, check: MoneyCheckRequest) =>
  postJson<SendResult>("/usg/send", { club_name: clubName, consent: true, check });
export const clubStatus = (reference: string, token: string) =>
  postJson<ClubStatus>(`/usg/sent/${encodeURIComponent(reference)}`, { club_token: token });
export const withdraw = (reference: string, token: string) =>
  postJson<{ reference: string; status: string }>(`/usg/sent/${encodeURIComponent(reference)}/withdraw`, { club_token: token });
