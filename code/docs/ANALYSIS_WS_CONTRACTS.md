# Analysis WebSocket contracts (v1)

All analysis-related messages use the shared envelope compatible with `emeeting-backend` `WSMessage`:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Event type (see below) |
| `session_id` | number | Meeting session id |
| `participant_id` | string | Optional participant key |
| `payload` | object | Type-specific body |
| `timestamp` | RFC3339 string | Event time (may be propagated from source) |

## Envelope fields inside `payload` (required for new analytics types)

Legacy `emotion` events are exempt.

| Field | Type | Description |
|-------|------|-------------|
| `module` | `text` \| `audio` \| `face` \| `report` | Source module |
| `stage` | `partial` \| `final` | Hybrid pipeline stage |
| `trace_id` | string | Correlation id across modules |
| `version` | string | Model / algorithm version |

## Event types

### `text_analysis`

ASR + NLP (produced by speech pipeline / `ai-gateway` after speech-service).

`payload` extensions:

- `transcript_partial` (string, optional)
- `transcript_final` (string, optional)
- `language` (string, optional)
- `text_features` (object, optional): e.g. `sentiment`, `topics`, `confidence`

### `audio_analysis`

Low-level voice / prosody features (not raw transcript).

- `audio_features` (object): energy, tempo, pause_ratio, etc.

### `face_analysis`

Facial emotion / presence.

- `face_features` (object): `dominant_emotion`, `probs`, `face_detected`, `confidence`
- optional `guard_reason` when `face_detected` is false (e.g. `no_face`) — UI should ignore emotion fields

#### `face.behavior` extension draft (v1)

Advanced behavior tracking should stay inside `face_analysis.payload` (same WS `type`) and be
attached as an optional nested object `face_behavior`.

Design goals:

- keep backward compatibility for current UI (`face_features` stays unchanged),
- allow separate feature flags for `face.emotion` and `face.behavior`,
- provide report-friendly signals (engagement / attention / fatigue) with explicit quality flags.

Recommended shape:

- `face_behavior.schema_version` (string, required): contract version, e.g. `"face_behavior.v1"`
- `face_behavior.provider` (string, required): detector backend, e.g. `"mediapipe_face_landmarker"`
- `face_behavior.face_count` (number, required): detected faces in frame (`0..N`)
- `face_behavior.blendshapes` (object, optional): normalized `[0..1]` coefficients
  - canonical keys for v1 (subset):
    - `smile`
    - `jaw_open`
    - `eye_closed_left`
    - `eye_closed_right`
    - `brow_inner_up`
    - `mouth_pucker`
- `face_behavior.head_pose` (object, optional): head orientation
  - `yaw_deg` (number)
  - `pitch_deg` (number)
  - `roll_deg` (number)
  - `transform_matrix` (`number[]`, optional, 16 values)
- `face_behavior.eye_state` (object, optional):
  - `left_closed_prob` (number `[0..1]`)
  - `right_closed_prob` (number `[0..1]`)
  - `blink_detected` (boolean)
- `face_behavior.engagement_proxy` (number, optional): normalized proxy score `[0..1]`
- `face_behavior.quality` (object, required):
  - `trackable` (boolean): whether downstream should use this event in report fusion
  - `guard_reason` (string, optional): e.g. `no_face`, `face_too_small`, `blurred_frame`, `low_light`
  - `frame_laplacian_var` (number, optional)
  - `min_face_side_px` (number, optional)
  - `confidence` (number, optional)

Suggested rules for producers:

- if `quality.trackable=false`, still emit `face_behavior` with `guard_reason` for observability;
- use only normalized numeric ranges in v1 (no model-specific raw scales);
- always include `schema_version`, `provider`, `face_count`, `quality`.

Suggested rules for consumers (UI/report):

- UI live tile can ignore `face_behavior` when absent;
- report fusion should include only events where `quality.trackable=true`;
- when `trackable=false`, count reason under data quality metrics (not as neutral signal).

Example payload fragment:

```json
{
  "module": "face",
  "version": "mediapipe-0.10-face-landmarker-v1",
  "stage": "partial",
  "trace_id": "8f730f2c-3b34-4982-9f7d-7a4e8c675d2b",
  "face_features": {
    "dominant_emotion": "happy",
    "probs": { "happy": 0.71, "neutral": 0.19, "surprise": 0.06 },
    "face_detected": true,
    "confidence": 0.71
  },
  "face_behavior": {
    "schema_version": "face_behavior.v1",
    "provider": "mediapipe_face_landmarker",
    "face_count": 1,
    "blendshapes": {
      "smile": 0.82,
      "jaw_open": 0.14,
      "eye_closed_left": 0.03,
      "eye_closed_right": 0.04
    },
    "head_pose": {
      "yaw_deg": -9.8,
      "pitch_deg": 2.1,
      "roll_deg": -1.6
    },
    "eye_state": {
      "left_closed_prob": 0.03,
      "right_closed_prob": 0.04,
      "blink_detected": false
    },
    "engagement_proxy": 0.74,
    "quality": {
      "trackable": true,
      "confidence": 0.88,
      "frame_laplacian_var": 128.2,
      "min_face_side_px": 56
    }
  }
}
```

### `emotion` (legacy alias)

Same semantics as dominant face emotion for UI backwards compatibility.

Gateways **may** emit both `face_analysis` and `emotion` for the same frame.

### `face_debug` (debug / overlays)

Диагностические сообщения с дорожки лица (bounding box, признак прохождения gate, компактные признаки вроде `landmarks_n`, опционально эмоция/уверенность). Используются для live UI и для пополнения in-memory **`feature_store`** заглушки отчёта.

**Persistence:** в текущем backend сообщения **`face_debug` только broadcast** и **не** записываются в таблицу `analysis_event` (в отличие от `face_analysis`). Подробности см. [`REPORTS_AND_ANALYTICS_STORAGE.md`](./REPORTS_AND_ANALYTICS_STORAGE.md).

Рекомендуется сохранять на payload те же обязательные поля v1 (`module`, `stage`, `trace_id`, `version`), если клиенты группируют события по контракту.

### `analysis_report` / `analysis_report_partial`

Aggregated report from the report orchestrator / own NN.

- `report` (object): meeting-level + per-participant sections
- `model_version` (string)
- `generated_at` (RFC3339)
- `config_snapshot` (object, optional): effective `modules.*` config at generation time
- `report_source` (`remote` | `local_fallback` | `local_stub`): origin of report body

Current stub orchestrator may include inside `report` (optional):

- `pipeline_stage` (`idle` | `listening` | `transcribing` | `visual_only`)
- `speech_ratio` (number, 0..1 proxy)
- `participants[]` entries with fields such as
  `audio_chunks`, `avg_speech_activity_proxy`, `avg_bitrate_kbps`, `last_emotion`, `last_transcript`
- `fusion` (object, optional): `bucket_sec`, `trace_ids_by_participant`, `buckets[]` (per-window kind counts + trace_ids) — produced by the gateway stub / merged from stub when the remote NN omits it
- `emotion_summary`, `transcript_summary` — недавняя история по участникам
- `face_behavior_summary` — если в потоке были события с `face_behavior`
- `face_tracking_summary` — агрегация по **`face_debug`** из feature store (не из БД напрямую)
- `timelines` — побuket-сводки эмоций и транскрипта
- `observations` — правило-based строки без отдельной НС
- `participant_tiles` — компактные карточки участника для UI
- `meeting_summary` — сводка по встрече: `emotion_distribution_top` (поля **`emotion`**, **`events`**, `share`), `highlights_ru`, `participation_rank`, `coverage`, сравнения verbal / face-tracking между участниками

Полный перечень и семантика хранения см. [`REPORTS_AND_ANALYTICS_STORAGE.md`](./REPORTS_AND_ANALYTICS_STORAGE.md).

## trace_id

Clients and services should attach one `trace_id` per logical utterance or per batch (e.g. UUID). The report orchestrator uses it to join partial features before calling the final NN.
