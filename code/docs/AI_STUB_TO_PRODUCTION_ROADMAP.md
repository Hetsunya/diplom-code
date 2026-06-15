# AI: от заглушек к продакшену — дорожная карта

Документ дополняет [`AI_MODULES_ACTION_PLAN.md`](./AI_MODULES_ACTION_PLAN.md) и задаёт **приоритетный план замены эвристик и stub-режимов** без ломки контрактов WS v1. Карточки задач: [`cursor backlog.md`](../cursor%20backlog.md) (BL-AI-101…).

## Текущее состояние (кратко)

| Компонент | Что в проде сейчас | Что считается «заглушкой» / ограничением |
|-----------|-------------------|----------------------------------------|
| **speech-service** | `stub`, опционально **faster-whisper** (`SPEECH_ASR_ENGINE=whisper`), ffmpeg | Нет стриминга partial из модели «как в Zoom»; stub без текста; качество/латентность зависят от модели без авто-масштабирования |
| **ai-gateway → text** | HTTP адаптер + CB/retry, нормализация в `text_analysis`, эвристический `text_features` | NLP не модельный; нет diarization → текст не привязан к спикеру автоматически |
| **ai-gateway → audio** | Сигнальные признаки по сырым чанкам (energy, pause, jitter/shimmer proxy и т.д.) | Нет полноценного PCM decode WebRTC; нет SER/стресс-моделей по контенту речи |
| **ai-gateway → face** | DeepFace emotion, guards, semaphore, legacy `emotion`; опционально **MediaPipe** для `face_behavior` и `emit_debug_face` (`mediapipe_*` в конфиге; GLES в Docker) | Полный ONNX/light edge-путь не выбран как единственный; TF/MediaPipe тяжёлые для малого CPU |
| **ai-gateway → report** | Локальный stub + `fusion` + `data_quality` + расширения UI (`meeting_summary`, тайлы участников, таймлайны); опционально `own_nn_url` | Эвристический текст и ранжирования; «своя НС» вне репо или не обучена |
| **Наблюдаемость** | Счётчики, latency rings, `snapshot_health`, логи | Нет обязательного Prometheus scrape на gateway (опционально BL-AI-107) |

Контракты и точки расширения зафиксированы в [`ANALYSIS_WS_CONTRACTS.md`](./ANALYSIS_WS_CONTRACTS.md), [`ANALYSIS_OBSERVABILITY.md`](./ANALYSIS_OBSERVABILITY.md), [`REPORTS_AND_ANALYTICS_STORAGE.md`](./REPORTS_AND_ANALYTICS_STORAGE.md).

## Фазы внедрения (рекомендуемый порядок)

### Фаза 1 — Речь и текст (максимальный эффект для UX)

1. Поднять **стабильный ASR** под нагрузку (GPU/CPU профиль, очередь, таймауты уже есть в gateway).
2. Добиться предсказуемых **partial/final** реплик в UI (при необходимости расширить ответ `/v1/transcribe`, не ломая поля из адаптера).
3. Добавить **реальный NLP-слой** поверх строки (sentiment/topics или API) → обогащение `text_features`.

**Беклог:** BL-AI-101, BL-AI-105.

### Фаза 2 — Мультимодальность аудио

1. Нормальный **decode** медиа (Opus/WebM → PCM или официальный pipeline).
2. SER / стресс / темп поверх PCM или совместимый embedding для отчёта.

**Беклог:** BL-AI-102.

### Фаза 3 — Лицо и приватность

1. Уже есть опциональный путь **MediaPipe Face Landmarker** в gateway; дальше — выбор **ONNX / InsightFace** или упрощение образа и времени cold start при сохранении контракта `face_analysis`.
2. Политики: разрешение пользователя, локальный inference, минимизация хранения кадров.

**Беклог:** BL-AI-103.

### Фаза 4 — Отчёт и продуктовая модель

1. Обучить или подключить сервис под **`POST …/v1/report`** с входом `features` + `fusion`.
2. Зафиксировать версию модели в `report.payload.model_version` и снимок конфига.

**Беклог:** BL-AI-104.

### Фаза 5 — Спикеры и отчётность

1. **Diarization** (offline или streaming) для привязки текста к `participant_id`.
2. Обновление UI («кто сказал») и полей отчёта.

**Беклог:** BL-AI-106.

### Фаза 6 — Платформа и наблюдаемость

1. Экспорт метрик (Prometheus) или агент по логам.
2. Каталог **`code/AI/`** удалён из репозитория; при необходимости эталонные проекты держать вне git (upstream, submodule, локальный архив).

**Беклог:** BL-AI-107 (BL-AI-108 закрыт вместе с удалением `code/AI/`).

## Связанные команды проверки

- Контракт + ML-стек: `code/ai-gateway/hybrid_pipeline_smoke.py` (тяжёлые зависимости).
- Контракт без ML: `python -m unittest discover -s code/ai-gateway/tests`.
- Эмоции (кадр): `code/ai-gateway/smoke_ws_emotion_test.py`.

---

*Версия: 2026-05. При смене архитектуры обновляйте таблицу «текущее состояние» и карточки BL-AI-* в `cursor backlog.md`.*
