# AI Gateway Memo

## Purpose

`ai-gateway` — отдельный WebSocket worker: подписан на события сессии встречи, выполняет AI-обработку и отправляет аналитические сообщения обратно в канал broadcast backend.

Точка входа: `main.py`.

## Configuration (modular)

| Источник | Описание |
|----------|----------|
| [`modules.default.json`](modules.default.json) | Локальный профиль по умолчанию |
| [`modules.docker.json`](modules.docker.json) | Образ Compose (`AI_GATEWAY_MODULES_CONFIG=/app/modules.docker.json`) |
| Env **`AI_GATEWAY_MODULES_CONFIG`** | Любой JSON с ключом верхнего уровня `modules` |

Структура каждого модуля: `enabled`, `provider`, `model`, `params`.

### text (ASR через HTTP)

- `modules.text.params.speech_service_url` → работающий [`speech-service`](../speech-service/) или совместимый API (`adapters/speech_service.py`).
- Таймауты / retry: `timeout_sec`, `retries`, `backoff_sec`.
- Circuit breaker: `circuit_failure_threshold`, `circuit_open_sec`; счётчик **`speech_service_circuit_open`** при быстром отказе.

### audio + text chain

- `modules/audio/pipeline.py`: опционально `audio_analysis`, затем вызов `modules/text/transcription.py` при включённом `text`.

### face

- Throttling: `min_interval_sec`.
- Качество: `min_confidence`, `min_laplacian_var`, `min_face_side_px`, `enforce_detection`, `detector_backend`, `align`, `emit_no_face_face_analysis`.
- Нагрузка: **`max_concurrent_inferences`** (default `2`) — `Semaphore` + `asyncio.to_thread` для DeepFace.
- Отладка: **`emit_debug_face`**, **`debug_bbox_smooth_alpha`**, **`debug_max_face_area_frac`** → исходящий WS **`face_debug`** (broadcast в backend **без** записи в `analysis_event`; см. `docs/REPORTS_AND_ANALYTICS_STORAGE.md`).
- Поведение лица (draft v1): **`emit_face_behavior`**, **`face_behavior_schema_version`**; опционально **MediaPipe** — **`mediapipe_enabled`**, **`mediapipe_model_path`** / **`mediapipe_model_url`**, **`mediapipe_max_landmarks`** (зависимость `mediapipe` только для Python **\< 3.13** в `requirements.txt`).
- Docker: образ ставит **`libegl1`** и **`libgles2`** (Mesa) для задач vision/MediaPipe.

### report

- `interval_sec`, **`report_wake_floor_sec`** (минимальная пауза между тиками цикла отчёта).
- `report_bucket_sec` — окна для `report.fusion`.
- Опционально **`own_nn_url`** → `POST {url}/v1/report` с телом `features`, `fusion`, `config_snapshot`, `stage`.

### Hot-reload без рестарта

- Env **`AI_GATEWAY_CONFIG_POLL_SEC`** (секунды; **`0`** = выключено): при изменении **mtime** файла `AI_GATEWAY_MODULES_CONFIG` конфиг перечитывается из `handlers.handle_message`.

Загрузчик: [`gateway_config.py`](gateway_config.py). Снимок для отчётов: `config_snapshot()`.

## Runtime flow

1. `main.py`: `set_gateway_config(load_gateway_config())`, URL WS из `BACKEND_WS_BASE_URL` + `SESSION_ID`.
2. `SessionWSClient`: токен `POST /auth/token`, заголовок на WS, backoff при обрыве.
3. Фоновая задача **`report_loop`**: периодические **`analysis_report_partial`** и финальный **`analysis_report`** при отмене задачи (закрытие соединения).
4. `handle_message` → плагины из **`modules/registry.py`** по `priority` и `can_handle`. Совместимость: тонкие shims в `plugins/*.py`.
5. Исходящие аналитические типы проверяются на обязательные поля v1: `module`, `version`, `stage`, `trace_id` (см. [`docs/ANALYSIS_WS_CONTRACTS.md`](../docs/ANALYSIS_WS_CONTRACTS.md)).

## Modules (`modules/`)

| Модуль | Priority | Поведение |
|--------|----------|-----------|
| `ping/handler.py` | 50 | Heartbeat / диагностика |
| `face/analysis.py` | 100 | DeepFace → `face_analysis` + legacy `emotion` |
| `audio/pipeline.py` | 150 | `audio_analysis` + опционально ASR → `text_analysis` |

Оркестрация отчёта: каталог **`modules/report/`** (`windowing`, `stub_builder`, `orchestrator`, `data_quality`); драйвер asyncio остаётся в **`report_loop.py`**.

## Observability

- [`observability.py`](observability.py): `incr`, `log_event`, `snapshot_metrics()`, **`observe_module_latency`**, **`snapshot_health()`** (p95/max/avg по последним сэмплам).
- Корреляция: `trace_id` в payload v1.
- Отчёты: **`report.data_quality`** (`complete`, `degraded_sources`, дельты счётчиков между тиками).

Подробнее: [`docs/ANALYSIS_OBSERVABILITY.md`](../docs/ANALYSIS_OBSERVABILITY.md).

## Backend integration

- WS `GET /ws/sessions/:id` (auth). Типы с **persist + broadcast**: `text_analysis`, `audio_analysis`, `face_analysis`, `analysis_report`, `analysis_report_partial`, `emotion` (legacy). Тип **`face_debug`** — **только broadcast** (не `analysis_event`).
- REST: `GET /sessions/:id/analysis/report`, `GET /sessions/:id/analysis/events?limit=`.

## Local checks

1. Env из `.env.example`: `BACKEND_WS_BASE_URL`, `SESSION_ID`, `AI_GATEWAY_*`, опционально `AI_GATEWAY_MODULES_CONFIG`, `AI_GATEWAY_CONFIG_POLL_SEC`.
2. `pip install -r requirements.txt`
3. Миграции backend с аналитикой применены к Postgres.
4. `python main.py`
5. Лицо: `python smoke_ws_emotion_test.py` — ожидаются `face_analysis` и `emotion`.
6. Полный hybrid (тяжёлые зависимости): `python hybrid_pipeline_smoke.py`.
7. Контракты без ML: `python -m unittest discover -s tests`.
8. Read-path к backend: `python e2e_analysis_readpath_check.py`.

## Добавить новый анализатор

1. Пакет `modules/<domain>/` с `plugin`, полями `name`, `priority`, `can_handle`, `async process`, опционально `metadata()`.
2. Регистрация в `modules/registry.py`.
3. При необходимости shim в `plugins/<name>.py`.
4. Контракт → [`docs/ANALYSIS_WS_CONTRACTS.md`](../docs/ANALYSIS_WS_CONTRACTS.md).
5. Backend: регистрация типа в `internal/session/ws_handler.go` и `internal/analysis`, если нужен persist.

## Документация проекта

Индекс: [`docs/README.md`](../docs/README.md). План замены заглушек: [`docs/AI_STUB_TO_PRODUCTION_ROADMAP.md`](../docs/AI_STUB_TO_PRODUCTION_ROADMAP.md).
