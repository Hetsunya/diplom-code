Отлично — вот готовый технический backlog с приоритетом, оценкой и привязкой к файлам, чтобы можно было сразу заносить в трекер.

**Где что лежит (монорепо):** каталог `code/` — основной код; **прод docker-compose и `.env.prod.example`** — в **корне репозитория** на уровень выше `code/` (`docker-compose.prod.yml`, `.env.prod.example`, `Caddyfile`). Локальный стек: `docker-compose.yml` там же.

---

Новая группировка задач (единая для планирования релиза)

Чтобы не смешивать “must-have до прод” и R&D после релиза, использовать следующую структуру:

**Track A — Release Gate (обязательно до прод)**
- BL-025 (HTTPS/reverse proxy), BL-027 (auth hardening), BL-029 (observability release-уровня)
- BL-110 (Report UI v2 без моков), BL-111 (контракт отчетов single/team/trends)
- BL-BE-113 (история транскрибации API уровня, стабильный endpoint)

**Track B — Prod Stabilization (первые 2–4 недели после запуска)**
- BL-AI-101 (ASR quality/latency baseline), BL-AI-112 (стабильный realtime flow без артефактов)
- BL-AI-109 (nightly smoke/CI для AI), BL-AI-107 (метрики/дашборды)

**Track C — Post-Prod R&D (не блокирует релиз)**
- BL-AI-102/103/104/105/106 (audio v2, face provider v3, own NN report, NLP, diarization)
- Новые face behavior задачи BL-AI-114..117 (ниже)

Правило приоритизации:
- пока не закрыт Track A — задачи Track C не поднимаются в активный спринт;
- Track B можно вести параллельно с bugfix после go-live;
- Track C — только отдельным roadmap-потоком.

Backlog (приоритетный)
P0 — Стабильный базовый контур (блокеры)
BL-001 [x]: Зафиксировать API-контракт v1 (UI ↔ Backend)

Цель: убрать рассинхрон эндпоинтов и payload.
Файлы: emeeting-ui/src/api/auth.ts, emeeting-ui/src/api/reports.ts, emeeting-ui/src/api/sessions.ts, emeeting-backend/cmd/server/main.go
Результат: документ docs/api-contract.md + backend маршруты соответствуют UI.
Оценка: 4–6 ч
DoD: UI не получает 404 на основных сценариях (login/sessions/reports).
BL-002 [x]: Убрать хардкод конфигов во всех сервисах

Цель: переносимость между окружениями.
Файлы: emeeting-backend/internal/db/postgres.go, emeeting-backend/cmd/server/main.go, emeeting-ui/src/api/http.ts, emeeting-ui/src/hooks/useSessionWS.ts, ai-gateway/main.py
Результат: env-переменные + .env.example в emeeting-backend, emeeting-ui, ai-gateway.
Оценка: 4–8 ч
DoD: запуск на новой машине без правки исходников.
BL-003 [x]: Минимально закрыть пустые backend-заготовки

Цель: убрать технические “дыры” в критическом пути.
Файлы: emeeting-backend/internal/auth/handler.go, emeeting-backend/internal/auth/service.go, emeeting-backend/internal/session/service.go, emeeting-backend/internal/ws/handler.go
Результат: рабочие заглушки/реализации без пустых файлов.
Оценка: 1–2 дн
DoD: проект билдится, маршруты отвечают предсказуемо (не “пустые” обработчики).
BL-004 [x]: Базовые автотесты backend

Цель: ловить регрессии по сессиям и WS.
Файлы: emeeting-backend/internal/session/*, новые *_test.go
Результат: unit + интеграционные smoke-тесты для /sessions и WS-подключения.
Оценка: 1–2 дн
DoD: go test ./... зеленый локально и в CI.
P1 — Предсказуемая разработка и релиз
BL-005 [x]: Настроить CI (lint + test + build)

Цель: автоматическая проверка каждого PR/коммита.
Файлы: .github/workflows/ci.yml (новый), конфиги линта/тестов
Результат: пайплайн для emeeting-ui, emeeting-backend, ai-gateway.
Оценка: 6–10 ч
DoD: CI падает при поломке тестов/линта.
BL-006 [x]: Воспроизводимый локальный запуск (docker-compose)

Цель: запуск всего стека одной командой.
Файлы: docker-compose.yml (новый), Dockerfile для сервисов, README.md (корень)
Результат: db + backend + gateway + ui в одном compose.
Оценка: 1–2 дн
DoD: docker compose up поднимает систему и health-check проходит.
BL-007 [x]: Миграции БД

Цель: управляемая эволюция схемы.
Файлы: emeeting-backend/migrations/* (новые), скрипты запуска миграций
Результат: versioned SQL миграции и инструкция отката.
Оценка: 6–12 ч
DoD: новая БД поднимается из нуля до актуальной схемы автоматически.
BL-008 [x]: Нормальная проектная документация

Цель: снизить bus factor и onboarding time.
Файлы: README.md (корень), emeeting-ui/README.md
Результат: runbook “как поднять/проверить/дебажить”.
Оценка: 3–5 ч
DoD: новый разработчик поднимает проект по инструкции без помощи.
P2 — Расширяемость инструментария (архитектурно)
BL-009 [x]: Backend модульная регистрация роутов

Цель: масштабировать новые домены без разрастания main.go.
Файлы: emeeting-backend/cmd/server/main.go, emeeting-backend/internal/*/module.go (новые)
Результат: интерфейс модуля (RegisterRoutes) и сборка через список модулей.
Оценка: 1–2 дн
DoD: добавление нового модуля не требует большого рефакторинга main.go.
BL-010 [x]: Интерфейсы портов в session/auth

Цель: тестируемость и замена реализаций.
Файлы: emeeting-backend/internal/session/contracts.go, handler.go, repository.go, hub.go
Результат: Repository/Service/Bus как интерфейсы, handler зависит от абстракций.
Оценка: 1–2 дн
DoD: можно подменить репозиторий моками в unit-тестах.
BL-011 [x]: Registry-based WS dispatch

Цель: легко добавлять новые WS-команды.
Файлы: emeeting-backend/internal/session/ws_handler.go
Результат: map[type]handler вместо giant switch.
Оценка: 6–10 ч
DoD: новая команда добавляется через регистрацию обработчика.
BL-012 [x]: Плагинный AI-pipeline в gateway

Цель: расширять AI-инструментарий без переписывания центра.
Файлы: ai-gateway/handlers.py, ai-gateway/main.py, ai-gateway/plugins/* (новые)
Результат: контракт анализатора (can_handle/process) + реестр плагинов.
Оценка: 1–2 дн
DoD: новый анализатор подключается отдельным модулем.
BL-013 [x]: Декларативный feature-config на UI

Цель: включать новые инструменты/страницы конфигом.
Файлы: emeeting-ui/src/router.tsx, emeeting-ui/src/components/Navbar.tsx, emeeting-ui/src/config/features.ts (новый)
Результат: маршруты/пункты меню генерируются из конфигурации.
Оценка: 6–12 ч
DoD: новая фича добавляется в одном месте, без ручной правки нескольких файлов.
Рекомендуемый порядок внедрения (спринты)
Спринт 1 (стабильность): BL-001 → BL-002 → BL-003 → BL-004
Спринт 2 (инженерная надежность): BL-005 → BL-006 → BL-007 → BL-008
Спринт 3 (расширяемость): BL-009 → BL-010 → BL-011 → BL-012 → BL-013
KPI, чтобы видеть прогресс
0 критичных 404 на основных user flow.
>=70% покрытие для критичного backend-пути сессий/WS (минимум smoke + ключевая логика).
Время поднятия проекта “с нуля” ≤ 15 минут по README.
Добавление новой WS-команды/AI-инструмента ≤ 1 файл + регистрация (без правки центральных switch-цепочек).
Если хочешь, следующим шагом разложу это в формат GitHub Issues (title, description, acceptance criteria, labels, estimate) — готовыми карточками.

---

Новый backlog (по `@instructions.md`, meeting/auth)

P0 — Meeting Service (MVP real-time, блокеры продукта)
BL-014 [x]: State machine митинга + аудит событий в БД

Цель: формализовать жизненный цикл и историю изменений.
Файлы: emeeting-backend/internal/meeting/**, emeeting-backend/migrations/up/*, emeeting-backend/migrations/down/*
Результат:
- статусы: created|active|paused|ended|cancelled
- сервис-методы переходов: StartMeeting(), EndMeeting() (+ валидация)
- таблица audit: meeting_events (append-only)
Оценка: 1–2 дн
DoD: unit-тесты на переходы (`TestMeeting_Transitions`) + миграция поднимается с нуля.

BL-015 [x]: Участники и роли (host/co-host/participant/guest)

Цель: управляемые join/leave и права на действия.
Файлы: emeeting-backend/internal/meeting/**, emeeting-backend/migrations/*
Результат:
- модель participants с ролями и флагом активности (soft leave: is_active=false)
- проверки доступа: user_id из токена ↔ participant.user_id
Оценка: 1–2 дн
DoD: тесты сервис-слоя на join/leave и проверки ролей.

BL-016 [x]: WS события join/leave/start/end + broadcast hub

Цель: синхронизация состояния в реальном времени.
Файлы: emeeting-backend/internal/session/**, emeeting-backend/internal/meeting/**, emeeting-ui/src/**
Результат:
- WSEvent (type/payload/ts)
- события: user_joined, user_left, host_started, meeting_ended (+ user_removed опционально)
- broadcast всем активным соединениям сессии
Оценка: 1–2 дн
DoD: интеграционный тест потока (`TestE2E_MeetingFlow`) + UI обновляет список участников.

BL-017 [x]: Реконнект: восстановление участника по session_id + token

Цель: устойчивость к обрывам сети.
Файлы: code/emeeting-backend/internal/ws/**, code/emeeting-backend/internal/meeting/**, code/emeeting-ui/src/features/meeting/**
Результат:
- server-side: rejoin без дубликатов participant, корректная повторная подписка
- client-side: авто-reconnect с backoff, resync состояния (fetch + cache update)
Оценка: 1–2 дн
DoD: тест на реконнект (backend) + unit-тесты обработчика событий (frontend).

BL-018 [x]: Обработка onClose (user_left) + правило “host ушёл”

Цель: консистентная очистка participants и корректное завершение митинга.
Файлы: code/emeeting-backend/internal/ws/handler.go, code/emeeting-backend/internal/meeting/service.go, code/emeeting-ui/src/features/meeting/**
Результат:
- onClose: is_active=false + broadcast user_left {user_id,left_at}
- если ушёл host и нет co-host: meeting → ended (+ meeting_ended)
Оценка: 6–12 ч
DoD: `TestMeeting_UserDisconnect_WithCoHost`, `TestMeeting_UserDisconnect_HostOnly` + UI корректно реагирует.

P1 — Frontend Meeting UX (чтобы митинг ощущался “живым”)
BL-019 [x]: Meeting feature-store (React Query + Zustand) + WS hook

Цель: разделить server-state и UI-state и стандартизировать WS подписку.
Файлы: code/emeeting-ui/src/features/meeting/**, (опц.) src/lib/ws
Результат:
- `useMeetingStore` (UI флаги/модалки)
- `useMeetingWebSocket`/`useWebSocket` с `onEvent(handleMeetingEvent)`
Оценка: 6–12 ч
DoD: тесты на обработку событий (Vitest) + отсутствие “ручных” setState по всему UI.

BL-020 [x]: UI реакции на WS события (participants cache + toasts + redirect)

Цель: завершить пользовательский цикл “вошёл/вышел/кикнули”.
Файлы: code/emeeting-ui/src/features/meeting/** (participants list, toast, routing)
Результат:
- user_left/user_joined обновляют кэш React Query
- если текущего кикнули: redirect на /meetings + сообщение
Оценка: 4–8 ч
DoD: RTL тесты на редирект/тост и корректное обновление списка.

P0 — Auth System (безопасный базовый контур)
BL-021 [x]: bcrypt для password_hash + миграция/переезд

Цель: убрать SHA-256 и подготовиться к прод-уровню.
Файлы: code/emeeting-backend/internal/auth/**, code/emeeting-backend/migrations/*
Результат:
- хранение bcrypt hash
- сценарий миграции: на логине “rehash” (или массовое обновление для демо-юзеров)
Оценка: 1 дн
DoD: `TestAuth_LoginFlow` покрывает корректные/некорректные пароли.

BL-022 [x]: Access/Refresh tokens + rotation + хранение refresh в БД

Цель: короткий access + безопасный refresh с одноразовостью.
Файлы: code/emeeting-backend/internal/auth/**, code/emeeting-backend/migrations/*
Результат:
- refresh_tokens (token_hash, user_id, expires_at, revoked) + индексы
- refresh rotation: при использовании выдаём новый, старый revoke
Оценка: 1–2 дн
DoD: `TestAuth_TokenRefresh_Invalidated` (старый refresh не работает).

BL-023 [x]: HttpOnly cookie с session token + фронтенд без localStorage

Цель: минимизировать XSS-риски и убрать хранение токенов на клиенте.
Файлы: code/emeeting-backend/internal/auth/**, code/emeeting-ui/src/features/auth/**, UI http client
Результат:
- backend выставляет cookie `session_token` (Secure только prod)
- frontend: AuthContext, retry при 401, auto refresh
Оценка: 1–2 дн
DoD: ручной сценарий “обновил страницу — остаюсь залогинен” (если предусмотрено) + автоповтор запроса после refresh.

BL-024 [x]: Middleware: RequireAuth / RequireRole / RateLimit + audit auth_events

Цель: централизованная защита эндпоинтов и защита от brute-force.
Файлы: code/emeeting-backend/middleware/**, code/emeeting-backend/internal/auth/**, migrations/*
Результат:
- порядок middleware: Recover → Logger → CORS → RateLimit → Auth → Handler
- rate-limit логина: 5/мин IP + lock после 10 попыток (locked_until)
- аудит: auth_events (login_attempt, token_refresh, logout)
Оценка: 1–2 дн
DoD: `TestMiddleware_RequireRole` + тест на блокировку brute-force.

Рекомендуемый порядок внедрения (следующие спринты)
Спринт 4 (meeting MVP): BL-014 → BL-015 → BL-016 → BL-018 → BL-020
Спринт 5 (meeting resilience): BL-017 → BL-019
Спринт 6 (auth secure): BL-021 → BL-022 → BL-023 → BL-024

---

P0 — Release/VDS (единое решение для Linux/Windows + прод)
BL-025 [~]: Продовый reverse-proxy + HTTPS (чтобы работал getUserMedia везде)

Цель: камера/микрофон работают не только на localhost, без “secure context” проблем.
Результат:
- домен + TLS (например Caddy или Nginx+certbot)
- единый origin: `https://<domain>` проксирует `/api` и `/ws` на backend
Оценка: 1 дн
DoD: `navigator.mediaDevices.getUserMedia` доступен на VDS, UI/WS/API работают через один домен.
Статус: **базово закрыто составом `docker-compose.prod.yml`** (сервис `caddy`, `DOMAIN`, volume сертификатов). Остаётся ручной настройкой: реальный DNS на VDS, заполнение `.env.prod`, проверка с браузера.

BL-026 [x]: Prod docker-compose (secrets/env/volumes) + .env.prod.example

Цель: воспроизводимый деплой на VDS без ручных правок.
Результат:
- `docker-compose.prod.yml` (корень репо, не в `code/`)
- `.env.prod.example` с `JWT_SECRET`, `POSTGRES_*`, `CORS_ALLOW_ORIGIN`, `VITE_*`, опционально AI profile
- том `postgres_data` для Postgres; Caddy + HTTPS на 80/443
Оценка: 6–12 ч
DoD: поднятие на чистой VDS одной командой, после рестарта данные на месте.
Статус: реализовано; см. корневой `README.md` (`docker compose -f docker-compose.prod.yml --env-file .env.prod …`). **Не автоматизировано:** scheduled pg_dump / внешние бэкапы — вне карточки (ручной процесс или отдельная задача).

BL-027 [~]: Auth hardening для prod (cookie Secure + SameSite + rotation)

Цель: убрать “иногда надо перезапуск” и сделать поведение токенов предсказуемым.
Результат:
- cookie `Secure=true` на HTTPS
- чёткая политика SameSite (обычно Lax при одном origin)
- refresh flow стабилен
Оценка: 4–8 ч
DoD: логин сохраняется после F5, `/sessions` не ловит 401 без причины.
Статус: **Secure** по `TLS` / `X-Forwarded-Proto` (Caddy) уже было; **SameSite** — эвристика: тот же hostname, что и API → **Lax** (раньше для не-localhost сразу ставился **None**). Опция **`AUTH_COOKIE_SAMESITE`** (strict|lax|none) в `internal/auth/handler.go` + `emeeting-backend/.env.example`. Ротация refresh — прежняя в `POST /auth/refresh`.

BL-028 [x]: ai-gateway: сервис‑аккаунт/токен для WS или отдельный internal-канал

Цель: gateway не получает 401 на WS.
Результат (варианты):
- A) gateway получает сервисный access token и подключается с ним
- B) отдельный endpoint для internal клиентов в одной сети (с ограничениями)
Оценка: 1–2 дн
DoD: ai-gateway стабильно подключается и не падает.

Статус:
- Реализовано: `/auth/token` (выдаёт TokenPair JSON для сервисов), поддержка `Authorization: Bearer <JWT>` в `RequireAuth`, настройки env для ai-gateway.
- Проверено: gateway подключается к `/ws/sessions/:id` без 401 в docker-compose.

BL-029 [~]: Observability для релиза (логирование/health/метрики)

Цель: быстро понимать “почему не работает” без дебага в браузере.
Результат:
- структурные логи, request-id
- health endpoints и понятные статусы
Оценка: 6–12 ч
DoD: по логам видно origin/cookies/auth path и причины отказа.

Статус (частично):
- Реализовано: `X-Request-ID` middleware + access log с rid/origin/host/xfp/uid.
- Реализовано: `GET /health` и `GET /ready` (ready проверяет Ping к Postgres).
- Реализовано: `GET /metrics` (Prometheus `client_golang` default registry, без auth — для скрейпа за firewall / allowlist).
- Не закрыто по DoD BL-029: бизнес-алерты/SLO, кастомные RED counts (отдельный трек).

---

P0 — AI modules implementation (единая папка модулей)

**Синхронизация статусов BL-030…BL-037 (2026-05):** часть работы уже в коде, но DoD карточек ниже формулировался шире — не удаляем карточки, фиксируем фактический прогресс.

| ID | Фактический статус | Куда смотреть в репо |
|----|--------------------|----------------------|
| BL-030 | **сделано** | `ai-gateway/modules/**` (face/audio/text/ping/report), `handlers` грузит `modules.registry`; `plugins/*` — тонкие shims |
| BL-031 | **сделано (v1)** | `normalize.py` + `features.py` + `transcription.py`; `speech_service.py` (retry/CB); юнит-тесты `tests/test_text_*.py`; тяжёлый NLP — вне v1 |
| BL-032 | **частично** | `modules/audio/signal.py`: energy/zcr/pause/jitter/shimmer + `modules.audio.params`; `pipeline.py`: интервалы между чанками; WebM/Opus без demux — эвристика по сырым байтам |
| BL-033 | **сделано (v2 baseline)** | `modules/face/schema.py`, `frame_quality.py`, `params.py`, `analysis.py`; `report_loop` читает `data.face_features`; UI игнор `face_detected=false` |
| BL-034 | **сделано (v1 orchestrator)** | `modules/report/*` + `report_loop.py` (partial + **final** on cancel); `fusion` + `report_bucket_sec`; `own_nn_client` POST с `fusion` |
| BL-035 | **частично** | фильтры `module`/`participant_id`/`from`/`to`/`limit` + доступ: организатор vs гость (`participant_id` обязателен); отчёт только организатору; audit-лог `[ANALYSIS_ACCESS]`; роли host/co-host из meeting-сервиса без отдельной таблицы — не делали |
| BL-036 | **сделано (контур)** | `hybrid_pipeline_smoke.py` + `hybrid_contract.py` + `tests/test_hybrid_contract.py`; Go `TestWS_AnalysisInboundBroadcast`; `report_wake_floor_sec` для быстрого partial |
| BL-037 | **сделано (baseline)** | hot-reload JSON, face semaphore, latency rings + `snapshot_health`, `report.data_quality`, prod compose `AI_GATEWAY_CONFIG_POLL_SEC` |
| BL-AI-101…109 | **план** | замена stub/эвристик на прод-модели: см. конец файла + `docs/AI_STUB_TO_PRODUCTION_ROADMAP.md` |

BL-030 [x]: Единый layout для AI-модулей в одной папке

Цель: стандартизовать структуру и убрать размазывание логики по разным местам.
Файлы: `ai-gateway/modules/**` (новые), `ai-gateway/handlers.py`, `ai-gateway/gateway_config.py`, `ai-gateway/MEMO.md`
Результат:
- единая папка: `ai-gateway/modules/`
- подпапки: `text/`, `audio/`, `face/`, `report/`, `shared/`
- общий интерфейс модуля (`can_handle/process` + metadata: module/provider/model/version)
Оценка: 1 дн
DoD: все активные анализаторы грузятся из `ai-gateway/modules/**`, старые `plugins/*` либо проксируют, либо удалены без потери функционала.
Статус: `handlers` → `modules.registry.iter_plugins()`; `plugins/*.py` — shims.

BL-031 [x]: Text module v1 (ASR + NLP поверх транскрибации)

Цель: получить стабильный поток `text_analysis` partial/final из отдельного speech-service.
Файлы: `ai-gateway/modules/text/**`, `ai-gateway/adapters/speech_service.py`, `speech-service/**`, `docs/ANALYSIS_WS_CONTRACTS.md`
Результат:
- адаптер к speech-service с timeout/retry/circuit-breaker
- нормализация ответа ASR в контракт `text_analysis`
- базовые `text_features` (sentiment/topics/keyphrases/confidence) как отдельный шаг
Оценка: 1–2 дн
DoD: в live-сессии приходят `text_analysis` события с `trace_id`, `stage`, `version`; при ошибке speech-service gateway не падает.
Статус (2026-05): `normalize_asr_response` (алиасы `text`/`final`/`segments`), `enrich_text_features` (эвристика при пустых полях), пропуск пустого транскрипта без WS-шума; тесты `test_text_normalize.py`, `test_text_features.py`, `test_text_transcription.py`.

BL-032 [~]: Audio module v1 (voice/signal features)

Цель: заменить текущий stub на реальный анализ аудио-сигнала.
Файлы: `ai-gateway/modules/audio/**`, `docs/ANALYSIS_WS_CONTRACTS.md`, `docs/ANALYSIS_OBSERVABILITY.md`
Результат:
- извлечение признаков: energy, pause_ratio, tempo, (опц.) jitter/shimmer
- публикация `audio_analysis` partial событий
- конфигурируемые пороги/окна (`modules.audio.params`)
Оценка: 1–2 дн
DoD: `audio_analysis` стабильно публикуется, latency в целевом диапазоне p95, есть fallback при невалидном чанке.
Статус (2026): baseline-v3 — `energy_rms_norm`, `zero_crossing_rate`, `pause_ratio`, `chunk_interval_ms` / `activity_pulses_per_min`, `timing_jitter_ms`, `shimmer_proxy`; `extract_audio_features_safe` при ошибке; пороги в `modules.audio.params`. Полный PCM/WebRTC decode и p95 — не замеряли.

BL-033 [x]: Face module v2 (emotion alias + quality guards)

Цель: стабилизировать модуль лица и подготовить к прод-режиму.
Файлы: `ai-gateway/modules/face/**`, `ai-gateway/contracts.py`, `emeeting-backend/internal/analysis/**`
Результат:
- основной тип `face_analysis`, legacy `emotion` как alias
- quality guards: face_detected=false, confidence thresholds, skip noisy frames
- вынесенные настройки провайдера/модели (`modules.face.*`)
Оценка: 1 дн
DoD: UI совместим с legacy `emotion`, а новый канал `face_analysis` используется для агрегаторов/отчетов.
Статус (2026-05): конфиг `enforce_detection`, `detector_backend`, `align`, `min_laplacian_var`, `min_face_side_px`, `emit_no_face_face_analysis`; blur/small-region/low-confidence — фильтры; опционально `face_analysis` без legacy при `no_face` (если включён emit); `_stub_report` учитывает `data.face_features` как в gateway; `VideoMeet` не парсит эмоцию при `face_detected=false`.

BL-034 [x]: Report orchestrator v1 (fusion text+audio+face -> own NN)

Цель: собрать 3 канала в единый отчетный пайплайн.
Файлы: `ai-gateway/modules/report/**`, `ai-gateway/feature_store.py`, `ai-gateway/own_nn_client.py`, `docs/ANALYSIS_WS_CONTRACTS.md`
Результат:
- windowing/join по `trace_id` + `participant_id` + time bucket
- `analysis_report_partial` (инкрементально) и `analysis_report` (финал)
- вызов собственной нейронки (`own_nn_url`) + fallback stub
Оценка: 2–3 дн
DoD: по завершении сессии есть финальный `analysis_report`, структура совпадает с контрактом, конфиг-снимок сохранен.
Статус (2026-05): `compute_fusion_meta` + `build_stub_report` (`fusion` в теле `report`); `resolve_report_body` / `build_report_ws_message`; при **отмене** `report_loop` (закрытие WS) отправляется `analysis_report` с `stage=final`; параметр `report_bucket_sec`; тесты `tests/test_report_windowing.py`. Полный NN fusion внешнего сервиса — по контракту POST `/v1/report` + поле `fusion`.

BL-035 [~]: Backend RBAC + API фильтры для аналитики

Цель: безопасный доступ к аналитике и удобная выборка.
Файлы: `emeeting-backend/internal/analysis/http_handlers.go`, `emeeting-backend/internal/analysis/repository.go`, `middleware/auth.go`
Результат:
- role-aware доступ к `/sessions/:id/analysis/*`
- фильтры для events: `module`, `participant_id`, `from`, `to`, `limit`
- audit лог доступа к participant-level данным
Оценка: 1–2 дн
DoD: host/co-host видят полный отчет, participant — только разрешенный уровень детализации.
Статус (2026): организатор (`session.created_by`) — полный `/report` и `/events`; не организатор — `/events` только с `participant_id`; фильтры по времени и модулю; лог `[ANALYSIS_ACCESS]`. Отдельные роли meeting без БД участников — вперёд.

BL-036 [x]: E2E тест-контур AI pipeline (hybrid)

Цель: поймать регрессии на сквозном потоке до релиза.
Файлы: `ai-gateway/smoke_ws_emotion_test.py` (расширить), новые `ai-gateway/tests/*`, `emeeting-backend/internal/session/ws_handler_test.go`
Результат:
- smoke: frame -> face_analysis/emotion
- smoke: audio -> text_analysis + audio_analysis
- smoke: partial report -> final report
Оценка: 1–2 дн
DoD: один сценарий запуска проверяет полный hybrid pipeline и валидирует обязательные поля контракта.
Статус (2026-05): `hybrid_pipeline_smoke.py` (локальный WS hub + stub `/v1/transcribe` + отмена gateway → финальный `analysis_report`); **контракт без ML**: `tests/test_hybrid_contract.py`; backend: `TestWS_AnalysisInboundBroadcast` для `text_analysis`. Полный smoke как у emotion-теста требует DeepFace/tf stack.

BL-037 [x]: Prod readiness AI (ресурсы, деградация, алерты)

Цель: контролируемое поведение под нагрузкой и при деградации внешних сервисов.
Файлы: `ai-gateway/observability.py`, `docs/ANALYSIS_OBSERVABILITY.md`, `docker-compose.prod.yml` (или эквивалент)
Результат:
- лимиты/очереди на тяжелые модули
- graceful degradation (отключение модуля через конфиг без перезапуска backend)
- метрики и алерты: error-rate, module latency, report generation lag
Оценка: 1–2 дн
DoD: при падении speech-service или face-провайдера остальные модули продолжают работу, отчет формируется с пометкой неполных данных.
Статус (2026-05): `AI_GATEWAY_CONFIG_POLL_SEC` + `maybe_reload_gateway_config` (mtime); face `max_concurrent_inferences` + semaphore/`to_thread`; `observe_module_latency` + `snapshot_health`; `speech_service_circuit_open` counter; `report.data_quality` (`modules/report/data_quality.py`); compose env для poll; тесты `test_data_quality`, `test_gateway_config_reload`, `test_observability_health`. Внешние алерты Prometheus — по желанию поверх логов/`snapshot_health`.

Рекомендуемый порядок внедрения (AI спринты)
Спринт 7 (структура + контракты): BL-030 → BL-031
Спринт 8 (мультимодальность): BL-032 → BL-033
Спринт 9 (агрегация/отчеты): BL-034 → BL-035
Спринт 10 (стабилизация): BL-036 → BL-037

---

P1 — UI: транскрипт, чат, вердикт AI (план в `docs/UI_AI_ANALYSIS_PLAN.md`)

BL-038 [x]: Правый рейл «Live транскрипт» (не чат)

Цель: отображать поток `text_analysis` (partial/final) по спикерам, без смешивания с пользовательским чатом.
Файлы: `emeeting-ui/src/pages/VideoMeet.tsx`, `emeeting-ui/src/features/meeting/MeetingTranscriptRail.tsx`
Оценка: 1–2 дн
DoD: при live-сессии видны строки транскрипта; состояния не «вечный analyzing».

BL-039 [x]: Отдельная панель «Чат»

Цель: явное UI-разделение чата и транскрипта (макет + роутинг/состояние при необходимости).
Статус: отдельная секция **`MeetingChatSection`** в правом рейле; транскрипт (ASR) выше, чат ниже с подсказкой «Отдельно от ASR». WS `chat_message`, сохранение в **`session_chat_message`** (`008_session_chat`), **`GET /sessions/:id/chat/messages`**, подгрузка истории для новых участников. Отдельный роут вида `/meet/:id/chat` не делали — не требуется для DoD.
Файлы: `emeeting-ui/src/features/meeting/MeetingChatSection.tsx`, `MeetingTranscriptRail.tsx`, `VideoMeet.tsx`; backend `ws_handler.go` + `internal/chat`, миграция `008_session_chat`.
Оценка: 1 дн
DoD: пользователь не путает ASR-текст с сообщениями чата.

BL-040 [x]: Плашка / блок «Вердикт» по `analysis_report_partial`

Цель: краткий вывод нейросети + раскрытие деталей (drawer/modal).
Статус: кнопка + раскрытие JSON `report` в рейле; REST fallback не делали.
Файлы: `emeeting-ui/src/pages/VideoMeet.tsx`, `emeeting-ui/src/features/meeting/MeetingTranscriptRail.tsx`; `emeeting-ui/src/api/sessions.ts` (опц. REST fallback)
Оценка: 1 дн
DoD: клик открывает подробности; пустое состояние без вводящего в заблуждение текста.

BL-041 [x]: Убрать или переработать «AI analyzing…»

Цель: заменить на состояния пайплайна (listening / transcribing / verdict) или убрать дублирование с индикаторами рейла.
Статус: до первого `emotion`/`face_analysis` — «Лицо: —»; после — эмоция + %; тип `Analyzing` убран.
Файлы: `emeeting-ui/src/pages/VideoMeet.tsx`, `emeeting-ui/src/features/meeting/useMeetingStore.ts`
Оценка: 0.5–1 дн
DoD: нет «вечного» analyzing при отсутствии событий; согласовано с BL-038.

Опционально позже (фаза D в плане): bubble под активным спикером — отдельная карточка после diarization/VAD в данных.

---

P2 — AI: от заглушек к продакшену (модели вместо stub / эвристик)

Дорожная карта по фазам: **`docs/AI_STUB_TO_PRODUCTION_ROADMAP.md`**. Индекс документации: **`docs/README.md`**.

Рекомендуемый порядок: **BL-AI-101 → BL-AI-105 → BL-AI-102 → BL-AI-106 → BL-AI-104 → BL-AI-103 → BL-AI-107/108** (параллельно CI BL-AI-109 по мере готовности железа).

BL-AI-101 [ ]: Production ASR (speech-service)

Цель: заменить повседневную эксплуатацию на предсказуемое распознавание (качество/latency под профиль CPU/GPU).
Файлы: `speech-service/**`, `ai-gateway/adapters/speech_service.py`, `docker-compose*.yml`
Результат: выбранный движок (улучшенный Whisper / whisper.cpp server / облачный API) за контрактом `POST /v1/transcribe`; политики очереди и ресурсов в Compose; baseline метрики latency/error на стороне gateway уже есть.
Оценка: 3–10 дн (зависит от облака vs self-hosted)
DoD: на эталонных записях WER/latency в целевых порогах; `text_analysis` стабильно в live; при падении ASR CB не роняет остальной пайплайн.

BL-AI-102 [ ]: Audio pipeline v2 (decode + SER/просодия)

Цель: уйти от эвристик только по «сырым» чанкам там, где нужен контент речи.
Файлы: `ai-gateway/modules/audio/**`, опционально отдельный лёгкий decode-сервис
Результат: надёжный путь WebRTC/WebM/Opus → PCM (или эквивалент); признаки SER/stress/tempo поверх PCM; контракт `audio_analysis` сохраняется.
Оценка: 1–3 нед
DoD: документированный формат входа; регрессионные фикстуры чанков; p95 latency в `ANALYSIS_OBSERVABILITY` целях.

BL-AI-103 [ ]: Face provider v3 (лёгкий inference / приватность)

Цель: снизить холодный старт и зависимость от TF-стека или улучшить качество на «сложных» камерах.
Файлы: `ai-gateway/modules/face/**`, Docker образ gateway
Результат: второй провайдер за флагом конфига (ONNX/MediaPipe/иное) или оптимизированный DeepFace-путь; документирование GDPR/хранения кадров.
Оценка: 1–2 нед
DoD: переключение только через `modules.face.*` без смены контракта UI.

BL-AI-104 [ ]: Сервис отчёта «своей НС» под `own_nn_url`

Цель: финальный `analysis_report` с модельным телом, а не только stub-агрегатом.
Файлы: `ai-gateway/own_nn_client.py`, `modules/report/**`, отдельный repo/образ модели
Результат: обученная или зафиксированная версия модели; вход `features` + `fusion`; валидируемый JSON `report`; версия в `model_version`.
Оценка: 2–6 нед
DoD: E2E: после сессии REST/UI видят содержательный отчёт; fallback на stub при 5xx сохраняется.

BL-AI-105 [ ]: NLP над транскриптом (реальные text_features)

Цель: заменить эвристический блок в `modules/text/features.py` на модель/API (sentiment/topics/keyphrases) по согласованной схеме.
Файлы: `ai-gateway/modules/text/**`, `docs/ANALYSIS_WS_CONTRACTS.md`
Оценка: 3–10 дн
DoD: воспроизводимый офлайн-тест на корпусе фраз; поля в `text_analysis.payload` описаны в контракте.

BL-AI-106 [ ]: Diarization / привязка речи к участнику

Цель: транскрипт и отчёт отражают «кто сказал» без ручной разметки.
Файлы: `speech-service` или отдельный worker, `ai-gateway`, `emeeting-ui` (отображение)
Оценка: 2–4 нед
DoD: для записи с 2 спикерами корректное разделение в эталонном наборе; интеграция с `participant_id` или явным speaker_label в контракте.

BL-AI-107 [ ]: Экспорт метрик (Prometheus или аналог)

Цель: алерты по error-rate / latency / отставанию отчёта без ручного разбора логов.
Файлы: `ai-gateway/**`, `docs/ANALYSIS_OBSERVABILITY.md`, опционально sidecar
Оценка: 2–5 дн
DoD: dashboard или минимальный scrape target; описание ключевых метрик в доке.

BL-AI-108 [x]: Каталог `code/AI/` удалён из репозитория

Цель: убрать тяжёлые эталоны и бинарники из git; выводы по стеку зафиксированы в `docs/*`.
Файлы: (ранее `code/AI/**`)
Оценка: —
DoD: каталог отсутствует в рабочем дереве; документы обновлены (`docs/README.md`, `AI_MODULES_ACTION_PLAN.md`, этот беклог).

BL-AI-109 [ ]: CI: опциональный прогон hybrid/smoke на образе с AI

Цель: ловить регрессии контракта на пайплайне с реальными зависимостями (за флагом или nightly).
Файлы: `.github/workflows/ci.yml`, `ai-gateway/hybrid_pipeline_smoke.py`
Оценка: 1–3 дн
DoD: workflow документирован; не блокирует основной CI без железа/GPU.

BL-UX-110 [ ]: Отчеты v2 — подключение реальных AI-метрик в UI

Цель: убрать fallback-агрегацию и показывать содержательные отчеты по звонку и команде.
Файлы: `emeeting-ui/src/pages/Report.tsx`, `emeeting-ui/src/api/reports.ts`, `emeeting-backend/internal/report/**`
Оценка: 2–4 дн
DoD: `/reports` и `/reports/:id` работают на боевом payload, без debug-блока и мок-логики.

BL-BE-111 [ ]: Контракт отчетов под финальную НС (single/team/trends)

Цель: стабилизировать формат данных до подключения итоговой нейронки.
Файлы: `docs/api-contract.md`, `docs/ANALYSIS_WS_CONTRACTS.md`, `emeeting-backend/internal/report/**`, `ai-gateway/modules/report/**`
Оценка: 1–2 дн
DoD: описаны и реализованы endpoint-ы: `GET /reports/session/:sessionId`, `GET /reports/team`, `GET /reports/team/trends`.

BL-AI-112 [ ]: Транскрибация realtime без накопительного буфера на сервере

Цель: убрать искажения и шум от склейки чанков в длинный cumulative payload.
Файлы: `ai-gateway/adapters/speech_service.py`, `speech-service/main.py`, `ai-gateway/modules/text/transcription.py`
Оценка: 2–5 дн
DoD: ASR принимает короткие независимые чанки, итоговый текст стабильнее на длинной речи.
Статус: **в работе** — внедрено окно/шаг (`test.py` approach) и анти-дубли в `speech-service`, осталось стабилизировать edge-кейсы WebM на длинных сессиях и добавить метрики подавления/ошибок.

BL-BE-113 [ ]: История транскрибации в БД + REST endpoint

Цель: хранить полную историю распознавания и восстанавливать ее при перезаходе.
Файлы: `emeeting-backend/internal/session/**`, `emeeting-backend/migrations/*`, `emeeting-ui/src/pages/VideoMeet.tsx`
Оценка: 2–4 дн
DoD: `GET /sessions/:id/transcription` возвращает историю, UI подгружает ее перед live-обновлениями.
Статус: **частично** — UI подгружает историю через `/sessions/:id/analysis/events?module=text`; отдельный “чистый” endpoint транскрибации еще не выделен.

BL-AI-114 [ ]: Face Behavior submodule (landmarks/blendshapes/head pose)

Цель: выделить продвинутый трекинг поведения как отдельный подмодуль `face.behavior` без ломки текущего `face_analysis`.
Файлы: `ai-gateway/modules/face/**`, `docs/ANALYSIS_WS_CONTRACTS.md`, `ai-gateway/modules/registry.py`
Оценка: 3–6 дн
DoD: в конфиге можно включить/выключить `face.emotion` и `face.behavior` независимо; WS payload совместим с текущим фронтом.

BL-AI-115 [ ]: Контракт `face.behavior` v1 + quality flags

Цель: стандартизировать поля для отчетов и дальнейшего fusion.
Файлы: `docs/ANALYSIS_WS_CONTRACTS.md`, `ai-gateway/contracts.py`, `ai-gateway/modules/face/schema.py`
Оценка: 2–4 дн
DoD: описаны поля `blendshapes`, `head_pose`, `eye_state`, `smile`, `quality`; есть валидация и fallback при неполных данных.

BL-AI-116 [ ]: Report fusion — использовать behavior-сигналы в отчете

Цель: добавить в отчеты метрики вовлеченности/усталости/внимания на основе face behavior.
Файлы: `ai-gateway/modules/report/**`, `ai-gateway/feature_store.py`, `emeeting-ui/src/pages/Report.tsx`
Оценка: 4–8 дн
DoD: в `analysis_report` появляется блок `face_behavior_summary` (trend + participant breakdown), UI отображает его без debug режима.

BL-AI-117 [ ]: Конфигуратор модулей — provider layer (speech-service как backend text-module)

Цель: отразить в конфигураторе, что `speech-service` — провайдер модуля `text.transcription`, а не отдельная UI-фича.
Файлы: `ai-gateway/modules.default.json`, `ai-gateway/modules.docker.json`, `docs/UI_AI_ANALYSIS_PLAN.md`, `docs/README.md`
Оценка: 2–5 дн
DoD: в конфиге явно задаются `module` + `provider` + `provider params`; переключение провайдера не меняет внешний контракт `text_analysis`.