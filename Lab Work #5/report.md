# Лабораторная работа №5

## Тема
Реализация архитектуры на основе сервисов (микросервисной архитектуры).

## Цель
Получить опыт организации взаимодействия сервисов с использованием контейнеров Docker.

## 1) Реализация контейнерной архитектуры 

В проекте реализована многоконтейнерная архитектура на `docker compose`.

Основные сервисы:
- `db` — PostgreSQL 16 (хранение пользователей, пар, настроек, opportunities, snapshots).
- `backend-api` — FastAPI (аутентификация, RBAC, admin API, user API).
- `frontend-user` — пользовательский интерфейс (React + Vite + nginx).

Дополнительно:
- `engine` — сервис расчета CEX/DEX спредов и записи сигналов в БД.
- `frontend-admin` — админ-панель (управление сетями, парами, настройками).

Файлы:
- `docker-compose.yml` — локальный запуск с build из исходников.
- `docker-compose.prod.yml` — production запуск из Docker Hub образов.

Демонстрация работоспособности:
1. Запуск:
```bash
docker compose up --build
```
2. Проверка UI:
- Docs: `http://localhost:8000/docs`
- User UI: `http://localhost:8080`
- Admin UI: `http://localhost:8081`
3. Проверка API:
- `POST /api/auth/login`
- `GET /api/opportunities`
- `GET /api/admin/pairs` (для admin роли)

## 2) Непрерывная интеграция CI 

Реализован workflow:
- `.github/workflows/ci.yml`

Что делает CI:
1. Checkout репозитория.
2. Подготовка `.env` для CI.
3. Сборка docker-образов сервисов (`backend-api`, `engine`, `frontend-user`, `frontend-admin`).
4. Подъем необходимых контейнеров (`db`, `backend-api`) для тестов.
5. Запуск smoke/integration тестов.
6. Сбор логов при ошибке и teardown окружения.

Итог: на каждый `push` в `main` автоматически выполняется проверка сборки и базовой работоспособности API.

## 3) Интеграционные тесты в CI 

Реализован скрипт:
- `tests/integration/api_smoke.sh`

Проверяемые сценарии:
1. Доступность backend (`/docs`).
2. Логин администратора (`/api/auth/login`).
3. Проверка токена (`/api/auth/me`).
4. Admin endpoint (`/api/admin/settings`, `/api/admin/pairs`).
5. User endpoint (`/api/opportunities?limit=5`).

Тесты встроены в CI workflow и запускаются автоматически.

## 4) Непрерывное развертывание CD 

Реализован workflow:
- `.github/workflows/cd.yml`

Схема CD:
1. По `push` в `main` собираются образы всех сервисов.
2. Образы публикуются в Docker Hub с тегами:
- `${GITHUB_SHA}`
- `latest`
3. Через SSH запускается деплой на сервер:
- `deploy/deploy.sh`
4. Сервер выполняет:
- `docker compose -f docker-compose.prod.yml pull`
- `docker compose -f docker-compose.prod.yml up -d --remove-orphans`

Требуемые GitHub Secrets:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_APP_DIR`

## 5) Вывод

Цель лабораторной работы достигнута:
- реализована и запущена микросервисная архитектура в Docker;
- настроен CI с автоматической сборкой и проверками;
- реализованы интеграционные API-тесты в пайплайне;
- настроен CD с публикацией образов в Docker Hub и автодеплоем на сервер.
