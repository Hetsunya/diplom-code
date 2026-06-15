# Отчёты по аналитике и хранение данных

Документ описывает, что попадает в БД, как собирается заглушечный отчёт в `ai-gateway`, и как UI получает данные. Дата актуализации: **2026-05**.

## Маршруты UI

| Маршрут | Назначение |
|---------|------------|
| `/reports` | Список сессий организатора и выбор отчёта (встроенная таблица); без `:id` показывается подсказка и история. |
| `/reports/:sessionId` | Детальный экран отчёта по сессии (данные из REST ниже). |

Колонка «Отчёт» на странице сессий ведёт на `/reports/:sessionId`. Роутинг задаётся в `emeeting-ui/src/config/features.ts`.

## REST API (источник истины для страницы отчёта)

Основной эндпоинт для экрана отчёта:

- **`GET /sessions/:id/analysis/report`** — последний сохранённый агрегат по сессии.
  - **Только организатор** (`session.created_by` = текущий пользователь). Гостям по ссылке — `403` (кроме старых строк без `created_by`, см. `docs/api-contract.md`).
  - Тело — JSON отчёта (часть полей приходит из gateway как `report` внутри WS-сообщения `analysis_report` / `analysis_report_partial` и сохраняется backend’ом).

История событий для отладки и таймлайнов на клиенте:

- **`GET /sessions/:id/analysis/events`** — см. фильтры в `docs/api-contract.md`.

Отдельный legacy-маршрут **`GET /reports/:id`** в backend может существовать для совместимости; продуктовый экран отчёта опирается на **`/sessions/:id/analysis/report`**.

## Что пишется в `analysis_event` (матрица persistence)

Backend регистрирует обработчики в `emeeting-backend/internal/session/ws_handler.go`:

| WS `type` | Broadcast | Persist в `analysis_event` |
|-----------|-----------|----------------------------|
| `text_analysis` | да | да |
| `audio_analysis` | да | да |
| `face_analysis` | да | да |
| `analysis_report` | да | да |
| `analysis_report_partial` | да | да |
| `emotion` (legacy) | да | да |
| **`face_debug`** | да | **нет** (только рассылка подключённым клиентам) |
| `frame`, `audio`, `chat_message`, … | по типу | нет (не аналитика v1) |

Следствия:

- **`face_debug`** удобен для live-оверлеев и отладки в UI, но **не восстанавлиется** через `GET .../analysis/events` после перезагрузки.
- Заглушка отчёта в gateway читает **`feature_store`** в памяти процесса; туда попадают срезы в том числе из **`face_debug`**, поэтому итоговый **`analysis_report`** может содержать `face_tracking_summary`, если во время жизни gateway отладочные события были. После рестарта gateway без новых данных эти сигналы в новых отчётах не появятся.
- Накопление **`face_analysis`**, **`text_analysis`**, **`audio_analysis`** и отчётов **не требует** явного «завершения встречи»: события копятся, пока идёт сессия; финальный тик отчёта обычно привязан к жизненному циклу `report_loop` (в т.ч. отключение gateway).

Если нужна полная история `face_debug` в БД — потребуется расширить backend (тип в `persistBroadcast` + миграции не нужны, таблица уже готова) и обновить этот документ.

## Поля заглушечного `report` (stub builder)

Источник: `ai-gateway/modules/report/stub_builder.py`. Ниже — расширения поверх базовых `summary`, `pipeline_stage`, `speech_ratio`, `participants`, `fusion`.

| Поле | Назначение |
|------|------------|
| `emotion_summary` | Агрегация эмоций по участникам (`counts`, `recent`, …). |
| `transcript_summary` | Недавние текстовые события ASR по участникам. |
| `face_behavior_summary` | Если в фичах есть `face_behavior` — сводка для отчёта. |
| `face_tracking_summary` | Сводка по **`face_debug`** из feature store (gate, skip reasons, recent). |
| `timelines` | Побucket-агрегация эмоций и транскрипта (`bucket_sec`, по участникам). |
| `observations` | Правила без НС (строки-наблюдения). |
| `participant_tiles` | Компактные карточки участников для UI. |
| `meeting_summary` | Общий rollup: `emotion_distribution_top` (**`emotion`**, **`events`**, `share`), `highlights_ru`, `participation_rank`, `coverage`, ссылки на most/least verbal, weakest/strongest face tracking и т.д. |

Контракт верхнего уровня WS по-прежнему см. `docs/ANALYSIS_WS_CONTRACTS.md`.

## Face-модуль и `face_debug`

Параметры `modules.face.params` (фрагмент): `emit_debug_face`, `emit_face_behavior`, **`mediapipe_enabled`**, `mediapipe_model_path`, `mediapipe_model_url`, `mediapipe_max_landmarks`.

- **DeepFace** остаётся основным путём для `face_analysis` / legacy `emotion`.
- **MediaPipe Face Landmarker** (опционально): даёт blendshapes и позу для `face_behavior` и опору для отладочных сообщений; в Docker образ gateway добавлены пакеты **EGL/GLES** (`libegl1`, `libgles2`), иначе задачи vision могут падать при загрузке.
- Зависимость **`mediapipe`** в `requirements.txt` ограничена **`python_version < "3.13"`**; образ gateway целится на **Python 3.11**.

## Связанные документы

- `docs/ANALYSIS_WS_CONTRACTS.md` — типы сообщений и поля envelope v1.
- `docs/api-contract.md` — REST и правила доступа к отчёту/событиям.
- `ai-gateway/MEMO.md` — конфиг модулей и поток runtime.
- `docs/ANALYSIS_OBSERVABILITY.md` — метрики (`face_mediapipe_errors`, события лога при сбое MediaPipe).
