"""Local stub report body (multimodal aggregate + fusion meta)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from modules.report.face_behavior import build_face_behavior_summary
from modules.report.windowing import compute_fusion_meta


def _mean(vals: list[float]) -> float | None:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 3)


def _clamp_str(v: Any, *, max_len: int) -> str | None:
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    if len(s) > max_len:
        s = s[:max_len]
    return s


def _top_k_counts(counts: dict[str, int], k: int) -> list[tuple[str, int]]:
    items: list[tuple[str, int]] = []
    for key, val in counts.items():
        if not isinstance(key, str):
            continue
        if isinstance(val, (int, float)):
            items.append((key, int(val)))
    items.sort(key=lambda kv: kv[1], reverse=True)
    return items[: max(0, int(k))]


def build_stub_report(session_id: int, features: list[dict[str, Any]], *, bucket_sec: float = 30.0) -> dict[str, Any]:
    """Aggregate audio / face / text feature rows into the stable stub `report` object."""
    kinds: dict[str, int] = {}
    participants: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "audio_chunks": 0,
            "avg_speech_activity_proxy": None,
            "avg_bitrate_kbps": None,
            "last_emotion": None,
            "last_transcript": None,
        }
    )
    audio_activity_acc: dict[str, list[float]] = defaultdict(list)
    audio_bitrate_acc: dict[str, list[float]] = defaultdict(list)

    # History (bounded): report needs minimal, readable timeline without NN.
    # Keep it small to avoid WS payload bloat and DB storage spikes.
    _MAX_EMO_EVENTS = 30
    _MAX_TEXT_EVENTS = 30
    _MAX_FACE_DBG_EVENTS = 40
    emotion_counts_by_pid: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    emotion_events_by_pid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    text_events_by_pid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    face_dbg_events_by_pid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    face_dbg_totals_by_pid: dict[str, dict[str, int]] = defaultdict(lambda: {"events": 0, "gate_passed": 0})
    face_dbg_skip_reasons: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    # Timelines (bucketed, bounded): per-participant by time window (no NN required).
    _MAX_BUCKETS = 20
    emo_bucket_counts: dict[str, dict[int, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    text_bucket_items: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    total_audio_chunks = 0
    speech_chunks = 0

    for f in features:
        k = f.get("kind") or "unknown"
        if isinstance(k, str):
            kinds[k] = kinds.get(k, 0) + 1
        pid = str(f.get("participant_id") or "unknown")
        data = f.get("data") if isinstance(f.get("data"), dict) else {}

        if k == "audio":
            total_audio_chunks += 1
            participants[pid]["audio_chunks"] += 1
            af = data.get("audio_features") if isinstance(data.get("audio_features"), dict) else {}
            sap = af.get("speech_activity_proxy")
            bitrate = af.get("bitrate_kbps_est")
            if isinstance(sap, (int, float)):
                sapf = float(sap)
                audio_activity_acc[pid].append(sapf)
                if sapf >= 0.35:
                    speech_chunks += 1
            if isinstance(bitrate, (int, float)):
                audio_bitrate_acc[pid].append(float(bitrate))

        elif k == "face":
            ff = data.get("face_features") if isinstance(data.get("face_features"), dict) else {}
            if not ff:
                payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
                ff = payload.get("face_features") if isinstance(payload.get("face_features"), dict) else {}
            if ff.get("face_detected") is False:
                continue
            dom = ff.get("dominant_emotion")
            if isinstance(dom, str) and dom.strip():
                participants[pid]["last_emotion"] = dom
                emotion_counts_by_pid[pid][dom] += 1
                if len(emotion_events_by_pid[pid]) < _MAX_EMO_EVENTS:
                    ts = f.get("ts")
                    confidence = ff.get("confidence")
                    emotion_events_by_pid[pid].append(
                        {
                            "ts": float(ts) if isinstance(ts, (int, float)) else None,
                            "emotion": dom,
                            "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
                        }
                    )
                ts_raw = f.get("ts")
                if bucket_sec > 0 and isinstance(ts_raw, (int, float)):
                    b = int(float(ts_raw) // bucket_sec)
                    emo_bucket_counts[pid][b][dom] += 1

        elif k == "text":
            payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
            transcript = payload.get("transcript_final") or payload.get("transcript_partial")
            t = _clamp_str(transcript, max_len=220)
            if t:
                participants[pid]["last_transcript"] = t[:180]
                if len(text_events_by_pid[pid]) < _MAX_TEXT_EVENTS:
                    ts = f.get("ts")
                    is_final = bool(payload.get("transcript_final"))
                    text_events_by_pid[pid].append(
                        {
                            "ts": float(ts) if isinstance(ts, (int, float)) else None,
                            "text": t,
                            "final": is_final,
                        }
                    )
                ts_raw = f.get("ts")
                if bucket_sec > 0 and isinstance(ts_raw, (int, float)):
                    b = int(float(ts_raw) // bucket_sec)
                    if len(text_bucket_items[pid][b]) < 3:
                        text_bucket_items[pid][b].append(
                            {
                                "text": t,
                                "final": bool(payload.get("transcript_final")),
                            }
                        )
        elif k == "face_debug":
            payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
            gp = payload.get("gate_passed") is True
            sr = payload.get("skip_reason")
            face_dbg_totals_by_pid[pid]["events"] += 1
            if gp:
                face_dbg_totals_by_pid[pid]["gate_passed"] += 1
            if isinstance(sr, str) and sr.strip():
                face_dbg_skip_reasons[pid][sr.strip()] += 1
            if len(face_dbg_events_by_pid[pid]) < _MAX_FACE_DBG_EVENTS:
                ts = f.get("ts")
                region = payload.get("region") if isinstance(payload.get("region"), dict) else None
                face_dbg_events_by_pid[pid].append(
                    {
                        "ts": float(ts) if isinstance(ts, (int, float)) else None,
                        "gate_passed": gp,
                        "skip_reason": sr if isinstance(sr, str) else None,
                        "region": region,
                        "landmarks_n": int(payload.get("landmarks_n", 0))
                        if isinstance(payload.get("landmarks_n"), (int, float))
                        else 0,
                        "dominant_emotion": payload.get("dominant_emotion")
                        if isinstance(payload.get("dominant_emotion"), str)
                        else None,
                        "model_confidence": float(payload.get("model_confidence"))
                        if isinstance(payload.get("model_confidence"), (int, float))
                        else None,
                    }
                )

    for pid, p in participants.items():
        p["avg_speech_activity_proxy"] = _mean(audio_activity_acc[pid])
        p["avg_bitrate_kbps"] = _mean(audio_bitrate_acc[pid])

    talk_ratio = 0.0
    if total_audio_chunks > 0:
        talk_ratio = round(speech_chunks / total_audio_chunks, 3)

    if kinds.get("text", 0) > 0:
        stage_label = "transcribing"
    elif total_audio_chunks > 0:
        stage_label = "listening"
    elif kinds.get("face", 0) > 0:
        stage_label = "visual_only"
    else:
        stage_label = "idle"

    summary = (
        f"pipeline={stage_label}; audio_chunks={total_audio_chunks}; "
        f"text_events={kinds.get('text', 0)}; face_events={kinds.get('face', 0)}; "
        f"speech_ratio={talk_ratio}"
    )

    report: dict[str, Any] = {
        "session_id": session_id,
        "summary": summary,
        "pipeline_stage": stage_label,
        "speech_ratio": talk_ratio,
        "feature_counts": kinds,
        "participants": [
            {"participant_id": pid, **pdata}
            for pid, pdata in sorted(participants.items(), key=lambda kv: kv[1]["audio_chunks"], reverse=True)
        ],
    }

    # Lightweight history extensions (stub-only; safe to ignore in older UI).
    report["emotion_summary"] = {
        "by_participant": {
            pid: {
                "events": sum(int(v) for v in counts.values()),
                "counts": dict(counts),
                "recent": emotion_events_by_pid.get(pid, []),
            }
            for pid, counts in emotion_counts_by_pid.items()
        }
    }
    report["transcript_summary"] = {
        "by_participant": {
            pid: {
                "events": len(text_events_by_pid.get(pid, [])),
                "recent": text_events_by_pid.get(pid, []),
            }
            for pid in text_events_by_pid.keys()
        }
    }
    face_behavior_summary = build_face_behavior_summary(features)
    if face_behavior_summary is not None:
        report["face_behavior_summary"] = face_behavior_summary

    # Face tracking summary (from `face_debug` history).
    if face_dbg_totals_by_pid:
        by_pid = {}
        totals_events = 0
        totals_gate = 0
        guard_reasons_total: dict[str, int] = defaultdict(int)
        for pid, t in face_dbg_totals_by_pid.items():
            ev = int(t.get("events", 0))
            gp = int(t.get("gate_passed", 0))
            totals_events += ev
            totals_gate += gp
            reasons = dict(face_dbg_skip_reasons.get(pid, {}))
            for rk, rv in reasons.items():
                guard_reasons_total[rk] += int(rv)
            by_pid[pid] = {
                "events": ev,
                "gate_passed_events": gp,
                "gate_passed_ratio": round(gp / ev, 3) if ev > 0 else 0.0,
                "skip_reasons": reasons,
                "recent": face_dbg_events_by_pid.get(pid, []),
            }
        report["face_tracking_summary"] = {
            "events": totals_events,
            "gate_passed_events": totals_gate,
            "gate_passed_ratio": round(totals_gate / totals_events, 3) if totals_events > 0 else 0.0,
            "skip_reasons": dict(guard_reasons_total),
            "by_participant": by_pid,
        }

    # Timelines: per-participant, last N buckets.
    if bucket_sec > 0 and (emo_bucket_counts or text_bucket_items):
        tl_by_pid: dict[str, Any] = {}
        all_pids = sorted(set(list(emo_bucket_counts.keys()) + list(text_bucket_items.keys())))
        for pid in all_pids:
            emo_rows: list[dict[str, Any]] = []
            for b, counts in emo_bucket_counts.get(pid, {}).items():
                if not counts:
                    continue
                top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[0][0]
                emo_rows.append(
                    {
                        "bucket_index": b,
                        "bucket_start_ts": round(b * bucket_sec, 3),
                        "top_emotion": top,
                        "counts": dict(counts),
                    }
                )
            emo_rows.sort(key=lambda r: r["bucket_index"])
            if len(emo_rows) > _MAX_BUCKETS:
                emo_rows = emo_rows[-_MAX_BUCKETS:]

            txt_rows: list[dict[str, Any]] = []
            for b, items in text_bucket_items.get(pid, {}).items():
                if not items:
                    continue
                txt_rows.append(
                    {
                        "bucket_index": b,
                        "bucket_start_ts": round(b * bucket_sec, 3),
                        "items": items[-3:],
                    }
                )
            txt_rows.sort(key=lambda r: r["bucket_index"])
            if len(txt_rows) > _MAX_BUCKETS:
                txt_rows = txt_rows[-_MAX_BUCKETS:]

            if emo_rows or txt_rows:
                tl_by_pid[pid] = {"emotion": emo_rows, "transcript": txt_rows}
        if tl_by_pid:
            report["timelines"] = {"bucket_sec": round(float(bucket_sec), 3), "by_participant": tl_by_pid}

    # Observations (rule-based, non-NN): keep UI useful until own NN is ready.
    obs: list[str] = []
    global_counts: dict[str, int] = defaultdict(int)
    for _, counts in emotion_counts_by_pid.items():
        for em, c in counts.items():
            global_counts[em] += int(c)
    if global_counts:
        top_em, top_c = sorted(global_counts.items(), key=lambda kv: kv[1], reverse=True)[0]
        obs.append(f"top_emotion={top_em} (events={top_c})")
    if kinds.get("text", 0) == 0:
        obs.append("no_transcript_events")
    fts = report.get("face_tracking_summary") if isinstance(report.get("face_tracking_summary"), dict) else None
    if isinstance(fts, dict):
        gpr = fts.get("gate_passed_ratio")
        if isinstance(gpr, (int, float)):
            obs.append(f"face_tracking_gate_passed_ratio={round(float(gpr), 3)}")
        sr = fts.get("skip_reasons")
        if isinstance(sr, dict) and sr:
            top_sr = sorted(sr.items(), key=lambda kv: kv[1], reverse=True)[0][0]
            obs.append(f"top_face_skip_reason={top_sr}")
    report["observations"] = obs

    # Participant tiles: compact per-participant summary for UI (no NN).
    tiles: list[dict[str, Any]] = []
    fts = report.get("face_tracking_summary") if isinstance(report.get("face_tracking_summary"), dict) else {}
    fts_by_pid = fts.get("by_participant") if isinstance(fts, dict) else None
    fts_by_pid = fts_by_pid if isinstance(fts_by_pid, dict) else {}

    for pid in sorted(participants.keys()):
        emo_counts = dict(emotion_counts_by_pid.get(pid, {}))
        top = _top_k_counts(emo_counts, 1)
        top_emotion = top[0][0] if top else None
        top_emotion_events = int(top[0][1]) if top else 0
        emo_total = sum(int(v) for v in emo_counts.values()) if emo_counts else 0
        top_ratio = round(top_emotion_events / emo_total, 3) if emo_total > 0 else 0.0

        txt_events = len(text_events_by_pid.get(pid, []))
        p_row = participants.get(pid) or {}
        audio_chunks = int(p_row.get("audio_chunks") or 0) if isinstance(p_row.get("audio_chunks"), (int, float)) else 0
        speech_avg = p_row.get("avg_speech_activity_proxy")
        speech_avg_f = round(float(speech_avg), 3) if isinstance(speech_avg, (int, float)) else None

        face_dbg = fts_by_pid.get(pid) if isinstance(fts_by_pid, dict) else None
        face_gate_ratio = None
        face_skip_reasons = None
        if isinstance(face_dbg, dict):
            gpr = face_dbg.get("gate_passed_ratio")
            if isinstance(gpr, (int, float)):
                face_gate_ratio = round(float(gpr), 3)
            sr = face_dbg.get("skip_reasons")
            if isinstance(sr, dict):
                face_skip_reasons = {
                    str(k): int(v) for k, v in sr.items() if isinstance(k, str) and isinstance(v, (int, float))
                }

        tiles.append(
            {
                "participant_id": pid,
                "emotion": {
                    "events": emo_total,
                    "top": top_emotion,
                    "top_ratio": top_ratio,
                    "top3": _top_k_counts(emo_counts, 3),
                },
                "transcript_events": int(txt_events),
                "audio": {"chunks": audio_chunks, "avg_speech_activity_proxy": speech_avg_f},
                "face_tracking": {"gate_passed_ratio": face_gate_ratio, "skip_reasons": face_skip_reasons},
            }
        )
    if tiles:
        report["participant_tiles"] = tiles

    # Meeting-level rollup for UI + tests (see tests/test_report_windowing.py).
    global_emo: dict[str, int] = defaultdict(int)
    for _, ec in emotion_counts_by_pid.items():
        for em, c in ec.items():
            global_emo[str(em)] += int(c)
    total_emo_events = sum(global_emo.values())
    emotion_distribution_top: list[dict[str, Any]] = []
    for em, cnt in _top_k_counts(dict(global_emo), 8):
        emotion_distribution_top.append(
            {
                "emotion": em,
                "events": cnt,
                "share": round(cnt / total_emo_events, 3) if total_emo_events > 0 else 0.0,
            }
        )

    meeting_summary: dict[str, Any] = {
        "session_id": session_id,
        "participant_count": len(participants),
        "emotion_distribution_top": emotion_distribution_top,
        "pipeline_stage": stage_label,
        "speech_ratio": talk_ratio,
        "feature_totals": dict(kinds),
        "highlights_ru": [],
    }

    if tiles:
        verbal_sorted = sorted(
            tiles,
            key=lambda t: (
                int(t.get("transcript_events") or 0),
                int(((t.get("audio") or {}).get("chunks") or 0)),
            ),
            reverse=True,
        )
        mv = verbal_sorted[0]
        meeting_summary["most_verbal_participant"] = {
            "participant_id": mv.get("participant_id"),
            "transcript_events": int(mv.get("transcript_events") or 0),
            "audio_chunks": int(((mv.get("audio") or {}).get("chunks") or 0)),
        }
        if len(verbal_sorted) > 1:
            q = verbal_sorted[-1]
            meeting_summary["least_verbal_participant"] = {
                "participant_id": q.get("participant_id"),
                "transcript_events": int(q.get("transcript_events") or 0),
                "audio_chunks": int(((q.get("audio") or {}).get("chunks") or 0)),
            }

        face_rank: list[tuple[float, dict[str, Any]]] = []
        for t in tiles:
            ft = t.get("face_tracking") if isinstance(t.get("face_tracking"), dict) else {}
            gpr = ft.get("gate_passed_ratio") if isinstance(ft, dict) else None
            if isinstance(gpr, (int, float)):
                face_rank.append((float(gpr), t))
        if face_rank:
            weakest = min(face_rank, key=lambda x: x[0])[1]
            strongest = max(face_rank, key=lambda x: x[0])[1]
            meeting_summary["weakest_face_tracking"] = {
                "participant_id": weakest.get("participant_id"),
                "gate_passed_ratio": (weakest.get("face_tracking") or {}).get("gate_passed_ratio"),
            }
            meeting_summary["strongest_face_tracking"] = {
                "participant_id": strongest.get("participant_id"),
                "gate_passed_ratio": (strongest.get("face_tracking") or {}).get("gate_passed_ratio"),
            }

    participation_rank: list[dict[str, Any]] = []
    for t in tiles:
        pid = str(t.get("participant_id") or "unknown")
        te = int(t.get("transcript_events") or 0)
        ac = int(((t.get("audio") or {}).get("chunks") or 0))
        emo = t.get("emotion") if isinstance(t.get("emotion"), dict) else {}
        ee = int(emo.get("events") or 0)
        score = round(float(te) * 2.0 + float(ac) * 0.12 + float(ee) * 0.35, 2)
        participation_rank.append({"participant_id": pid, "participation_score": score})
    participation_rank.sort(key=lambda r: float(r.get("participation_score") or 0.0), reverse=True)

    hl_ru: list[str] = []
    if emotion_distribution_top:
        top = emotion_distribution_top[0]
        hl_ru.append(
            f"По встрече чаще всего фиксировалась эмоция «{top['emotion']}» "
            f"({top['events']} событий, ~{int(round(float(top['share']) * 100))}% от всех эмоций)."
        )
    mv2 = meeting_summary.get("most_verbal_participant")
    if isinstance(mv2, dict) and mv2.get("participant_id"):
        hl_ru.append(
            f"Больше всего текстовых событий ASR у участника {mv2['participant_id']} "
            f"({int(mv2.get('transcript_events') or 0)})."
        )
    wf = meeting_summary.get("weakest_face_tracking")
    if isinstance(wf, dict) and wf.get("participant_id") is not None:
        gpr_w = wf.get("gate_passed_ratio")
        pct = int(round(float(gpr_w) * 100)) if isinstance(gpr_w, (int, float)) else None
        if pct is not None:
            hl_ru.append(
                f"Сложнее всего удерживать качество трекинга лица у {wf['participant_id']} "
                f"(gate passed ~{pct}%)."
            )
    if kinds.get("text", 0) == 0:
        hl_ru.append("Транскрипт не поступал — проверьте модуль speech и аудио-поток.")
    if kinds.get("face_debug", 0) == 0 and kinds.get("face", 0) > 0:
        hl_ru.append(
            "Для детального трекинга включите emit_debug_face в настройках face-модуля."
        )
    meeting_summary["highlights_ru"] = hl_ru
    meeting_summary["participation_rank"] = participation_rank
    meeting_summary["coverage"] = {
        "audio_events": int(kinds.get("audio", 0)),
        "text_events": int(kinds.get("text", 0)),
        "face_events": int(kinds.get("face", 0)),
        "face_debug_events": int(kinds.get("face_debug", 0)),
    }

    report["meeting_summary"] = meeting_summary

    report["fusion"] = compute_fusion_meta(features, bucket_sec)
    return report
