# Документация проекта (индекс)

Единая точка входа для текстов в каталоге `code/docs/` и смежных памяток. **Монорепозиторий:** в корне репозитория лежат `docker-compose.yml`, `docker-compose.prod.yml`, `.env.prod.example`; основной код и эта документация — в каталоге **`code/`**.

## Обзор сервисов

| Документ | Назначение |
|----------|------------|
| [Корневой README](../../README.md) | Runbook Docker / локальный запуск, переменные окружения, прод VDS |
| [emeeting-ui/README.md](../emeeting-ui/README.md) | Фронтенд |
| [emeeting-backend/migrations/README.md](../emeeting-backend/migrations/README.md) | Миграции БД и откат |
| [speech-service/README.md](../speech-service/README.md) | HTTP ASR (`/v1/transcribe`) |
| [ai-gateway/MEMO.md](../ai-gateway/MEMO.md) | Конфиг модулей gateway, поток WS, smoke-тесты |

## Контракты и аналитика

| Документ | Назначение |
|----------|------------|
| [api-contract.md](./api-contract.md) | REST v1 (UI ↔ backend) |
| [**REPORTS_AND_ANALYTICS_STORAGE.md**](./REPORTS_AND_ANALYTICS_STORAGE.md) | Отчёты UI (`/reports`), REST отчёта, матрица persistence (`analysis_event` vs `face_debug`), поля stub-отчёта |
| [ANALYSIS_WS_CONTRACTS.md](./ANALYSIS_WS_CONTRACTS.md) | WS-события аналитики v1 (`text_analysis`, `face_analysis`, отчёты, legacy `emotion`) |
| [ANALYSIS_OBSERVABILITY.md](./ANALYSIS_OBSERVABILITY.md) | Логи, счётчики, latency, hot-reload конфига, `data_quality` в отчётах |
| [UI_AI_ANALYSIS_PLAN.md](./UI_AI_ANALYSIS_PLAN.md) | План UI (транскрипт, чат, вердикт) |
| [AI_MODULES_ACTION_PLAN.md](./AI_MODULES_ACTION_PLAN.md) | Что оставить / доработать / не удалять в AI-стеке |
| [**AI_STUB_TO_PRODUCTION_ROADMAP.md**](./AI_STUB_TO_PRODUCTION_ROADMAP.md) | План замены заглушек на продуктовые модели и связка с беклогом BL-AI-* |

Каталог **`code/AI/`** (черновики исследований, эталонные репозитории, бинарники) **удалён из репозитория** для уменьшения размера клонов; выводы по выбору стека отражены в `docs/*` и в тексте ВКР при необходимости.

## Трекер задач

| Файл | Назначение |
|------|------------|
| [cursor backlog.md](../cursor%20backlog.md) | Приоритизированный беклог, включая блок **«AI: от заглушек к продакшену»** (BL-AI-101…) |

## Короткие локальные памятки

| Файл | Назначение |
|------|------------|
| [ai-gateway/CONTRACTS.md](../ai-gateway/CONTRACTS.md) | Краткий напоминатель по контрактам рядом с кодом gateway |

---

*Индекс обновляется при добавлении новых документов в `docs/` или смене ролей файлов. Пути в таблицах — относительно каталога `code/` репозитория.*
