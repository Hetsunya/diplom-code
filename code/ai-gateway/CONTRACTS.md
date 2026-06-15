# AI Gateway — WS analysis contracts (v1)

Canonical documentation: [`../docs/ANALYSIS_WS_CONTRACTS.md`](../docs/ANALYSIS_WS_CONTRACTS.md). Индекс всех документов: [`../docs/README.md`](../docs/README.md).

Quick reference:

- All new analytics payloads must include: `module`, `stage`, `trace_id`, `version`.
- Legacy `emotion` type is still supported without those fields.
- Prefer emitting `face_analysis` plus optional `emotion` for UI compatibility.
- **`face_debug`** — отладочный тип для overlays; backend его **не** персистит в БД (см. канонический файл раздел `face_debug`).

Python helpers: `contracts.py` (`build_trace_id`, `analysis_payload`, …).

Stub report extensions (`meeting_summary`, tiles, timelines): см. **`docs/REPORTS_AND_ANALYTICS_STORAGE.md`**.
