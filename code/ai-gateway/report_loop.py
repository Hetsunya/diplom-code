"""Periodic hybrid partial reports + final report on disconnect; delegates to `modules/report/`."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from contracts import build_trace_id
from feature_store import get_feature_store
from gateway_config import config_snapshot, get_gateway_config
from modules.report.data_quality import augment_report_data_quality
from modules.report.orchestrator import build_report_ws_message, resolve_report_body
from modules.report.stub_builder import build_stub_report
from modules.shared.session_modules import is_module_enabled_for_session
from observability import incr, log_event, monotonic_ms, snapshot_metrics

# Backwards compatibility for tests importing `_stub_report`.
_stub_report = build_stub_report

_PIPELINE_STAGES = {"idle", "listening", "transcribing", "visual_only"}

# Passthrough keys for stub / multimodal UI (remote NN may omit them).
_REPORT_SHAPE_EXTENSIONS: tuple[tuple[str, type], ...] = (
    ("emotion_summary", dict),
    ("transcript_summary", dict),
    ("face_tracking_summary", dict),
    ("timelines", dict),
    ("observations", list),
    ("participant_tiles", list),
    ("meeting_summary", dict),
)

_REPORT_QUALITY_PREV: dict[str, int] | None = None


def _to_non_empty_str(v: Any, default: str) -> str:
    if isinstance(v, str) and v.strip():
        return v.strip()
    return default


def _to_float(v: Any, default: float, *, lo: float | None = None, hi: float | None = None) -> float:
    if isinstance(v, (int, float)):
        out = float(v)
        if lo is not None and out < lo:
            out = lo
        if hi is not None and out > hi:
            out = hi
        return round(out, 3)
    return default


def _sanitize_feature_counts(v: Any) -> dict[str, int]:
    if not isinstance(v, dict):
        return {}
    out: dict[str, int] = {}
    for k, val in v.items():
        if not isinstance(k, str):
            continue
        if isinstance(val, (int, float)):
            out[k] = max(0, int(val))
    return out


def _sanitize_participants(v: Any) -> list[dict[str, Any]]:
    if not isinstance(v, list):
        return []
    out: list[dict[str, Any]] = []
    for raw in v:
        if not isinstance(raw, dict):
            continue
        pid = _to_non_empty_str(raw.get("participant_id"), "unknown")
        item = {
            "participant_id": pid,
            "audio_chunks": int(_to_float(raw.get("audio_chunks"), 0.0, lo=0)),
            "avg_speech_activity_proxy": _to_float(raw.get("avg_speech_activity_proxy"), 0.0, lo=0.0, hi=1.0),
            "avg_bitrate_kbps": _to_float(raw.get("avg_bitrate_kbps"), 0.0, lo=0.0),
            "last_emotion": _to_non_empty_str(raw.get("last_emotion"), ""),
            "last_transcript": _to_non_empty_str(raw.get("last_transcript"), "")[:180],
        }
        out.append(item)
    return out


def _sanitize_fusion(v: Any) -> dict[str, Any] | None:
    if not isinstance(v, dict):
        return None
    out: dict[str, Any] = {}
    bs = v.get("bucket_sec")
    if isinstance(bs, (int, float)):
        out["bucket_sec"] = round(float(bs), 3)
    tbp = v.get("trace_ids_by_participant")
    if isinstance(tbp, dict):
        clean: dict[str, list[str]] = {}
        for pk, pv in tbp.items():
            if not isinstance(pk, str):
                continue
            if isinstance(pv, list):
                clean[pk] = [str(x) for x in pv if isinstance(x, str)]
        out["trace_ids_by_participant"] = clean
    buckets = v.get("buckets")
    if isinstance(buckets, list):
        out_buckets: list[dict[str, Any]] = []
        for b in buckets:
            if not isinstance(b, dict):
                continue
            entry: dict[str, Any] = {}
            for key in ("participant_id", "bucket_index", "bucket_start_ts"):
                if key in b:
                    entry[key] = b[key]
            km = b.get("kinds")
            if isinstance(km, dict):
                entry["kinds"] = {str(k): int(v2) for k, v2 in km.items() if isinstance(v2, (int, float))}
            tr = b.get("trace_ids")
            if isinstance(tr, list):
                entry["trace_ids"] = [str(x) for x in tr if isinstance(x, str)]
            if entry:
                out_buckets.append(entry)
        out["buckets"] = out_buckets
    return out if out else None


def _sanitize_face_behavior_summary(v: Any) -> dict[str, Any] | None:
    if not isinstance(v, dict):
        return None
    events = v.get("events")
    trackable_events = v.get("trackable_events")
    trackable_ratio = v.get("trackable_ratio")
    if not isinstance(events, (int, float)) or not isinstance(trackable_events, (int, float)):
        return None
    out: dict[str, Any] = {
        "events": int(max(0, events)),
        "trackable_events": int(max(0, trackable_events)),
        "trackable_ratio": _to_float(trackable_ratio, 0.0, lo=0.0, hi=1.0),
    }
    reasons = v.get("guard_reasons")
    if isinstance(reasons, dict):
        out["guard_reasons"] = {
            str(k): int(val) for k, val in reasons.items() if isinstance(k, str) and isinstance(val, (int, float))
        }
    participants = v.get("participants")
    if isinstance(participants, list):
        out_p: list[dict[str, Any]] = []
        for p in participants:
            if not isinstance(p, dict):
                continue
            pid = p.get("participant_id")
            if not isinstance(pid, str) or not pid.strip():
                continue
            out_p.append(
                {
                    "participant_id": pid,
                    "events": int(_to_float(p.get("events"), 0.0, lo=0.0)),
                    "trackable_events": int(_to_float(p.get("trackable_events"), 0.0, lo=0.0)),
                    "trackable_ratio": _to_float(p.get("trackable_ratio"), 0.0, lo=0.0, hi=1.0),
                    "avg_engagement_proxy": _to_float(p.get("avg_engagement_proxy"), 0.0, lo=0.0, hi=1.0),
                }
            )
        out["participants"] = out_p
    return out


def sanitize_report_shape(raw: Any, *, session_id: int) -> dict[str, Any]:
    """
    Keep report JSON shape stable for UI regardless of remote model output.
    Unknown fields are dropped in this baseline implementation.
    """
    if not isinstance(raw, dict):
        return build_stub_report(session_id, [], bucket_sec=30.0)

    stage = _to_non_empty_str(raw.get("pipeline_stage"), "idle")
    if stage not in _PIPELINE_STAGES:
        stage = "idle"

    out: dict[str, Any] = {
        "session_id": int(_to_float(raw.get("session_id"), float(session_id), lo=0)),
        "summary": _to_non_empty_str(raw.get("summary"), "report generated"),
        "pipeline_stage": stage,
        "speech_ratio": _to_float(raw.get("speech_ratio"), 0.0, lo=0.0, hi=1.0),
        "feature_counts": _sanitize_feature_counts(raw.get("feature_counts")),
        "participants": _sanitize_participants(raw.get("participants")),
    }
    fusion = _sanitize_fusion(raw.get("fusion"))
    if fusion is not None:
        out["fusion"] = fusion
    fbs = _sanitize_face_behavior_summary(raw.get("face_behavior_summary"))
    if fbs is not None:
        out["face_behavior_summary"] = fbs
    dq = _sanitize_data_quality(raw.get("data_quality"))
    if dq is not None:
        out["data_quality"] = dq
    for key, typ in _REPORT_SHAPE_EXTENSIONS:
        val = raw.get(key)
        if isinstance(val, typ):
            out[key] = val
    return out


def _sanitize_data_quality(v: Any) -> dict[str, Any] | None:
    if not isinstance(v, dict):
        return None
    complete = bool(v.get("complete"))
    ds = v.get("degraded_sources")
    degraded = [str(x) for x in ds] if isinstance(ds, list) else []
    notes_raw = v.get("notes")
    notes = [str(x) for x in notes_raw] if isinstance(notes_raw, list) else []
    cw = v.get("counters_window")
    counters: dict[str, int] = {}
    if isinstance(cw, dict):
        for k, val in cw.items():
            if isinstance(k, str) and isinstance(val, (int, float)):
                counters[k] = int(val)
    return {
        "complete": complete,
        "degraded_sources": degraded,
        "notes": notes,
        "counters_window": counters,
    }


async def _send_report(
    ws: Any,
    *,
    session_id: int,
    feats: list[dict[str, Any]],
    own_url: str,
    model_ver: str,
    bucket_sec: float,
    msg_type: str,
    envelope_stage: str,
) -> None:
    global _REPORT_QUALITY_PREV
    if ws is None or not getattr(ws, "open", True):
        return
    t0 = monotonic_ms()
    trace = build_trace_id()
    snap = config_snapshot()
    report_body, report_source = resolve_report_body(
        session_id,
        feats,
        own_url,
        snap,
        stage=envelope_stage,
        bucket_sec=bucket_sec,
        sanitize_report_shape=sanitize_report_shape,
    )
    curr_metrics = snapshot_metrics()
    report_body = augment_report_data_quality(report_body, curr_metrics, _REPORT_QUALITY_PREV)
    _REPORT_QUALITY_PREV = dict(curr_metrics)
    out = build_report_ws_message(
        session_id=session_id,
        report_body=report_body,
        report_source=report_source,
        model_ver=model_ver,
        trace_id=trace,
        msg_type=msg_type,  # type: ignore[arg-type]
        envelope_stage=envelope_stage,  # type: ignore[arg-type]
        config_snapshot=snap,
    )
    try:
        await ws.send(json.dumps(out))
        if msg_type == "analysis_report_partial":
            incr("report_partial_sent")
            log_event(
                "report_partial",
                trace_id=trace,
                module="report",
                extra={"latency_ms": round(monotonic_ms() - t0, 2)},
            )
        else:
            incr("report_final_sent")
            log_event(
                "report_final",
                trace_id=trace,
                module="report",
                extra={"latency_ms": round(monotonic_ms() - t0, 2)},
            )
    except Exception as e:
        if msg_type == "analysis_report_partial":
            incr("report_partial_errors")
            log_event("report_partial_failed", extra={"error": str(e)})
        else:
            incr("report_final_errors")
            log_event("report_final_failed", extra={"error": str(e)})


async def report_loop(ws_holder: list[Any], session_id: int) -> None:
    """ws_holder[0] is the active websocket client protocol (mutated by SessionWSClient)."""
    cfg = get_gateway_config()
    mod = cfg.module("report")
    if not mod or not mod.enabled:
        return
    interval = float(mod.params.get("interval_sec", 30))
    own_url = str(mod.params.get("own_nn_url", "") or "")
    model_ver = mod.model or "report-v1"
    bucket_sec = float(mod.params.get("report_bucket_sec", 30.0))
    wake_floor = float(mod.params.get("report_wake_floor_sec", 5.0))

    try:
        while True:
            await asyncio.sleep(max(interval, wake_floor))
            ws = ws_holder[0] if ws_holder else None
            store = get_feature_store()
            targets = [session_id] if session_id > 0 else store.session_ids()
            for sid in targets:
                if not is_module_enabled_for_session(int(sid), "report"):
                    continue
                feats = store.snapshot_session(sid)
                await _send_report(
                    ws,
                    session_id=sid,
                    feats=feats,
                    own_url=own_url,
                    model_ver=model_ver,
                    bucket_sec=bucket_sec,
                    msg_type="analysis_report_partial",
                    envelope_stage="partial",
                )
    except asyncio.CancelledError:
        ws = ws_holder[0] if ws_holder else None
        store = get_feature_store()
        targets = [session_id] if session_id > 0 else store.session_ids()
        for sid in targets:
            if not is_module_enabled_for_session(int(sid), "report"):
                continue
            feats = store.snapshot_session(sid)
            await _send_report(
                ws,
                session_id=sid,
                feats=feats,
                own_url=own_url,
                model_ver=model_ver,
                bucket_sec=bucket_sec,
                msg_type="analysis_report",
                envelope_stage="final",
            )
        raise
