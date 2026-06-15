# Analysis pipeline — observability & SLO hints

## ai-gateway

- **Logs**: `observability.log_event(event, trace_id=..., module=..., extra=...)`.
- **Counters**: `observability.incr("metric_name")` — use `snapshot_metrics()` for periodic dumps or health.
- **Latency rings**: `observe_module_latency("face"|"audio", ms)` — summarized via `snapshot_health()` (`p95_ms`, `max_ms`, `avg_ms` over last 256 samples per module).
- **Correlation**: every v1 outbound message should include `payload.trace_id` (UUID). Propagate the same `trace_id` when a module chains work (e.g. audio chunk → speech-service → `text_analysis`).
- **Report latency**: wrap ML / HTTP calls with `t0 = monotonic_ms()` and log `latency_ms` on completion (see `report_loop`).
- **Hot-reload modules JSON**: mount `AI_GATEWAY_MODULES_CONFIG` (e.g. `/app/modules.docker.json`) and set **`AI_GATEWAY_CONFIG_POLL_SEC`** (default `10` in prod compose; use `0` to disable). On file **mtime** change, gateway reloads module flags/params **without** restarting the process (`handlers.handle_message` polls).
- **Heavy modules**: Face inference runs under **`max_concurrent_inferences`** (default `2`) via `asyncio.Semaphore` + `asyncio.to_thread` so frames don’t pile unbounded synchronous GPU/CPU work on one thread.
- **MediaPipe (optional)**: on landmarker failures the gateway increments **`face_mediapipe_errors`** and emits **`face_mediapipe_failed`** via `log_event` — учитывать при алертинге и при диагностике Docker (EGL/GLES, см. `ai-gateway/Dockerfile`).
- **Degraded pipeline visibility**: each `analysis_report_partial` / final `analysis_report` includes **`report.data_quality`**: `complete`, `degraded_sources` (`text_asr`, `face_inference`, …), `notes`, `counters_window` (counter deltas since the previous report tick). Derived from `speech_service_circuit_open`, `text_analysis_errors`, `face_inference_errors`, etc.

## Suggested SLO targets (tune per deployment)

| Stage | Target | Notes |
|-------|--------|-------|
| `face_analysis` partial | \< 500 ms p95 | depends on DeepFace / GPU; watch `snapshot_health().latency_ms.face` |
| `audio_analysis` partial | \< 100 ms p95 | DSP-only baseline |
| `text_analysis` partial | \< 2 s p95 | ASR network + model |
| `analysis_report_partial` | interval-based | `interval_sec` + `report_wake_floor_sec` |
| End-to-end final report | post-meeting async | own NN `POST /v1/report` timeout default 60 s |

## emeeting-backend

- Persist failures are logged as `[ANALYSIS] validate skipped store: ...` (invalid v1 payload) without closing the WS.
- REST: use `GET /sessions/:id/analysis/events` for debugging timelines.
