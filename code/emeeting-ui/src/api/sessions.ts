import { apiFetch } from "./http";
import type { Session, CreateSessionDTO } from "../types/db";

export async function getSessions(): Promise<Session[]> {
  const res = await apiFetch("/sessions");
  if (!res.ok) throw new Error("Failed to fetch sessions");
  const json = await res.json();
  return Array.isArray(json) ? json : [];
}

export async function createSession(data: CreateSessionDTO): Promise<Session> {
  const res = await apiFetch("/sessions", {
    method: "POST",
    body: JSON.stringify(data),
  });

  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

export async function getSession(id: string): Promise<Session> {
  const res = await apiFetch(`/sessions/${id}`);
  if (!res.ok) throw new Error("Failed to fetch session");
  return res.json();
}

/** Persisted meeting chat (REST); live sync remains over WebSocket `chat_message`. */
export type ChatMessageDTO = {
  chat_message_id: number;
  session_id: number;
  participant_id: string;
  client_message_id?: string | null;
  sender_name: string;
  body: string;
  created_at: string;
};

export async function getSessionChatMessages(
  sessionId: string,
  limit = 120
): Promise<ChatMessageDTO[]> {
  const q = limit > 0 ? `?limit=${encodeURIComponent(String(limit))}` : "";
  const res = await apiFetch(`/sessions/${sessionId}/chat/messages${q}`);
  if (!res.ok) throw new Error("Failed to fetch chat messages");
  const json = (await res.json()) as { messages?: ChatMessageDTO[] };
  return Array.isArray(json.messages) ? json.messages : [];
}
