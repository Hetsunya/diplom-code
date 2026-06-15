"""WS `type: audio` → optional `audio_analysis` + optional `text_analysis` (ASR)."""

from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from typing import Any

from contracts import analysis_envelope, build_trace_id, has_required_envelope_fields
from feature_store import get_feature_store
from gateway_config import get_gateway_config
from modules.audio.signal import extract_audio_features_safe
from modules.shared.session_modules import is_module_enabled_for_session
from modules.text.transcription import transcribe_and_emit_text_analysis
from observability import incr, monotonic_ms, observe_module_latency


class AudioPipelinePlugin:
    name = "audio"
    priority = 150

    def __init__(self) -> None:
        self._last_chunk_mono_ms: dict[str, float] = {}
        self._iat_ms: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=12))
        self._rms_hist: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=8))

    def metadata(self) -> dict[str, str]:
        cfg = get_gateway_config()
        m = cfg.module("audio")
        return {
            "module": self.name,
            "provider": (m.provider if m else ""),
            "model": (m.model if m else ""),
            "version": (m.model if m else "audio-features-v2"),
        }

    def can_handle(self, msg: dict[str, Any]) -> bool:
        return msg.get("type") == "audio"

    async def process(self, msg: dict[str, Any], ws: Any) -> None:
        cfg = get_gateway_config()
        audio_mod = cfg.module("audio")
        text_mod = cfg.module("text")

        session_id = msg.get("session_id")
        participant_id = msg.get("participant_id")
        if session_id is None or not participant_id:
            return

        trace_id = build_trace_id()
        ts = msg.get("timestamp")
        payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}

        if audio_mod and audio_mod.enabled and is_module_enabled_for_session(int(session_id), "audio"):
            t_audio = monotonic_ms()
            audio_ver = audio_mod.model or "audio-features-v2"
            params = audio_mod.params or {}
            key = f"{session_id}:{participant_id}"
            now_ms = time.monotonic() * 1000.0
            last_ms = self._last_chunk_mono_ms.get(key)
            inter_arrival = None if last_ms is None else (now_ms - last_ms)
            self._last_chunk_mono_ms[key] = now_ms
            if inter_arrival is not None:
                self._iat_ms[key].append(inter_arrival)
            ts_ms = payload.get("timeslice_ms")
            duration_override = float(ts_ms) if isinstance(ts_ms, (int, float)) and ts_ms > 0 else None
            prev_rms = list(self._rms_hist[key])
            audio_features = extract_audio_features_safe(
                payload,
                params,
                inter_arrival_ms=inter_arrival,
                duration_ms_override=duration_override,
                iat_history_ms=list(self._iat_ms[key]),
                rms_history_for_shimmer=prev_rms if prev_rms else None,
            )
            er = audio_features.get("energy_rms_norm")
            if isinstance(er, (int, float)):
                self._rms_hist[key].append(float(er))
            if audio_features.get("degraded"):
                incr("audio_features_degraded")
            audio_out = {
                "type": "audio_analysis",
                "session_id": session_id,
                "participant_id": participant_id,
                "payload": {
                    **analysis_envelope(
                        module="audio",
                        version=audio_ver,
                        stage="partial",
                        trace_id=trace_id,
                    ),
                    "audio_features": audio_features,
                },
                "timestamp": ts,
            }
            if not has_required_envelope_fields(audio_out["payload"]):
                incr("audio_contract_invalid")
            else:
                await ws.send(json.dumps(audio_out))
                get_feature_store().push(
                    int(session_id),
                    kind="audio",
                    participant_id=str(participant_id),
                    trace_id=trace_id,
                    data={"audio_features": audio_features},
                )
                incr("audio_analysis_sent")
                observe_module_latency("audio", monotonic_ms() - t_audio)

        if not text_mod or not text_mod.enabled:
            return
        if not is_module_enabled_for_session(int(session_id), "text"):
            return

        await transcribe_and_emit_text_analysis(
            msg=msg,
            ws=ws,
            text_mod=text_mod,
            trace_id=trace_id,
        )


plugin = AudioPipelinePlugin()
