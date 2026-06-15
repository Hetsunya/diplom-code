# eMeeting Monorepo

## What is inside

- `code/emeeting-ui` - React + TypeScript frontend
- `code/emeeting-backend` - Go (Gin) backend API + WebSocket
- `code/ai-gateway` - Python gateway for WS/AI handlers (DeepFace, отчёты, вызов ASR)
- `code/speech-service` - HTTP ASR (stub или faster-whisper), см. `SPEECH_ASR_ENGINE`
- `docker-compose.yml` / `docker-compose.prod.yml` - оркестрация стека

## Документация

- **Индекс (`code/docs/README.md`):** контракты API/WS, наблюдаемость, планы UI и AI, ссылки на README сервисов.
- **Отчёты и хранение аналитики (`code/docs/REPORTS_AND_ANALYTICS_STORAGE.md`):** маршруты `/reports`, что пишется в БД, поля stub-отчёта, `face_debug` без persist.
- **Замена заглушек AI (`code/docs/AI_STUB_TO_PRODUCTION_ROADMAP.md`):** фазы и связь с беклогом **BL-AI-101…** в `code/cursor backlog.md`.
- **Беклог задач:** `code/cursor backlog.md`.

## Runbook: quick start (Docker Compose)

Requirements:
- Docker Desktop (or Docker Engine)
- Docker Compose plugin

1) Start stack **без** тяжёлого AI (db + backend + ui):

```bash
docker compose up --build
```

2) Опционально — **AI профиль** (speech-service + ai-gateway; первый запуск Whisper может долго качать модель):

```bash
docker compose --profile ai up --build
```

Переменные (опционально):

- `SPEECH_ASR_ENGINE=stub` — быстрый контрактный stub без распознавания (меньше CPU/RAM при сборке).
- `AI_GATEWAY_SESSION_ID` — ID комнаты WS (`SESSION_ID` в контейнере gateway), должен совпадать с тем же номером в URL встречи в UI (по умолчанию `1`).

В Docker gateway читает конфиг **`code/ai-gateway/modules.docker.json`** (`speech_service_url: http://speech-service:8090`). Локально без Compose используйте `modules.default.json` и свой URL.

3) Open services:
- UI: `http://localhost:5173`
- Backend API: `http://localhost:8080`
- Backend health: `http://localhost:8080/ws/health`
- Postgres: `localhost:5432`

4) Stop stack:

```bash
docker compose down
```

5) Reset DB data (fresh bootstrap):

```bash
docker compose down -v
```

## Runbook: local development (without Docker)

### Backend

```bash
cd code/emeeting-backend
go test ./...
go run ./cmd/server
```

Default backend URL: `http://localhost:8080`

### UI

```bash
cd code/emeeting-ui
npm install
npm run lint
npm run build
npm run dev
```

Default UI URL: `http://localhost:5173`
In dev mode Vite proxies `/api` and `/ws` to `http://localhost:8080`, so `VITE_API_URL=/api` and `VITE_WS_URL=/ws` work locally without extra env.

### AI gateway

```bash
cd code/ai-gateway
python -m pip install -r requirements.txt
export SESSION_ID=1   # совпадайте с id сессии в UI
python main.py
```

Конфиг модулей: по умолчанию `modules.default.json`; переопределение путём `AI_GATEWAY_MODULES_CONFIG=/path/to.json`.

### Speech service (ASR)

```bash
cd code/speech-service
python -m pip install -r requirements.txt
# опционально: export SPEECH_ASR_ENGINE=whisper  (нужен ffmpeg)
uvicorn main:app --host 0.0.0.0 --port 8090
```

Подробнее: `code/speech-service/README.md`.

## Database migrations

- Versioned SQL migrations live in:
  - `code/emeeting-backend/migrations/up`
  - `code/emeeting-backend/migrations/down`
- On fresh startup, `docker compose` auto-applies only `up` scripts via `/docker-entrypoint-initdb.d`.
- Rollback instructions are documented in `code/emeeting-backend/migrations/README.md`.

## Verify checklist

- `docker compose up --build` starts all services without crash loops.
- `GET http://localhost:8080/ws/health` returns status `ok`.
- UI opens and can call backend endpoints (`/sessions`, `/auth/login`, `/sessions/:id/analysis/report` для организатора, страницы `/reports`).
- Backend tests pass locally: `go test ./...`.
- UI quality checks pass locally: `npm run lint && npm run build`.
- Для AI-пайплайна (профиль `ai`) в live-сессии появляются WS события `text_analysis` и `audio_analysis`.
- `analysis_report_partial` в gateway нормализуется по стабильной структуре перед отправкой в UI.

## Debug guide

- **Backend fails to connect DB**
  - Check `POSTGRES_DSN` in compose/env.
  - Ensure DB container is healthy before backend start.
- **UI cannot reach API or WS**
  - Check `VITE_API_URL` and `VITE_WS_URL`.
  - Verify backend exposed on port `8080`.
- **WS closes immediately**
  - Confirm `GET /ws/sessions/:id` is reachable.
  - Check backend logs for upgrade errors.
- **AI profile is up, but no transcript**
  - Verify `docker compose --profile ai ps` shows healthy `speech-service`.
  - Ensure meeting URL session id matches `AI_GATEWAY_SESSION_ID`.
  - Temporarily set `SPEECH_ASR_ENGINE=stub` to isolate ASR performance/model issues.
- **DB schema missing**
  - Reset volumes (`docker compose down -v`) and start again.
  - Verify scripts exist in `migrations/up`.

## Environment variables

- Backend config in compose:
  - `POSTGRES_DSN`
  - `SERVER_PORT`
  - `CORS_ALLOW_ORIGIN`
- UI config in compose:
  - `VITE_API_URL`
  - `VITE_WS_URL`
    - path prefix mode (`/ws`) or absolute ws base (`ws://host:port`)
- AI gateway config in compose:
  - `BACKEND_WS_BASE_URL`
  - `SESSION_ID` (или `AI_GATEWAY_SESSION_ID` в корневом `docker-compose.yml`)
  - `AI_GATEWAY_MODULES_CONFIG` (в образе с Compose: `/app/modules.docker.json`)
  - `AI_GATEWAY_CONFIG_POLL_SEC` (период опроса файла конфига для hot-reload; в prod см. `docker-compose.prod.yml`)
- Speech service (`--profile ai`):
  - `SPEECH_ASR_ENGINE` (`stub` | `whisper`)
  - `WHISPER_MODEL_SIZE` (например `base`, `tiny`)

## Seed users (demo auth)

Демо пользователи хранятся в таблице `auth_user` (пароли — **bcrypt** в `password_hash`; при необходимости при первом входе выполняется rehash со старых схем).

1. `demo1@example.com` / `demo1pass`
2. `demo2@example.com` / `demo2pass`

В UI поля логина/пароля по умолчанию заполнены для пользователя `demo1`.

TODO: будет cookie-based auth (HttpOnly cookie / session token) вместо хранения только `isAuthenticated` в frontend state.

---

## Production (VDS) deploy

### Requirements
- A VDS with Docker Engine + Docker Compose plugin
- A domain name pointing to your VDS IP (A/AAAA records)
- Open ports **80** and **443** in firewall/security group

### Files
- `docker-compose.prod.yml` – production stack (db + backend + ui + caddy)
- `Caddyfile` – HTTPS + reverse proxy
- `.env.prod.example` – example environment file

### AI на проде

Те же сервисы, что и локально, включаются профилем **`ai`**:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod --profile ai up -d --build
```

Без профиля поднимаются только db, backend, ui, caddy. Убедитесь, что ресурсов хватает под Whisper (CPU/RAM) или задайте `SPEECH_ASR_ENGINE=stub`.

### Deploy steps

1) Copy `.env.prod.example` to `.env.prod` and fill values:
- `DOMAIN` (your domain)
- `JWT_SECRET` (generate a long random string)
- `POSTGRES_PASSWORD`

2) Start the stack:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

3) Open the app:
- `https://<DOMAIN>/`

### Notes
- **Camera/mic**: `getUserMedia` works on `https://<DOMAIN>` and on `http://localhost` (browser secure-context rules).
- **Caddy TLS**: certificates are stored in `caddy_data` volume.
