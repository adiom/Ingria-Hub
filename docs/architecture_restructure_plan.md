# Ingria Hub – План реструктуризации

## Карта текущей архитектуры
FastAPI-приложение `main.py` держит HTTP API, напрямую создает SQLAlchemy-сессию и управляет пайплайном диалога: загрузка файлов, обращение к Google Gemini, сохранение `Memory` через `MemoryService` и `BlockchainService`. Параллельно существуют самостоятельные сценарии (`live.py`, `telegram_bot.py`, `migrate_*.py`), которые копируют настройки, инициируют собственные подключения к БД и повторяют правила генерации ответов.

Данные моделируются в `db.py` (SQLAlchemy Base). Сервисы памяти и блокчейна живут в одном файле каждый, комбинируя доменную логику, доступ к БД и форматирование. UI представлен статическими страницами `frontend/*.html` + `style.css`. Кросс-срезы: конфигурация и креды «зашиты» в код, логирование разбросано `print`-ами, тесты — скрипты на Python без общего раннера.

## Риски и технический долг
1. Хардкоды API ключей и строк подключения в нескольких файлах — риск утечки и сложность деплоя.
2. Отсутствие пакета/модуля настроек: каждый скрипт поднимает собственный `SessionLocal`, невозможно управлять транзакциями централизованно.
3. Доменные сервисы смешивают работу с БД, блокчейн и форматирование текста — сложно тестировать и переиспользовать.
4. Дублированные системные инструкции и логика памяти между `main.py`, `live.py`, `live_tools.py` → расходящиеся поведения.
5. Скрипты `test_*.py` и runtime-код лежат рядом в корне, нет четкого разделения на prod и tooling.
6. UI хранится как чистая статика без сборки, но обслуживается тем же процессом, что и API, что мешает дальнейшему развитию фронтенда.
7. Нет единого слоя инфраструктуры (брокеры, сторонние API), поэтому интеграции сложно мокать и заменять.

## Целевая структура директорий
```text
ingria_hub/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── memories.py      # HTTP-эндпоинты
│   │   │       └── blockchain.py
│   │   ├── dependencies.py          # Depends: session, services
│   │   ├── config.py                # Pydantic Settings
│   │   └── main.py                  # FastAPI factory
│   ├── domain/
│   │   ├── memories/
│   │   │   ├── models.py            # dataclass + правила
│   │   │   ├── repository.py        # работа с БД
│   │   │   └── service.py           # бизнес-логика
│   │   ├── blockchain/service.py
│   │   └── live/session.py
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── base.py              # Base, metadata
│   │   │   ├── session.py           # SessionLocal
│   │   │   └── migrations/
│   │   └── integrations/
│   │       ├── gemini/client.py
│   │       └── telegram/bot.py
│   ├── interfaces/
│   │   ├── cli/
│   │   └── workers/
│   └── frontend/                    # отдельный пакет → CDN/SPA
├── scripts/
│   ├── maintenance/
│   └── experiments/
├── tests/
│   ├── api/
│   ├── domain/
│   └── integration/
└── pyproject.toml
```
Правила импорта: `app` зависит только от `domain` и `infrastructure`; `domain` не знает про FastAPI и внешние клиенты; `infrastructure` предоставляет адаптеры для `domain`; `interfaces` (CLI, боты) используют `app` и `domain` через зависимости.

## План миграции
**MVP.**
- Ввести `src/`-пакет, перенести `db.py` в `infrastructure/db/base.py`, добавить `session.py` и единый `get_session()`.
- Создать `app/config.py` на Pydantic Settings, заменить хардкоды в `main.py`, `live.py`, `telegram_bot.py` на зависимости.
- Разделить `MemoryService` на `domain.memories.service` (бизнес) и `repository` (SQLAlchemy), переписать FastAPI-эндпоинт на использование DI.

**Стабилизация.**
- Выделить HTTP-роутеры (`app/api/v1/*.py`) и фабрику `create_app()`; подключить middleware, единый логгер.
- Обновить `live.py` и другие сценарии до использования новых сервисов + общей конфигурации.
- Переместить тестовые скрипты в `tests/` и оформить pytest-настройки, добавить docker-compose для локальной БД.

**Улучшения.**
- Упаковать фронтенд в отдельный build (например, Vite/React) и отдавать как статический артефакт из CDN.
- Добавить слой событий (например, сохранение памяти → очередь) и метрики.
- Настроить CI/CD (lint + tests), интегрировать pre-commit, ввести миграции Alembic.

## Механические преобразования
- Создать `pyproject.toml`, объявить пакет `ingria_hub` с `src/` layout.
- Автоматический `sed`/скрипт для замены прямых `SessionLocal()` на импорт из `app.dependencies.get_session`.
- Выделить общие системные инструкции в `domain/memories/prompts.py` и подключить их в `main.py`/`live.py`.
- Перенести статические файлы в `src/frontend` и обновить `StaticFiles` путь.
- Добавить `.env.example` и заменить прямые ключи на `settings.google_api_key`.
- Разбить `MemoryService`/`BlockchainService` на интерфейсы + реализации, покрыть unit-тестами.

## Quick Wins
- Вынести строки подключения и ключи в `.env.example`, подключить через Pydantic Settings (≤1 ч).
- Настроить единый `logging` конфиг вместо `print` (создать `logging.ini`, обновить импорты) — 1 ч.
- Привести `requirements.txt` и `package.json` к актуальным зависимостям, удалить неиспользуемые тестовые скрипты (быстрый аудит) — 1–2 ч.
- Добавить `Makefile` с командами `run-api`, `run-tests`, `lint` для упрощения входа — 1 ч.
- Перенести тестовые сценарии в `tests/manual/` и описать в README, чтобы разгрузить корень — 1 ч.
