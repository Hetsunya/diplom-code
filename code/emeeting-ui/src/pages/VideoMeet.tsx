import { useCallback, useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMediaStream } from "../hooks/useMediaStream";
import { useMeetingWebSocket } from "../features/meeting/useMeetingWebSocket";
import { useMeetingStore } from "../features/meeting/useMeetingStore";
import { useScreenShare } from "../hooks/useScreenShare";
import {
  MeetingTranscriptRail,
  type ChatLine,
  type TranscriptLine,
} from "../features/meeting/MeetingTranscriptRail";
import {
  IconCallEnd,
  IconCamOff,
  IconMicOff,
  IconMicOn,
  IconCamOn,
  IconScreenShare,
} from "../components/MeetingUiIcons";
import { useMeetingAudioChunks } from "../features/meeting/useMeetingAudioChunks";
import { getSession, getSessionChatMessages } from "../api/sessions";
import { getSessionTranscription } from "../api/analysis";

export type Emotion = "Happy" | "Neutral" | "Engaged" | "Focused" | "Surprised" | "Thoughtful";

type Participant = {
  id: string;
  name: string;
  emotion: Emotion;
  emotionConfidence: number;
  faceSignalReceived: boolean;
};

function mapEmotionLabel(normalized: string): Emotion | undefined {
  if (normalized.includes("happy")) return "Happy";
  if (normalized.includes("surpris")) return "Surprised";
  if (normalized.includes("neutral")) return "Neutral";
  if (normalized.includes("fear") || normalized.includes("disgust")) return "Engaged";
  if (normalized.includes("sad")) return "Focused";
  if (normalized.includes("angry")) return "Thoughtful";
  return undefined;
}

function parseEmotionFromLegacyPayload(p: Record<string, unknown>): { emotion: Emotion; confidence: number } | null {
  let emotion: Emotion | undefined;
  let confidence = 0;

  const maybeEmotion = p["emotion"];
  if (typeof maybeEmotion === "string") {
    emotion = mapEmotionLabel(maybeEmotion.toLowerCase());
  }

  const maybeConfidence = p["confidence"];
  if (typeof maybeConfidence === "number") {
    confidence = maybeConfidence > 1 ? maybeConfidence : maybeConfidence * 100;
  }

  const probs = p["probs"] ?? p["probabilities"];
  if (!emotion && probs && typeof probs === "object") {
    const pr = probs as Record<string, unknown>;
    let bestKey: string | null = null;
    let bestVal = -1;
    for (const [k, v] of Object.entries(pr)) {
      if (typeof v !== "number") continue;
      if (v > bestVal) {
        bestVal = v;
        bestKey = k;
      }
    }
    if (bestKey) {
      emotion = mapEmotionLabel(bestKey.toLowerCase());
      confidence = bestVal > 1 ? bestVal : bestVal * 100;
    }
  }

  if (!emotion) return null;
  return { emotion, confidence: Math.round(confidence) };
}

function parseFaceAnalysisPayload(p: Record<string, unknown>): { emotion: Emotion; confidence: number } | null {
  const ff = p["face_features"];
  if (!ff || typeof ff !== "object") return null;
  const f = ff as Record<string, unknown>;
  if (f["face_detected"] === false) return null;
  let emotion: Emotion | undefined;
  let confidence = 0;
  const dom = f["dominant_emotion"];
  if (typeof dom === "string") emotion = mapEmotionLabel(dom.toLowerCase());

  const probs = f["probs"] ?? f["probabilities"];
  if (!emotion && probs && typeof probs === "object") {
    const pr = probs as Record<string, unknown>;
    let bestKey: string | null = null;
    let bestVal = -1;
    for (const [k, v] of Object.entries(pr)) {
      if (typeof v !== "number") continue;
      if (v > bestVal) {
        bestVal = v;
        bestKey = k;
      }
    }
    if (bestKey) {
      emotion = mapEmotionLabel(bestKey.toLowerCase());
      confidence = bestVal > 1 ? bestVal : bestVal * 100;
    }
  }

  const maybeConf = f["confidence"];
  if (typeof maybeConf === "number") {
    confidence = maybeConf > 1 ? maybeConf : maybeConf * 100;
  }

  if (!emotion) return null;
  return { emotion, confidence: Math.round(confidence) };
}

/** Debug overlay: bbox + gate info (typed `face_debug` from ai-gateway). */
type FaceDebugPayload = {
  frameW: number;
  frameH: number;
  region: { x: number; y: number; w: number; h: number } | null;
  landmarks: Array<{ x: number; y: number }>;
  gatePassed: boolean;
  skipReason: string | null;
  dominant: string;
  modelConfidence: number;
  minConfidence: number;
  traceId: string;
};

function parseFaceDebugPayload(p: Record<string, unknown>): FaceDebugPayload | null {
  const fw = p["frame_width"];
  const fh = p["frame_height"];
  if (typeof fw !== "number" || typeof fh !== "number" || fw <= 0 || fh <= 0) return null;
  const regionRaw = p["region"];
  let region: FaceDebugPayload["region"] = null;
  const landmarks: FaceDebugPayload["landmarks"] = [];
  if (regionRaw && typeof regionRaw === "object") {
    const r = regionRaw as Record<string, unknown>;
    const x = r["x"];
    const y = r["y"];
    const w = r["w"];
    const h = r["h"];
    if (
      typeof x === "number" &&
      typeof y === "number" &&
      typeof w === "number" &&
      typeof h === "number"
    ) {
      region = { x, y, w, h };
    }
  }
  const landmarksRaw = p["landmarks"];
  if (Array.isArray(landmarksRaw)) {
    for (const item of landmarksRaw) {
      if (!item || typeof item !== "object") continue;
      const m = item as Record<string, unknown>;
      const x = m["x"];
      const y = m["y"];
      if (typeof x === "number" && typeof y === "number") {
        landmarks.push({ x, y });
      }
    }
  }
  const dom = p["dominant_emotion"];
  const mc = p["model_confidence"];
  const gp = p["gate_passed"];
  const sr = p["skip_reason"];
  const mic = p["min_confidence"];
  const tid = p["trace_id"];
  return {
    frameW: fw,
    frameH: fh,
    region,
    landmarks,
    gatePassed: gp === true,
    skipReason: sr == null ? null : String(sr),
    dominant: typeof dom === "string" ? dom : "?",
    modelConfidence: typeof mc === "number" ? mc : 0,
    minConfidence: typeof mic === "number" ? mic : 0,
    traceId: typeof tid === "string" ? tid : "",
  };
}

/**
 * `.tile-media` is 16:9; `<video>` uses `object-fit: cover` → map JPEG frame pixels to tile %.
 */
function faceDebugOverlayStyleCover(
  region: { x: number; y: number; w: number; h: number },
  frameW: number,
  frameH: number
): CSSProperties {
  const cw = 1;
  const ch = 9 / 16;
  const scale = Math.max(cw / frameW, ch / frameH);
  const dispW = frameW * scale;
  const dispH = frameH * scale;
  const ox = (cw - dispW) / 2;
  const oy = (ch - dispH) / 2;
  const left = ox + region.x * scale;
  const top = oy + region.y * scale;
  const w = region.w * scale;
  const h = region.h * scale;
  return {
    left: `${left * 100}%`,
    top: `${(top / ch) * 100}%`,
    width: `${w * 100}%`,
    height: `${(h / ch) * 100}%`,
  };
}

function faceDebugPointStyleCover(
  point: { x: number; y: number },
  frameW: number,
  frameH: number
): CSSProperties {
  const cw = 1;
  const ch = 9 / 16;
  const scale = Math.max(cw / frameW, ch / frameH);
  const dispW = frameW * scale;
  const dispH = frameH * scale;
  const ox = (cw - dispW) / 2;
  const oy = (ch - dispH) / 2;
  const left = ox + point.x * scale;
  const top = oy + point.y * scale;
  return {
    left: `${left * 100}%`,
    top: `${(top / ch) * 100}%`,
  };
}

const VideoMeet = () => {
  const { id = "" } = useParams(); // session ID
  const navigate = useNavigate();
  const getOrCreateParticipant = () => {
    const existingId = sessionStorage.getItem("participant_id") || localStorage.getItem("participant_id");
    if (existingId) return existingId;

    const uuid =
      globalThis.crypto?.randomUUID?.() ||
      `p_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
    sessionStorage.setItem("participant_id", uuid);

    if (!sessionStorage.getItem("participant_name") && !localStorage.getItem("participant_name")) {
      sessionStorage.setItem("participant_name", "You");
    }

    return uuid;
  };

  const [participantId] = useState<string>(getOrCreateParticipant);
  const participantName =
    sessionStorage.getItem("participant_name") || localStorage.getItem("participant_name") || "You";
  const participantRole =
    sessionStorage.getItem("participant_role") || localStorage.getItem("participant_role") || "participant";
  const normalizeSpeakerLabel = (pid: string, fallback?: string) => {
    if (pid === participantId) return participantName;
    const fromStore = useMeetingStore.getState().participants[pid]?.name;
    if (typeof fromStore === "string" && fromStore.trim()) return fromStore.trim();
    if (typeof fallback === "string" && fallback.trim()) return fallback.trim();
    return "Участник";
  };

  const {
    videoRef,
    streamRef,
    mediaReady,
    streamEpoch,
    captureFrame,
    toggleMic,
    toggleCam,
    micEnabled,
    camEnabled,
    error: mediaError,
  } = useMediaStream();

  const { startShare, error: shareError } = useScreenShare();

  const meetingParticipants = useMeetingStore((s) => s.participants);
  const toasts = useMeetingStore((s) => s.toasts);
  const popToast = useMeetingStore((s) => s.popToast);
  const upsert = useMeetingStore((s) => s.upsertParticipant);
  const resetMeetingStore = useMeetingStore((s) => s.reset);

  const [transcriptLines, setTranscriptLines] = useState<TranscriptLine[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatLine[]>([]);
  const [lastTextAt, setLastTextAt] = useState<number | null>(null);
  const [faceDebugByParticipant, setFaceDebugByParticipant] = useState<
    Record<string, FaceDebugPayload>
  >({});
  const [verdictSummary, setVerdictSummary] = useState<string | null>(null);
  const [verdictDetail, setVerdictDetail] = useState<string | null>(null);
  const [verdictOpen, setVerdictOpen] = useState(false);

  useEffect(() => {
    resetMeetingStore();
  }, [id, resetMeetingStore]);

  useEffect(() => {
    upsert({
      id: participantId,
      name: participantName,
      emotion: "Neutral",
      emotionConfidence: 0,
      faceSignalReceived: false,
    });
  }, [participantId, participantName, upsert]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const s = await getSession(id);
        if (cancelled) return;
        const cfg = s.analysisConfigJson;
        if (cfg && typeof cfg === "object") {
          const maybeModules = (cfg as { modules?: unknown }).modules;
          const modulesPayload =
            maybeModules && typeof maybeModules === "object" ? maybeModules : cfg;
          sessionStorage.setItem(`session_analysis_modules:${id}`, JSON.stringify(modulesPayload));
        }
      } catch {
        // optional
      }
    })();
    (async () => {
      try {
        const rows = await getSessionChatMessages(id, 150);
        if (cancelled) return;
        const mapped: ChatLine[] = rows.map((r) => ({
          id: String(r.chat_message_id),
          participantId: r.participant_id,
          name: r.sender_name?.trim() || normalizeSpeakerLabel(r.participant_id),
          text: r.body,
          at: r.created_at,
        }));
        setChatMessages((prev) => {
          const byId = new Map<string, ChatLine>();
          for (const m of mapped) byId.set(m.id, m);
          for (const m of prev) {
            if (!byId.has(m.id)) byId.set(m.id, m);
          }
          return Array.from(byId.values())
            .sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime())
            .slice(-200);
        });
      } catch {
        // History is optional; live chat still works over WS.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const history = await getSessionTranscription(id, { limit: 300 });
        if (cancelled) return;
        const next: TranscriptLine[] = history.lines.map((row) => ({
          traceId: row.traceId || `history-${row.participantId}`,
          participantId: row.participantId,
          speakerLabel: normalizeSpeakerLabel(row.participantId),
          text: row.text,
          final: row.final,
          at: row.at || new Date().toISOString(),
        }));
        setTranscriptLines(
          next
            .sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime())
            .slice(-160)
        );
      } catch {
        // History is optional; live flow keeps working.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const onAnalysisMessage = useCallback(
    (msg: unknown) => {
      if (typeof msg !== "object" || msg === null) return;
      const m = msg as { type?: unknown; participant_id?: unknown; payload?: unknown };
      const type = typeof m.type === "string" ? m.type : undefined;
      const pid = typeof m.participant_id === "string" ? m.participant_id : undefined;

      const store = useMeetingStore.getState();
      const nameFor = (id: string) => normalizeSpeakerLabel(id, store.participants[id]?.name);

      if (type === "chat_message" && pid && m.payload && typeof m.payload === "object") {
        const p = m.payload as Record<string, unknown>;
        const text = typeof p.text === "string" ? p.text.trim() : "";
        if (!text) return;
        const nameRaw = p.name;
        const dispName = typeof nameRaw === "string" && nameRaw.trim() ? nameRaw.trim() : nameFor(pid);
        const clientId = typeof p.client_id === "string" ? p.client_id : "";
        const tsRaw = (m as { timestamp?: unknown }).timestamp;
        const at = typeof tsRaw === "string" ? tsRaw : new Date().toISOString();
        const mid = p.chat_message_id;
        const id =
          typeof mid === "number" && Number.isFinite(mid)
            ? String(mid)
            : clientId
              ? `${pid}:${clientId}`
              : `${pid}-${at}-${text.slice(0, 48)}`;
        setChatMessages((prev) => {
          if (prev.some((x) => x.id === id)) return prev;
          return [...prev, { id, participantId: pid, name: dispName, text, at }].slice(-200);
        });
        return;
      }

      if (type === "emotion" && pid && m.payload && typeof m.payload === "object") {
        const parsed = parseEmotionFromLegacyPayload(m.payload as Record<string, unknown>);
        if (parsed) {
          upsert({
            id: pid,
            name: nameFor(pid),
            emotion: parsed.emotion,
            emotionConfidence: parsed.confidence,
            faceSignalReceived: true,
          });
        }
        return;
      }

      if (type === "face_analysis" && pid && m.payload && typeof m.payload === "object") {
        const parsed = parseFaceAnalysisPayload(m.payload as Record<string, unknown>);
        if (parsed) {
          upsert({
            id: pid,
            name: nameFor(pid),
            emotion: parsed.emotion,
            emotionConfidence: parsed.confidence,
            faceSignalReceived: true,
          });
        }
        return;
      }

      if (type === "face_debug" && pid && m.payload && typeof m.payload === "object") {
        const parsed = parseFaceDebugPayload(m.payload as Record<string, unknown>);
        if (parsed) {
          setFaceDebugByParticipant((prev) => ({ ...prev, [pid]: parsed }));
        }
        return;
      }

      if (
        (type === "analysis_report_partial" || type === "analysis_report") &&
        m.payload &&
        typeof m.payload === "object"
      ) {
        const p = m.payload as Record<string, unknown>;
        const report =
          p.report && typeof p.report === "object" ? (p.report as Record<string, unknown>) : p;
        let summary =
          typeof report.summary === "string" && report.summary.trim()
            ? report.summary.trim()
            : "";
        const meetingSummary =
          report.meeting_summary && typeof report.meeting_summary === "object"
            ? (report.meeting_summary as Record<string, unknown>)
            : null;
        if (!summary && meetingSummary) {
          const highlights = meetingSummary.highlights_ru;
          if (Array.isArray(highlights) && typeof highlights[0] === "string") {
            summary = highlights[0];
          }
        }
        if (!summary && type === "analysis_report") {
          summary = "Финальный отчёт готов";
        }
        if (!summary) {
          summary = "Промежуточный вердикт обновлён";
        }
        setVerdictSummary(summary);
        setVerdictDetail(JSON.stringify(report, null, 2));
        return;
      }

      if (type === "text_analysis" && pid && m.payload && typeof m.payload === "object") {
        const p = m.payload as Record<string, unknown>;
        const traceRaw = p["trace_id"];
        const serverTraceId =
          typeof traceRaw === "string" && traceRaw.trim() ? traceRaw : `local-${Date.now()}-${pid}`;
        const partial = p["transcript_partial"];
        const final = p["transcript_final"];
        const text =
          typeof final === "string" ? final : typeof partial === "string" ? partial : "";
        const stage = p["stage"];
        const isFinal =
          typeof final === "string" ||
          stage === "final" ||
          (typeof stage === "string" && stage.toLowerCase().includes("final"));
        const normalizedText = text.trim();
        if (!normalizedText) return;

        setTranscriptLines((prev) => {
          const finalizedPrev = prev.map((line) =>
            !line.final && line.participantId === pid ? { ...line, final: true } : line
          );
          const last = prev[prev.length - 1];
          const looksDuplicate =
            last &&
            last.participantId === pid &&
            last.text.trim() === normalizedText &&
            last.final === isFinal;
          if (looksDuplicate) {
            return finalizedPrev;
          }

          const line: TranscriptLine = {
            traceId: `${serverTraceId}:${isFinal ? "f" : "p"}:${Date.now()}`,
            participantId: pid,
            speakerLabel: nameFor(pid),
            text: normalizedText,
            final: isFinal,
            at: new Date().toISOString(),
          };
          return [...finalizedPrev, line].slice(-160);
        });
        setLastTextAt(Date.now());
        return;
      }
    },
    [upsert]
  );

  const { send, close, connected } = useMeetingWebSocket(
    id,
    participantId,
    onAnalysisMessage,
    () => {
      sessionStorage.setItem("meeting_notice", "Митинг завершён (хост вышел).");
      navigate("/sessions");
    }
  );

  const sendChatMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      const client_id =
        globalThis.crypto?.randomUUID?.() ?? `c_${Date.now()}_${Math.floor(Math.random() * 1e9)}`;
      send("chat_message", {
        text: trimmed.slice(0, 2000),
        name: participantName,
        client_id,
      });
    },
    [send, participantName]
  );

  useMeetingAudioChunks(streamRef, send, {
    enabled: micEnabled && connected,
    mediaReady,
    streamEpoch,
    timesliceMs: 1000,
  });

  useEffect(() => {
    if (toasts.length === 0) return;
    const t = window.setTimeout(() => popToast(), 2500);
    return () => window.clearTimeout(t);
  }, [toasts.length, popToast]);

  const participants: Record<string, Participant> = Object.fromEntries(
    Object.entries(meetingParticipants).map(([k, v]) => [
      k,
      {
        id: v.id,
        name: v.name,
        emotion: (v.emotion as Emotion) ?? "Neutral",
        emotionConfidence: v.emotionConfidence ?? 0,
        faceSignalReceived: v.faceSignalReceived === true,
      },
    ])
  );

  const FRAME_CAPTURE_MS = 320;

  useEffect(() => {
    if (!id || !mediaReady || !camEnabled) return;

    const timer = window.setInterval(() => {
      const frame = captureFrame();
      if (!frame) return;
      send("frame", { frame });
    }, FRAME_CAPTURE_MS);

    return () => window.clearInterval(timer);
  }, [id, mediaReady, camEnabled, captureFrame, send]);

  const emotionToClass = (emotion: Emotion) => {
    switch (emotion) {
      case "Happy":
        return "happy";
      case "Engaged":
        return "engaged";
      case "Focused":
        return "focused";
      case "Surprised":
        return "surprised";
      case "Thoughtful":
        return "thoughtful";
      case "Neutral":
      default:
        return "neutral";
    }
  };

  const leaveMeeting = () => {
    send("leave", { name: participantName, role: participantRole });
    close();
    sessionStorage.setItem("meeting_notice", "Вы вышли из встречи.");
    navigate("/sessions");
  };

  const endMeeting = () => {
    // If not host, behave like leave.
    if (participantRole !== "host") {
      leaveMeeting();
      return;
    }
    send("end_meeting", { role: "host" });
    close();
    sessionStorage.setItem("meeting_notice", "Вы завершили встречу.");
    navigate("/sessions");
  };

  return (
    <div className="video-container">
      <div className="video-meet-layout">
        <div className="video-meet-main">
          {(mediaError || shareError) && (
            <div
              style={{
                background: "#3b2a1f",
                color: "white",
                padding: "10px 12px",
                borderRadius: 10,
                marginBottom: 12,
              }}
              role="status"
            >
              {mediaError || shareError}
            </div>
          )}
          {toasts.length > 0 && (
            <div style={{ position: "fixed", top: 12, right: 12, zIndex: 10 }}>
              {toasts.map((t, idx) => (
                <div
                  key={`${idx}-${t}`}
                  style={{
                    background: "rgba(0,0,0,0.75)",
                    color: "white",
                    padding: "10px 12px",
                    borderRadius: 10,
                    marginBottom: 8,
                    maxWidth: 320,
                  }}
                >
                  {t}
                </div>
              ))}
            </div>
          )}
          <div className="video-grid">
            {Object.values(participants).map((p) => {
              const isSelf = p.id === participantId;
              const showCamOff = isSelf && !camEnabled;
              const faceDbg = faceDebugByParticipant[p.id];
              const showFaceDebugHud = Boolean(faceDbg && isSelf);
              return (
                <div key={p.id} className="video-tile">
                  <div className="tile-media">
                    {isSelf ? (
                      <>
                        <video
                          ref={videoRef}
                          autoPlay
                          playsInline
                          className={`tile-media__video ${showCamOff ? "video-hidden" : ""}`}
                        />
                        {showCamOff && (
                          <div
                            className="video-placeholder video-placeholder--overlay video-placeholder--cam-off"
                            aria-hidden
                          >
                            <IconCamOff size={56} className="video-placeholder__cam-icon" />
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="fake-video fake-video--remote">
                        <div className="face-placeholder" />
                      </div>
                    )}

                    {showFaceDebugHud && faceDbg && (
                      <>
                        {faceDbg.region && (
                          <div
                            className="face-debug-box"
                            style={faceDebugOverlayStyleCover(
                              faceDbg.region,
                              faceDbg.frameW,
                              faceDbg.frameH
                            )}
                          />
                        )}
                        {faceDbg.landmarks.map((lm, idx) => (
                          <div
                            key={`lm-${idx}`}
                            className="face-debug-point"
                            style={faceDebugPointStyleCover(lm, faceDbg.frameW, faceDbg.frameH)}
                          />
                        ))}
                        <div className="face-debug-hud">
                          <div>
                            {faceDbg.dominant} model={faceDbg.modelConfidence.toFixed(1)} minThr=
                            {faceDbg.minConfidence.toFixed(1)}{" "}
                            {faceDbg.gatePassed ? "pass" : `skip:${faceDbg.skipReason ?? "?"}`}
                          </div>
                          <div>
                            frame {faceDbg.frameW}×{faceDbg.frameH}
                            {faceDbg.traceId ? ` · ${faceDbg.traceId.slice(0, 8)}…` : ""}
                          </div>
                          {!faceDbg.region && (
                            <div className="face-debug-hud__warn">region=null — bbox от OpenCV нет</div>
                          )}
                        </div>
                      </>
                    )}

                    {!p.faceSignalReceived ? (
                      <div
                        className="emotion-indicator emotion-indicator--pending"
                        title="Ожидание данных о лице с сервера"
                      >
                        Лицо: —
                      </div>
                    ) : (
                      <div className={`emotion-indicator ${emotionToClass(p.emotion)}`}>
                        {p.emotion} {p.emotionConfidence}%
                      </div>
                    )}

                    <div className="participant-chip">
                      <span className="participant-chip__name">{p.name}</span>
                      {isSelf && (
                        <span className="participant-chip__devices">
                          <span
                            className={`participant-chip__icon ${micEnabled ? "participant-chip__icon--on" : "participant-chip__icon--off"}`}
                            title={micEnabled ? "Микрофон включён" : "Микрофон выключен"}
                          >
                            {micEnabled ? <IconMicOn size={14} /> : <IconMicOff size={14} />}
                          </span>
                          <span
                            className={`participant-chip__icon ${camEnabled ? "participant-chip__icon--on" : "participant-chip__icon--off"}`}
                            title={camEnabled ? "Камера включена" : "Камера выключена"}
                          >
                            {camEnabled ? <IconCamOn size={14} /> : <IconCamOff size={14} />}
                          </span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="controls controls--meet">
            <button
              className={`control-btn control-btn--round mic-btn ${micEnabled ? "active" : ""}`}
              onClick={toggleMic}
              type="button"
              title={micEnabled ? "Выключить микрофон" : "Включить микрофон"}
              aria-pressed={micEnabled}
            >
              {micEnabled ? <IconMicOn size={22} /> : <IconMicOff size={22} />}
              <span className="control-btn__label">{micEnabled ? "Микрофон" : "Вкл. микрофон"}</span>
            </button>

            <button
              className={`control-btn control-btn--round cam-btn ${camEnabled ? "active" : ""}`}
              onClick={toggleCam}
              type="button"
              title={camEnabled ? "Выключить камеру" : "Включить камеру"}
              aria-pressed={camEnabled}
            >
              {camEnabled ? <IconCamOn size={22} /> : <IconCamOff size={22} />}
              <span className="control-btn__label">{camEnabled ? "Камера" : "Вкл. камеру"}</span>
            </button>

            <button
              className="control-btn control-btn--round share-btn"
              onClick={startShare}
              type="button"
              title="Демонстрация экрана"
            >
              <IconScreenShare size={22} />
              <span className="control-btn__label">Экран</span>
            </button>

            <button
              className="control-btn control-btn--round control-btn--leave"
              onClick={leaveMeeting}
              type="button"
              title="Покинуть встречу"
            >
              <IconCallEnd size={22} />
              <span className="control-btn__label">Покинуть</span>
            </button>

            {participantRole === "host" && (
              <button className="control-btn control-btn--round end-btn" onClick={endMeeting} type="button" title="Завершить встречу для всех">
                <span className="control-btn__label">Завершить</span>
              </button>
            )}
          </div>
        </div>

        <MeetingTranscriptRail
          lines={transcriptLines}
          asrStatus={lastTextAt ? "Слушаю…" : "Нет речи"}
          chatMessages={chatMessages}
          currentParticipantId={participantId}
          onSendChat={sendChatMessage}
          chatConnected={connected}
          verdictSummary={verdictSummary}
          verdictDetail={verdictDetail}
          verdictOpen={verdictOpen}
          onToggleVerdict={() => setVerdictOpen((v) => !v)}
          participants={Object.values(participants).map((p) => ({
            id: p.id,
            name: p.name,
            isSelf: p.id === participantId,
            micOn: p.id === participantId ? micEnabled : undefined,
            camOn: p.id === participantId ? camEnabled : undefined,
            emotionLabel: p.faceSignalReceived ? `${p.emotion} · ${p.emotionConfidence}%` : undefined,
          }))}
        />
      </div>
    </div>
  );
};

export default VideoMeet;
