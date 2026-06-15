# Backlog Sync — аудит 2026-06-10

Сверка `code/cursor backlog.md` с фактическим состоянием репозитория.  
Обновлять после закрытия задач или крупных рефакторингов.

## Треки релиза (без изменений)

| Track | Задачи | Статус |
|-------|--------|--------|
| **A — Release Gate** | BL-025, BL-027, BL-029, BL-UX-110, BL-BE-111, BL-BE-113 | Частично |
| **B — Prod Stabilization** | BL-AI-101, BL-AI-112, BL-AI-109, BL-AI-107 | В плане / частично |
| **C — Post-Prod R&D** | BL-AI-102…106, BL-AI-114…117 | Ожидает |

---

## ✅ Выполнено (и интегрировано)

| ID | Задача | Примечание |
|----|--------|------------|
| BL-001 | API contract v1 | `code/docs/api-contract.md`, модули в `main.go` |
| BL-003 | Backend без пустых заготовок | auth, session, ws реализованы |
| BL-006 | docker-compose локально | корневой `docker-compose.yml` |
| BL-008 | README / runbook | корневой `README.md`, `code/docs/README.md` |
| BL-009 | Модульная регистрация роутов | `internal/*/module.go` |
| BL-010 | Интерфейсы session/auth | `contracts.go` |
| BL-011 | Registry WS dispatch | `ws_handler.go` map handlers |
| BL-012 | Плагинный AI-pipeline | `modules/registry.py` + shims |
| BL-021 | bcrypt пароли | + rehash SHA-256 legacy |
| BL-022 | Refresh rotation | `refresh_tokens` + тесты |
| BL-026 | Prod compose + `.env.prod.example` | Caddy, volumes |
| BL-028 | AI gateway service token | `/auth/token`, Bearer WS |
| BL-030 | Layout `ai-gateway/modules/` | единая папка модулей |
| BL-031 | Text module v1 | normalize + speech adapter + тесты |
| BL-033 | Face module v2 | quality guards, schema |
| BL-034 | Report orchestrator v1 | fusion, final on cancel |
| BL-036 | E2E hybrid contour | `hybrid_pipeline_smoke.py`, contract tests |
| BL-037 | AI prod readiness baseline | hot-reload, semaphore, health |
| BL-038 | Live транскрипт UI | `MeetingTranscriptRail` |
| BL-039 | Чат отдельно от ASR | `MeetingChatSection` + REST/WS |
| BL-041 | Убрать «AI analyzing…» | состояния лица в `VideoMeet` |
| BL-013 | Feature-config UI | `src/config/features.ts` |
| BL-019 | Meeting store + WS hook | Zustand + `useMeetingWebSocket` |
| BL-020 | UI реакции на WS | join/leave, toasts, redirect |
| BL-AI-108 | Удалён `code/AI/` | доки в `code/docs/` |

---

## 🔄 В процессе / Требует рефакторинга

| ID | Задача | Расхождение с бэклогом | Следующий шаг |
|----|--------|------------------------|---------------|
| BL-002 | Env без хардкода | default DSN/JWT в `main.go` | Вынести в `.env.example`, убрать dev-пароли из кода |
| BL-004 | Backend autotests | нет coverage gate, meeting tests изолированы | Интеграционные тесты + wire meeting |
| BL-005 | CI lint+test+build | Go без golangci-lint; ai-gateway только compileall | pytest + опц. golangci-lint |
| BL-007 | Миграции | README до 007, есть 009 | Обновить `migrations/README.md` |
| BL-014…018 | Meeting state machine | подключено к WS (`meeting_wire.go`) | host_started, DB join/leave/end |
| BL-015 | Participants DB | таблица есть, runtime — только hub | Join/Leave через meeting repo |
| BL-016 | WS events | нет `host_started`, `user_removed` | Добавить события + тесты |
| BL-017 | Reconnect | WS-only, без DB rejoin | Rejoin через meeting service |
| BL-018 | onClose host rule | WS broadcast без DB status | `EndMeeting()` + persist |
| BL-023 | HttpOnly cookies | `access_token`/`refresh_token`, не `session_token` | Синхронизировать docs/rules |
| BL-024 | Middleware + audit | `RequireRole` не на роутах; нет refresh/logout audit | Дописать `auth_events` |
| BL-025 | HTTPS / reverse proxy | compose готов, DNS/VDS вручную | Чеклист деплоя на VDS |
| BL-027 | Auth hardening prod | SameSite эвристика есть | E2E тест F5 + cookie policy |
| BL-029 | Observability | health/ready/metrics есть | RED-метрики, алерты |
| BL-032 | Audio v1 | эвристики по сырым байтам | Документировать v1 limits или decode v2 |
| BL-035 | Analysis RBAC | organizer vs guest, не host/co-host | Роли из meeting_participant |
| ~~BL-040~~ | Вердикт UI | реализовано в `VideoMeet` + `MeetingTranscriptRail` | — |
| BL-UX-110 | Report UI v2 | single API есть; team mock, debug JSON | Убрать stub UX, team API |
| BL-BE-111 | Контракт отчётов team/trends | только stub `/reports/:id` | Новые endpoints + docs |
| ~~BL-BE-113~~ | История транскрибации | endpoint + UI через `getSessionTranscription` | — |
| BL-AI-112 | Realtime ASR без буфера | window/step в speech-service; UI шлёт growing WebM | Независимые чанки end-to-end |
| BL-AI-117 | Provider layer config | gateway JSON богатый; UI — boolean flags | Configurator + `text.transcription` |

---

## 📌 Ожидает (приоритетные следующие шаги)

### P0 — Release Gate (Track A)

| ID | Задача | Оценка |
|----|--------|--------|
| ~~BL-MEET-WIRE~~ | Подключить `internal/meeting` к session/WS | **сделано 2026-06-10** |
| BL-UX-110 | Report UI без моков и debug-блоков | 2–4 дн |
| BL-BE-111 | `GET /reports/session/:id`, `/team`, `/team/trends` | 1–2 дн |
| ~~BL-BE-113~~ | `GET /sessions/:id/transcription` + UI | **сделано 2026-06-10** |
| ~~BL-040~~ | Live verdict panel (`analysis_report_partial`) | **сделано 2026-06-10** |
| BL-025 | VDS checklist: DNS, TLS, getUserMedia smoke | 1 дн |
| BL-027 | Cookie/auth E2E на prod origin | 0.5–1 дн |
| BL-029 | Минимальные алерты / runbook observability | 1 дн |

### P1 — Stabilization (Track B)

| ID | Задача | Оценка |
|----|--------|--------|
| BL-AI-112 | Стабилизировать realtime ASR (WebM edge cases) | 2–5 дн |
| BL-AI-101 | Production ASR engine + метрики WER/latency | 3–10 дн |
| BL-AI-109 | CI: pytest ai-gateway + nightly hybrid smoke | 1–3 дн |
| BL-AI-107 | Prometheus scrape / dashboard AI | 2–5 дн |
| ~~BL-024~~ (частично) | auth audit refresh/logout | **сделано 2026-06-10** | RequireRole на роутах — остаётся |
| BL-005 | Усилить CI (golangci-lint, pytest) | 1 дн |

### P2 — Post-Prod R&D (Track C, не в активный спринт)

BL-AI-102, BL-AI-103, BL-AI-104, BL-AI-105, BL-AI-106, BL-AI-114…117

---

## Критические находки аудита

1. **`internal/meeting` — мёртвый код**: тесты зелёные, runtime использует только `session/hub` + WS.
2. **BL-040 помечена ✅, вердикт не реализован**: CSS есть, обработчиков WS нет.
3. **`.cursor/rules/auth-system.mdc` устарел**: `session_token`, RS256, Strict — не совпадают с кодом.
4. **Два слоя отчётов**: `internal/analysis` (реальный) vs `internal/reports` (stub legacy).
