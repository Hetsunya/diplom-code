"""Resolve report body (remote NN vs local stub) and build WS payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Literal

from contracts import analysis_envelope
from modules.report.stub_builder import build_stub_report
from observability import incr
from own_nn_client import generate_report

ReportStage = Literal["partial", "final"]


def _is_report_substantial(report: dict[str, Any]) -> bool:
    summary = report.get("summary")
    if isinstance(summary, str) and summary.strip() and summary.strip().lower() != "report generated":
        return True

    fc = report.get("feature_counts")
    if isinstance(fc, dict) and any(isinstance(v, int) and v > 0 for v in fc.values()):
        return True

    participants = report.get("participants")
    if isinstance(participants, list) and len(participants) > 0:
        for p in participants:
            if not isinstance(p, dict):
                continue
            if isinstance(p.get("audio_chunks"), int) and p.get("audio_chunks", 0) > 0:
                return True
            if isinstance(p.get("last_transcript"), str) and p.get("last_transcript", "").strip():
                return True
    fusion = report.get("fusion")
    if isinstance(fusion, dict):
        buckets = fusion.get("buckets")
        if isinstance(buckets, list) and len(buckets) > 0:
            return True
        tbp = fusion.get("trace_ids_by_participant")
        if isinstance(tbp, dict) and any(isinstance(v, list) and len(v) > 0 for v in tbp.values()):
            return True
    return False


def resolve_report_body(
    session_id: int,
    features: list[dict[str, Any]],
    own_url: str,
    config_snapshot: dict[str, Any],
    *,
    stage: str,
    bucket_sec: float,
    sanitize_report_shape: Callable[[Any, int], dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    """
    Returns `(report_body, report_source)` where `report_body` matches the stub shape (+ fusion).

    `sanitize_report_shape` is injected to avoid a circular import with `report_loop`.
    """
    snap = config_snapshot
    stub = build_stub_report(session_id, features, bucket_sec=bucket_sec)
    fusion_meta = stub.get("fusion") if isinstance(stub.get("fusion"), dict) else {}
    remote = generate_report(
        own_url,
        session_id=session_id,
        features=features,
        config_snapshot=snap,
        stage=stage,
        fusion=fusion_meta,
    )
    if isinstance(remote, dict) and remote.get("report"):
        sanitized = sanitize_report_shape(remote.get("report"), session_id=session_id)
        if _is_report_substantial(sanitized):
            out = dict(sanitized)
            if not isinstance(out.get("fusion"), dict) or not out.get("fusion"):
                out["fusion"] = fusion_meta
            incr("report_shape_validated")
            return out, "remote"
        incr("report_remote_empty_fallback")
        return stub, "local_fallback"
    return stub, "local_stub"


def build_report_ws_message(
    *,
    session_id: int,
    report_body: dict[str, Any],
    report_source: str,
    model_ver: str,
    trace_id: str,
    msg_type: Literal["analysis_report_partial", "analysis_report"],
    envelope_stage: ReportStage,
    config_snapshot: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "type": msg_type,
        "session_id": session_id,
        "participant_id": "",
        "payload": {
            **analysis_envelope(
                module="report",
                version=model_ver,
                stage=envelope_stage,
                trace_id=trace_id,
            ),
            "report": report_body,
            "report_source": report_source,
            "model_version": model_ver,
            "generated_at": now,
            "config_snapshot": config_snapshot,
        },
        "timestamp": now,
    }
