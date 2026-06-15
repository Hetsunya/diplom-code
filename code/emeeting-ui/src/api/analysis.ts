import { apiFetch } from "./http";

export type AnalysisEventDTO = {
  analysis_event_id: number;
  session_id: number;
  event_type: string;
  participant_id?: string;
  trace_id?: string;
  module?: string;
  stage?: string;
  model_version?: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export async function getSessionAnalysisEvents(
  sessionId: string,
  opts: { module?: string; participantId?: string; limit?: number } = {}
): Promise<AnalysisEventDTO[]> {
  const params = new URLSearchParams();
  if (opts.module) params.set("module", opts.module);
  if (opts.participantId) params.set("participant_id", opts.participantId);
  if (typeof opts.limit === "number" && opts.limit > 0) {
    params.set("limit", String(opts.limit));
  }
  const query = params.toString();
  const url = `/sessions/${sessionId}/analysis/events${query ? `?${query}` : ""}`;
  const res = await apiFetch(url);
  if (!res.ok) throw new Error("Failed to fetch analysis events");
  const json = await res.json();
  return Array.isArray(json) ? (json as AnalysisEventDTO[]) : [];
}

export type TranscriptionLineDTO = {
  participantId: string;
  traceId: string;
  text: string;
  final: boolean;
  at: string;
};

export type SessionTranscriptionDTO = {
  sessionId: number;
  lines: TranscriptionLineDTO[];
};

export async function getSessionTranscription(
  sessionId: string,
  opts: { participantId?: string; limit?: number } = {}
): Promise<SessionTranscriptionDTO> {
  const params = new URLSearchParams();
  if (opts.participantId) params.set("participant_id", opts.participantId);
  if (typeof opts.limit === "number" && opts.limit > 0) {
    params.set("limit", String(opts.limit));
  }
  const query = params.toString();
  const url = `/sessions/${sessionId}/transcription${query ? `?${query}` : ""}`;
  const res = await apiFetch(url);
  if (!res.ok) throw new Error("Failed to fetch transcription");
  return res.json() as Promise<SessionTranscriptionDTO>;
}

