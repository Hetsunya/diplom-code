import type {
  ParticipantsSnapshotPayload,
  UserJoinedPayload,
  UserLeftPayload,
  WSEvent,
} from "./types";
import type { MeetingParticipant } from "./useMeetingStore";

type Ops = {
  upsertParticipant: (p: MeetingParticipant) => void;
  removeParticipant: (id: string) => void;
  replaceParticipantsFromSnapshot?: (list: Pick<MeetingParticipant, "id" | "name">[]) => void;
  pushToast?: (message: string) => void;
  onMeetingEnded?: (payload: unknown) => void;
};

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null;

export function handleMeetingEvent(msg: unknown, ops: Ops) {
  if (!isRecord(msg)) return;
  const type = typeof msg.type === "string" ? msg.type : undefined;
  if (!type) return;

  const event = msg as WSEvent;
  const payload = event.payload;

  if (type === "user_joined" && isRecord(payload)) {
    const p = payload as unknown as UserJoinedPayload & Record<string, unknown>;
    const id = typeof p.participant_id === "string" ? p.participant_id : undefined;
    if (!id) return;
    const name = typeof p.name === "string" && p.name.length > 0 ? p.name : `Participant ${id}`;
    ops.upsertParticipant({ id, name });
    ops.pushToast?.(`${name} подключился(лась)`);
    return;
  }

  if (type === "user_left" && isRecord(payload)) {
    const p = payload as unknown as UserLeftPayload & Record<string, unknown>;
    const id = typeof p.participant_id === "string" ? p.participant_id : undefined;
    if (!id) return;
    ops.removeParticipant(id);
    const name = typeof p.name === "string" && p.name.length > 0 ? p.name : `Participant ${id}`;
    ops.pushToast?.(`${name} вышел(ла)`);
    return;
  }

  if (type === "meeting_ended") {
    ops.onMeetingEnded?.(payload);
    return;
  }

  if (type === "participants_snapshot" && isRecord(payload)) {
    const p = payload as unknown as ParticipantsSnapshotPayload & Record<string, unknown>;
    const raw = p.participants;
    if (!Array.isArray(raw) || !ops.replaceParticipantsFromSnapshot) return;
    const list: Pick<MeetingParticipant, "id" | "name">[] = [];
    for (const item of raw) {
      if (!isRecord(item)) continue;
      const id =
        typeof item.participant_id === "string"
          ? item.participant_id
          : typeof item["participant_id"] === "string"
            ? (item["participant_id"] as string)
            : undefined;
      if (!id) continue;
      const nameRaw = item.name ?? item["name"];
      const name =
        typeof nameRaw === "string" && nameRaw.length > 0 ? nameRaw : `Participant ${id}`;
      list.push({ id, name });
    }
    ops.replaceParticipantsFromSnapshot(list);
    return;
  }

  // Back-compat WSMessage (old shape): join/leave.
  const participantId = typeof msg.participant_id === "string" ? msg.participant_id : undefined;
  const wsPayload = isRecord(msg.payload) ? msg.payload : undefined;

  if (type === "join" && participantId) {
    const nameRaw = wsPayload?.["name"];
    const name = typeof nameRaw === "string" && nameRaw.length > 0 ? nameRaw : `Participant ${participantId}`;
    ops.upsertParticipant({ id: participantId, name });
    ops.pushToast?.(`${name} подключился(лась)`);
  }

  if (type === "leave" && participantId) {
    ops.removeParticipant(participantId);
    ops.pushToast?.(`Participant ${participantId} вышел(ла)`);
  }
}

