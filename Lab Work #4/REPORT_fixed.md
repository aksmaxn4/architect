# Лабораторная работа №4 — Проектирование REST API
**Тема:** Проектирование REST API  
**Сервис:** Backend API системы мониторинга арбитражных ситуаций между CEX и DEX  

---

## 1. Принятые проектные решения (12)

1. **Ресурсный дизайн**: 1:1 соответствие ресурсам ERD (User, Exchange, TradingPair, CurrentPrice, ArbitrageOpportunity, NotificationRule, NotificationChannel, AlertLog).  
2. **Версионирование**: публичное API `/api/v1`, внутреннее `/internal/v1`.  
3. **Разделение публичного и внутреннего контуров**: запись котировок/оппортьюнити/логов — только internal endpoints (SERVICE ключ).  
4. **RBAC**: роли USER/ADMIN/SERVICE; админские операции (CRUD Exchange/Pair) изолированы.  
5. **User-scope**: `notification-*` и `alert-logs` всегда ограничены текущим пользователем (по `userId`).  
6. **Фильтрация и пагинация**: стандартные query-параметры (`limit`, `fromTs`, `toTs`, `minSpreadPct`).  
7. **Стандартизация ошибок**: 401 для отсутствия ключа, 403 для запрета, 404 для отсутствия ресурса.  
8. **Идемпотентность**: PUT для полного обновления Exchange; PATCH для частичного обновления Channel/Rule.  
9. **Форматы данных**: JSON в запросах/ответах; экспорт возможностей — JSON/CSV.  
10. **Единое время**: все временные метки в UTC (`datetime` в ISO 8601).  
11. **Нормализация справочников**: Exchange и TradingPair отделены от цен/возможностей.  
12. **Готовность к event-driven**: internal ingest сочетается с публикацией событий в брокер.

---

## 2. Документация по API (кратко)

Полное описание доступно через OpenAPI: `/docs`.

### Публичное API (пример)

- `GET /api/v1/exchanges` — список бирж  
- `POST /api/v1/notification-rules` — создать правило уведомлений  
- `GET /api/v1/opportunities?minSpreadPct=0.5` — список арбитражных возможностей  
- `GET /api/v1/opportunities/export?format=csv` — экспорт  

### Внутреннее API (пример)

- `POST /internal/v1/prices` — ingest котировок (Engine)  
- `POST /internal/v1/opportunities` — ingest возможностей (Engine)  
- `POST /internal/v1/alert-logs` — запись факта отправки (Notifications)  

---

## 3. Тестирование API

Тестирование выполняется в Postman.

В переменные окружения были добавлены следующие значения:

![Переменные окружения](postman_screenshots/env_vars.png)

---

### 01 Health-check

![01 Health-check](postman_screenshots/01_health.png)

---

### 02 Exchange — пользователь получает список

![02 User GET Exchanges](postman_screenshots/02_user_get_exchanges.png)

---

### 03 Exchange — пользователь пытается создать (403)

![03 User POST Exchange](postman_screenshots/03_user_creates_exchange.png)

---

### 04 Exchange — администратор создаёт биржу (201)

![04 Admin POST Exchange](postman_screenshots/04_admin_creates_exchange.png)

---

### 05 Pairs — администратор создаёт торговую пару

![05 Admin POST Pair](postman_screenshots/05_admin_creates_pair.png)

---

### 06 Pairs — пользователь получает список

![06 User GET Pairs](postman_screenshots/06_user_gets_pairs.png)

---

### 07 Internal — сервис создаёт котировку

![07 Service POST Price](postman_screenshots/07_service_creates_quotation.png)

---

### 08 Internal — пользователь пытается вызвать сервисный endpoint (403)

![08 User POST Price](postman_screenshots/08_user_creates_quotation.png)

---

### 09 Opportunities — сервис создаёт арбитражную возможность

![09 Service POST Opportunity](postman_screenshots/09_service_creates_opportunity.png)

---

### 10 Opportunities — пользователь получает список

![10 User GET Opportunities](postman_screenshots/10_user_gets_opportunities.png)

---

### 11 Notification Channel — пользователь создаёт канал

![11 User POST Notification Channel](postman_screenshots/11_user_creates_notif_channel.png)

---

### 12 Notification Rule — пользователь создаёт правило

![12 User POST Notification Rule](postman_screenshots/12_user_creates_notif_rule.png)

---

## 4. Что реализовано

- Реализованы методы **GET/POST/PUT/DELETE**  
- Реализовано разграничение ролей USER / ADMIN / SERVICE  
- Реализована фильтрация и обработка ошибок  
- Разделены публичный и внутренний контуры API  
