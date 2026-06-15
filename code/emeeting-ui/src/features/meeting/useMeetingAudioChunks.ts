import { useEffect } from "react";

/** Bound CPU/network: ~60–90s of Opus-in-WebM per rolling segment. */
const SEGMENT_MAX_MS = 8_000;
const SEGMENT_MAX_BYTES = 2 * 1024 * 1024;

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function concatUint8Arrays(a: Uint8Array, b: Uint8Array): Uint8Array {
  const out = new Uint8Array(a.byteLength + b.byteLength);
  out.set(a, 0);
  out.set(b, a.byteLength);
  return out;
}

function hasWebmEbmlHeader(bytes: Uint8Array): boolean {
  if (bytes.byteLength < 4) return false;
  // EBML signature for WebM/Matroska container: 0x1A45DFA3
  return bytes[0] === 0x1a && bytes[1] === 0x45 && bytes[2] === 0xdf && bytes[3] === 0xa3;
}

/** Preferred mime for payload labelling; recorder may omit codec in `mimeType` after create. */
function createMediaRecorder(stream: MediaStream): { recorder: MediaRecorder; mimeHint: string } | null {
  if (typeof MediaRecorder === "undefined") return null;
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
    "audio/ogg",
  ];
  const supported = typeof MediaRecorder.isTypeSupported === "function";
  for (const m of candidates) {
    if (supported && !MediaRecorder.isTypeSupported(m)) continue;
    try {
      const recorder = new MediaRecorder(stream, { mimeType: m });
      return { recorder, mimeHint: recorder.mimeType || m };
    } catch {
      continue;
    }
  }
  try {
    const recorder = new MediaRecorder(stream);
    const mimeHint = recorder.mimeType || "audio/webm";
    return { recorder, mimeHint };
  } catch {
    return null;
  }
}

/** Sends periodic mic chunks over WS as `type: "audio"` for speech pipeline. */
export function useMeetingAudioChunks(
  streamRef: React.RefObject<MediaStream | null>,
  send: (type: string, payload?: unknown) => void,
  opts: { enabled: boolean; mediaReady: boolean; streamEpoch?: number; timesliceMs?: number }
) {
  const { enabled, mediaReady, streamEpoch = 0, timesliceMs = 3500 } = opts;

  useEffect(() => {
    if (!enabled || !mediaReady || !streamRef.current) return;
    const base = streamRef.current;
    // Mic on/off is `enabled`; do not require `track.enabled` here (avoids UI vs track mismatch).
    const audioTracks = base.getAudioTracks().filter((t) => t.readyState === "live");
    if (audioTracks.length === 0) {
      console.warn("[emeeting-audio] skip MediaRecorder: no live audio tracks", {
        total: base.getAudioTracks().length,
        states: base.getAudioTracks().map((t) => t.readyState),
      });
      return;
    }

    // Some browsers record mic more reliably on an audio-only MediaStream than video+audio.
    const recordStream = new MediaStream(audioTracks);
    const created = createMediaRecorder(recordStream);
    if (!created) {
      console.warn("[emeeting-audio] MediaRecorder unsupported for this stream/mime");
      return;
    }

    let cancelled = false;
    const { recorder: mr, mimeHint: mime } = created;
    let chunkSeq = 0;
    let segmentStarted = Date.now();
    let segmentMerged: Uint8Array | null = null;
    let restartingSegment = false;

    const restartSegment = () => {
      if (cancelled) return;
      segmentStarted = Date.now();
      segmentMerged = null;
      restartingSegment = false;
      try {
        mr.start(timesliceMs);
      } catch {
        /* recorder may be unavailable right after stop */
      }
    };

    mr.onstop = () => {
      restartSegment();
    };

    mr.ondataavailable = async (ev: BlobEvent) => {
      if (cancelled || !ev.data || ev.data.size === 0) return;
      try {
        const chunk = new Uint8Array(await ev.data.arrayBuffer());
        if (chunk.byteLength < 64) return;
        if (!segmentMerged) {
          // Browser can emit tiny trailer chunks around stop/start boundaries.
          // New segment MUST begin with a container header, otherwise ffmpeg/whisper rejects it.
          if (chunk.byteLength < 1024) return;
          if (!hasWebmEbmlHeader(chunk)) return;
          segmentMerged = chunk;
        } else {
          segmentMerged = concatUint8Arrays(segmentMerged, chunk);
        }
        const decodableChunk = segmentMerged;
        const elapsed = Date.now() - segmentStarted;
        const overBytes = decodableChunk.byteLength >= SEGMENT_MAX_BYTES;
        const overTime = elapsed >= SEGMENT_MAX_MS;
        const isFinal = overBytes || overTime;

        send("audio", {
          chunk_base64: bytesToBase64(decodableChunk),
          mime,
          encoding: "base64",
          /** Passed through to speech-service / faster-whisper (default ru in service if omitted). */
          language: "ru",
          timeslice_ms: timesliceMs,
          sent_at_ms: Date.now(),
          chunk_seq: ++chunkSeq,
          final_chunk: isFinal,
          segment_elapsed_ms: elapsed,
        });
        if (isFinal && !restartingSegment && mr.state === "recording") {
          restartingSegment = true;
          mr.stop();
        }
      } catch {
        /* ignore chunk upload errors */
      }
    };

    try {
      mr.start(timesliceMs);
    } catch (e) {
      console.warn("[emeeting-audio] MediaRecorder.start failed", e);
      return;
    }

    return () => {
      cancelled = true;
      try {
        if (mr.state !== "inactive") mr.stop();
      } catch {
        /* noop */
      }
    };
  }, [enabled, mediaReady, streamEpoch, streamRef, send, timesliceMs]);
}
