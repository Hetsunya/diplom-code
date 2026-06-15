# eMeeting Monorepo — контекст для агентов

Рабочая область Cursor часто открыта на каталоге **`code/`** внутри репозитория; пути ниже указаны **от корня монорепозитория** (`diplom/`), как в CI и Docker.

## Архитектура

| Компонент | Путь | Стек |
|-----------|------|------|
| Frontend | `code/emeeting-ui` | React 19, TypeScript, Vite, TanStack Query, Zustand |
| Backend | `code/emeeting-backend` | Go, Gin, gorilla/websocket, PostgreSQL |
| AI Gateway | `code/ai-gateway` | Python 3.11, WebSocket-пайплайн аналитики (face, audio, text, отчёты) |
| ASR | `code/speech-service` | HTTP `/v1/transcribe`: режимы `stub` и `whisper` (faster-whisper) |

Оркестрация: `docker-compose.yml` / `docker-compose.prod.yml` в корне репозитория.

## Текущее состояние (актуально, аудит 2026-06-10)

- **Аутентификация:** bcrypt, JWT HS256 (`access_token`/`refresh_token` cookies), ротация refresh. Код: `code/emeeting-backend/internal/auth/`.
- **Встречи / сессии:** runtime — `internal/session` (WS hub). Пакет `internal/meeting` (state machine, participants DB) **существует, но не подключён к серверу** — приоритет BL-MEET-WIRE.
- **AI:** `code/ai-gateway/modules/` (face, audio, text, report); ASR — `code/speech-service`.
- **Документация:** `code/docs/README.md`; бэклог — `code/cursor backlog.md`; сверка статусов — `.cursor/BACKLOG_SYNC.md`.
- **Правила:** `.cursor/rules/monorepo-standards.mdc` (всегда), `meeting-service.mdc`, `auth-system.mdc`.

## Команды

```bash
# Корень репозитория (diplom/)
docker compose up --build

# Backend
cd code/emeeting-backend && go test ./... && go vet ./... && go build ./...

# Frontend
cd code/emeeting-ui && npm ci && npm run lint && npm run test && npm run build
```

## Соглашения

- Миграции БД: SQL в `code/emeeting-backend/migrations/up` и `down`.
- Новые документы продуктового уровня — в `code/docs/`, ссылка из `docs/README.md`.
- Не добавлять в git тяжёлые бинарники и полные клоны сторонних ML-проектов; достаточно ссылок и описания в документации.
