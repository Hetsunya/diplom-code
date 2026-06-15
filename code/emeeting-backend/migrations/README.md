# DB migrations

Versioned migrations are stored in:
- `migrations/up` - forward migrations
- `migrations/down` - rollback migrations

Current version (see `migrations/up`):
- through `007_analysis` (`analysis_event`, `analysis_report` tables for WS analytics persistence)
- `008_session_chat` (`session_chat_message` for meeting text chat history)

## Auto-apply on fresh DB

`docker-compose.yml` mounts only `migrations/up` into `/docker-entrypoint-initdb.d`, so new databases are initialized automatically from the latest `up` scripts.

## Manual apply

From repository root:

```bash
# пример: выполнить forward-миграции вручную (если нужно)
# docker-entrypoint-initdb.d содержит только mounted скрипты, а в проде/локально путь может отличаться
docker compose exec db psql -U postgres -d emeeting -f /docker-entrypoint-initdb.d/001_init.sql
docker compose exec db psql -U postgres -d emeeting -f /docker-entrypoint-initdb.d/002_auth_users.sql
```

## Manual rollback

Rollback is kept in source under:
- `code/emeeting-backend/migrations/down/001_init.sql`
- `code/emeeting-backend/migrations/down/002_auth_users.sql`

Run from host (example with local psql):

```bash
psql "postgres://postgres:1040@localhost:5432/emeeting?sslmode=disable" -f code/emeeting-backend/migrations/down/001_init.sql
# откатить в обратном порядке при наличии нескольких версий:
# psql ... -f code/emeeting-backend/migrations/down/002_auth_users.sql
# psql ... -f code/emeeting-backend/migrations/down/001_init.sql
```
