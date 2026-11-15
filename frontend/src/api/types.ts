// Shapes returned by the backend. Keep in step with backend/app/api/*.py.

export type Severity = "red" | "yellow" | "office_decides" | "info";
export type Verdict = "green" | "yellow" | "red" | "office_decides";

export interface Health {
  status: "ok" | "degraded";
  app: string;
  notice: string;
  ai_mode: "live" | "recorded" | "record";
  database: string;
  rules: {
    loaded: boolean;
    count: number;
    by_domain?: Record<string, number>;
    by_verification?: Record<string, number>;
    shown_yellow_until_verified?: number;
    problems: string[];
  };
  calendar: {
    loaded: boolean;
    verified?: string;
    verification_note?: string | null;
    terms?: string[];
    problems: string[];
  };
}

export interface Citation {
  rule_id: string;
  source: string;
  source_section: string | null;
  source_url: string;
  source_text: string;
  effective_date: string;
  verified: string;
  snapshot_fetched_at: string | null;
  uncertain_reasons: string[];
  display_severity: Severity;
}

export interface Rule {
  id: string;
  domain: string;
  kind: string;
  title: string;
  owner_office: string;
  severity: Severity;
  display_severity: Severity;
  message: string;
  verified: "read" | "fetched" | "unverified";
  verification_note: string | null;
  citation: Citation;
}

export interface RuleList {
  count: number;
  rules: Rule[];
}
