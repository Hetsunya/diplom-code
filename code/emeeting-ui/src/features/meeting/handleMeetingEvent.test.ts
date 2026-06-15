import { describe, expect, it } from "vitest";
import { handleMeetingEvent } from "./handleMeetingEvent";

describe("handleMeetingEvent", () => {
  it("adds participant on user_joined", () => {
    const upserts: Array<{ id: string; name: string }> = [];
    const removes: string[] = [];

    handleMeetingEvent(
      { type: "user_joined", payload: { participant_id: "p1", name: "Alice" }, ts: new Date().toISOString() },
      {
        upsertParticipant: (p) => upserts.push({ id: p.id, name: p.name }),
        removeParticipant: (id) => removes.push(id),
      }
    );

    expect(upserts).toEqual([{ id: "p1", name: "Alice" }]);
    expect(removes).toEqual([]);
  });

  it("removes participant on user_left", () => {
    const upserts: Array<{ id: string; name: string }> = [];
    const removes: string[] = [];

    handleMeetingEvent(
      { type: "user_left", payload: { participant_id: "p1" }, ts: new Date().toISOString() },
      {
        upsertParticipant: (p) => upserts.push({ id: p.id, name: p.name }),
        removeParticipant: (id) => removes.push(id),
      }
    );

    expect(upserts).toEqual([]);
    expect(removes).toEqual(["p1"]);
  });

  it("supports legacy join/leave WSMessage shape", () => {
    const upserts: Array<{ id: string; name: string }> = [];
    const removes: string[] = [];

    handleMeetingEvent(
      { type: "join", participant_id: "p1", payload: { name: "Alice" } },
      {
        upsertParticipant: (p) => upserts.push({ id: p.id, name: p.name }),
        removeParticipant: (id) => removes.push(id),
      }
    );
    handleMeetingEvent(
      { type: "leave", participant_id: "p1", payload: {} },
      {
        upsertParticipant: (p) => upserts.push({ id: p.id, name: p.name }),
        removeParticipant: (id) => removes.push(id),
      }
    );

    expect(upserts[0]).toEqual({ id: "p1", name: "Alice" });
    expect(removes).toEqual(["p1"]);
  });

  it("calls onMeetingEnded on meeting_ended", () => {
    let called = 0;
    handleMeetingEvent(
      { type: "meeting_ended", payload: { reason: "host_left" }, ts: new Date().toISOString() },
      {
        upsertParticipant: () => undefined,
        removeParticipant: () => undefined,
        onMeetingEnded: () => {
          called++;
        },
      }
    );
    expect(called).toBe(1);
  });
});

