import { create } from "zustand";

export type MeetingParticipant = {
  id: string;
  name: string;
  emotion?: string;
  emotionConfidence?: number;
  /** True after first emotion or face_analysis for this tile (replaces vague “analyzing”). */
  faceSignalReceived?: boolean;
};

type MeetingState = {
  participants: Record<string, MeetingParticipant>;
  toasts: string[];
  upsertParticipant: (p: MeetingParticipant) => void;
  removeParticipant: (id: string) => void;
  /** Полная замена списка с сохранением эмоций по id (снимок с сервера). */
  replaceParticipantsFromSnapshot: (list: Pick<MeetingParticipant, "id" | "name">[]) => void;
  pushToast: (message: string) => void;
  popToast: () => void;
  reset: () => void;
};

export const useMeetingStore = create<MeetingState>((set) => ({
  participants: {},
  toasts: [],
  upsertParticipant: (p) =>
    set((s) => ({
      participants: {
        ...s.participants,
        [p.id]: { ...(s.participants[p.id] ?? {}), ...p },
      },
    })),
  removeParticipant: (id) =>
    set((s) => {
      if (!s.participants[id]) return s;
      const next = { ...s.participants };
      delete next[id];
      return { participants: next };
    }),
  replaceParticipantsFromSnapshot: (list) =>
    set((s) => {
      const next: Record<string, MeetingParticipant> = {};
      for (const p of list) {
        const prev = s.participants[p.id];
        next[p.id] = {
          id: p.id,
          name: p.name,
          emotion: prev?.emotion ?? "Neutral",
          emotionConfidence: prev?.emotionConfidence ?? 0,
          faceSignalReceived: prev?.faceSignalReceived ?? false,
        };
      }
      return { participants: next };
    }),
  pushToast: (message) =>
    set((s) => ({
      toasts: [...s.toasts, message].slice(-3),
    })),
  popToast: () =>
    set((s) => ({
      toasts: s.toasts.slice(1),
    })),
  reset: () => set({ participants: {}, toasts: [] }),
}));

