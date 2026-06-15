import { apiFetch } from "./http";

export type SessionReportResponse = {
  sessionId?: number;
  source?: string;
  stage?: string;
  model_version?: string;
  report?: Record<string, unknown>;
  [key: string]: unknown;
};

export type TeamSessionItem = {
  sessionId: number;
  title: string;
  sessionType: string;
  startDatetime?: string;
  hasReport: boolean;
  participantCount: number;
  topEmotion?: string;
  textEvents: number;
  pipelineStage?: string;
};

export type TeamReportResponse = {
  totalSessions: number;
  sessionsThisMonth: number;
  bySessionType: Record<string, number>;
  sessions: TeamSessionItem[];
  groupBy?: string;
  from?: string;
  to?: string;
};

export type TrendPoint = {
  period: string;
  label: string;
  value: number;
};

export type TeamTrendsResponse = {
  metric: string;
  groupBy: string;
  points: TrendPoint[];
};

export async function getSessionReport(sessionId: string): Promise<SessionReportResponse> {
  const res = await apiFetch(`/reports/session/${sessionId}`);
  if (res.ok) return res.json();

  const legacy = await apiFetch(`/sessions/${sessionId}/analysis/report`);
  if (legacy.ok) return legacy.json();

  const old = await apiFetch(`/reports/${sessionId}`);
  if (!old.ok) throw new Error("Failed to fetch report");
  return old.json();
}

/** @deprecated use getSessionReport */
export async function getReport(id: string) {
  return getSessionReport(id);
}

export async function getTeamReport(opts: {
  from?: string;
  to?: string;
  groupBy?: string;
} = {}): Promise<TeamReportResponse> {
  const params = new URLSearchParams();
  if (opts.from) params.set("from", opts.from);
  if (opts.to) params.set("to", opts.to);
  if (opts.groupBy) params.set("groupBy", opts.groupBy);
  const q = params.toString();
  const res = await apiFetch(`/reports/team${q ? `?${q}` : ""}`);
  if (!res.ok) throw new Error("Failed to fetch team report");
  return res.json();
}

export async function getTeamTrends(opts: {
  metric?: string;
  groupBy?: string;
  from?: string;
  to?: string;
} = {}): Promise<TeamTrendsResponse> {
  const params = new URLSearchParams();
  if (opts.metric) params.set("metric", opts.metric);
  if (opts.groupBy) params.set("groupBy", opts.groupBy);
  if (opts.from) params.set("from", opts.from);
  if (opts.to) params.set("to", opts.to);
  const q = params.toString();
  const res = await apiFetch(`/reports/team/trends${q ? `?${q}` : ""}`);
  if (!res.ok) throw new Error("Failed to fetch team trends");
  return res.json();
}
