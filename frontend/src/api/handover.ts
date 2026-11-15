// Handover packet API: shapes from backend/app/services/handover.py and backend/app/api/handover.py.

import { postJson } from "./events";
import type { YearPlanRequest } from "./plans";

export interface HandoverPacket {
  as_of: string;
  club_name: string;
  packets: { role: string; text: string }[];
  next_year_plan: YearPlanRequest;
  notes: string[];
  notice: string;
}

export const buildHandover = (plan: YearPlanRequest, applications: { reference: string; club_token: string }[]) =>
  postJson<HandoverPacket>("/handover", { plan, applications });
export const approvePacket = (role: string, text: string) =>
  postJson<{ approved: boolean; message: string }>("/handover/approve", { role, text });
