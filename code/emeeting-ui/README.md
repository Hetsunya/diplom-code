# eMeeting UI

Frontend application for eMeeting built with React, TypeScript, and Vite.

## Prerequisites

- Node.js 20+
- npm

## Configuration

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Main variables:
- `VITE_API_URL` - backend HTTP URL (default `http://localhost:8080`)
- `VITE_WS_URL` - backend WS base URL (default `ws://localhost:8080`)

## Development

```bash
npm install
npm run dev
```

App runs on `http://localhost:5173` by default.

## Quality checks

```bash
npm run lint
npm run build
```

## API expectations

UI depends on these backend routes:
- `POST /auth/login`
- `POST /auth/logout`
- `GET /sessions`
- `POST /sessions`
- `GET /sessions/:id`
- **`GET /sessions/:id/analysis/report`** — отчёт по аналитике встречи (организатор сессии)
- **`GET /sessions/:id/analysis/events`** — история событий аналитики (с ограничениями доступа)
- `GET /reports/:id` — legacy отчёт, если используется в backend
- `GET /ws/sessions/:id` (WebSocket)

Маршруты приложения: **`/reports`** (список/выбор), **`/reports/:sessionId`** (детализация). Фичи роутера: `src/config/features.ts`.

## Troubleshooting

- **Blank page or build failure**
  - Run `npm run lint` and fix errors first.
- **Network errors in browser**
  - Verify `VITE_API_URL` points to running backend.
- **WebSocket not connecting**
  - Verify `VITE_WS_URL` and backend WS endpoint availability.
- **CORS errors**
  - Set backend `CORS_ALLOW_ORIGIN` to UI origin.
