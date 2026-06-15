import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useSessionWS } from "./useSessionWS";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];

  url: string;
  readyState = 0;
  sent: string[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.onclose?.();
  }

  open() {
    this.readyState = 1;
    this.onopen?.();
  }
}

describe("useSessionWS", () => {
  it("reconnects and re-sends join", async () => {
    vi.useFakeTimers();
    // @ts-expect-error test override
    globalThis.WebSocket = FakeWebSocket;
    // JSDOM localStorage can be disabled in some environments; provide minimal stub.
    const storageStub = (() => {
      const data = new Map<string, string>();
      return {
        getItem: (k: string) => data.get(k) ?? null,
        setItem: (k: string, v: string) => void data.set(k, v),
        removeItem: (k: string) => void data.delete(k),
        clear: () => void data.clear(),
      };
    })();
    // @ts-expect-error test override
    globalThis.localStorage = storageStub;
    // @ts-expect-error test override
    globalThis.sessionStorage = storageStub;

    const { unmount } = renderHook(() =>
      useSessionWS("1", "p1", undefined, { reconnect: true, maxReconnectDelayMs: 10 })
    );

    expect(FakeWebSocket.instances.length).toBe(1);
    FakeWebSocket.instances[0]!.open();
    expect(FakeWebSocket.instances[0]!.sent.some((s) => s.includes('"type":"join"'))).toBe(true);

    // Simulate close -> should schedule reconnect.
    FakeWebSocket.instances[0]!.close();
    await vi.advanceTimersByTimeAsync(20);

    expect(FakeWebSocket.instances.length).toBeGreaterThanOrEqual(2);
    const ws2 = FakeWebSocket.instances[1]!;
    ws2.open();
    expect(ws2.sent.some((s) => s.includes('"type":"join"'))).toBe(true);

    unmount();
    vi.useRealTimers();
  });
});

