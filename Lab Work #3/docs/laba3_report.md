# Лабораторная работа №3

**Тема:** Использование принципов проектирования на уровне методов и классов  
**Цель работы:** Получить опыт проектирования и реализации модулей с использованием принципов KISS, YAGNI, DRY, SOLID и др.

## Выбранный вариант использования
Управление торговыми парами и порогами через admin-интерфейс с последующим `hot reload` конфигурации в `engine` без перезапуска контейнеров и публикацией актуальных арбитражных возможностей в пользовательский интерфейс.

## Диаграмма контейнеров (C4)
```mermaid
flowchart LR
    admin["Администратор<br/>[Person]<br/>Управляет парами и порогами"]
    user["Пользователь<br/>[Person]<br/>Смотрит арбитражные возможности"]

    subgraph system["CEX-DEX Parser MVP<br/>[Software System]"]
      direction LR
      fa["frontend-admin<br/>[Container: React + Vite + Nginx]<br/>Управление конфигурацией"]
      fu["frontend-user<br/>[Container: React + Vite + Nginx]<br/>Просмотр opportunities"]
      api["backend-api<br/>[Container: FastAPI]<br/>JWT, RBAC, REST API"]
      eng["engine<br/>[Container: Python Worker]<br/>Сбор цен, фильтрация, hot reload"]
      db["PostgreSQL<br/>[Container: Database]<br/>Конфиг, снимки цен, opportunities, users"]
    end

    mexc["MEXC API<br/>[External Software System]"]
    rpc["EVM RPC (Base/BSC)<br/>[External Software System]"]

    admin -->|HTTPS| fa
    user -->|HTTPS| fu
    fa -->|HTTPS/JSON| api
    fu -->|HTTPS/JSON| api
    api -->|SQL| db
    eng -->|Read/Write SQL| db
    eng -->|WS| mexc
    eng -->|JSON-RPC / WebSocket| rpc

    classDef person fill:#0b4f8c,color:#ffffff,stroke:#08365f,stroke-width:1px;
    classDef container fill:#2f80c9,color:#ffffff,stroke:#1d5d96,stroke-width:1px;
    classDef external fill:#8b8f94,color:#ffffff,stroke:#666a70,stroke-width:1px,stroke-dasharray: 4 3;
    class admin,user person;
    class fa,fu,api,eng,db container;
    class mexc,rpc external;
    style system fill:transparent,stroke:#2f80c9,stroke-width:2px,color:#0b4f8c;
```

Краткое пояснение:
- Детализируемый контейнер для диаграммы компонентов: `engine` (ядро бизнес-логики и применение принципов проектирования).

## Диаграмма компонентов (C4) для контейнера `engine`
```mermaid
flowchart TB
    db["PostgreSQL<br/>[Container: Database]"]
    mexc["MEXC API<br/>[External Software System]"]
    rpc["EVM RPC/WS<br/>[External Software System]"]

    subgraph engine["engine<br/>[Container: Python Worker]"]
      direction TB
      app["app.py<br/>[Component]<br/>Оркестратор цикла и reload"]
      store["PostgresStore<br/>[Component]<br/>Чтение/запись в БД"]
      cex["MexcClient<br/>[Component]<br/>Получение CEX цен"]
      factory["create_dex_source<br/>[Component]<br/>Фабрика DEX-источников"]
      dex["EvmDexSource + BaseDexRpcPricer<br/>[Component]<br/>Получение DEX цен"]
      qgate["SignalQualityGate<br/>[Component]<br/>Проверка качества сигнала"]
      ws["ChainWsMonitor<br/>[Component]<br/>Контроль WS-свежести"]
    end

    app -->|load/save config,data| store
    app -->|fetch mid| cex
    app -->|build source| factory
    factory --> dex
    app -->|check| qgate
    app -->|health state| ws
    store -->|SQL| db
    cex -->|REST| mexc
    dex -->|JSON-RPC| rpc
    ws -->|WebSocket| rpc

    classDef component fill:#2f80c9,color:#ffffff,stroke:#1d5d96,stroke-width:1px;
    classDef external fill:#8b8f94,color:#ffffff,stroke:#666a70,stroke-width:1px,stroke-dasharray: 4 3;
    classDef dbnode fill:#2a6ca8,color:#ffffff,stroke:#1d5d96,stroke-width:1px;
    class app,store,cex,factory,dex,qgate,ws component;
    class mexc,rpc external;
    class db dbnode;
    style engine fill:transparent,stroke:#2f80c9,stroke-width:2px,color:#0b4f8c;
```

Краткое пояснение:
- Компоненты разделены по ответственностям: получение данных (`MexcClient`, `EvmDexSource`), бизнес-валидация (`SignalQualityGate`), инфраструктура (`PostgresStore`, `ChainWsMonitor`), координация (`app.py`).

## Диаграмма последовательностей
```mermaid
sequenceDiagram
    actor A as Admin
    participant FA as frontend-admin
    participant API as backend-api
    participant DB as PostgreSQL
    participant ENG as engine
    actor U as User
    participant FU as frontend-user

    A->>FA: Изменяет pair/settings
    FA->>API: PATCH /api/admin/pairs|settings (JWT)
    API->>DB: UPDATE pairs/settings + bump config_version
    DB-->>API: OK (new config_version)
    API-->>FA: 200 OK

    loop каждые ENGINE_CONFIG_CHECK_INTERVAL_SEC
      ENG->>DB: SELECT settings.config_version
      DB-->>ENG: версия изменилась
      ENG->>DB: SELECT runtime config (pairs/chains/protocols)
      DB-->>ENG: обновленная конфигурация
    end

    loop polling
      ENG->>DB: UPSERT price_snapshot / INSERT opportunities
    end

    U->>FU: Открывает список opportunities
    FU->>API: GET /api/opportunities?limit=50 (JWT)
    API->>DB: SELECT opportunities
    DB-->>API: rows
    API-->>FU: JSON
```

Краткое пояснение:
- Последовательность демонстрирует главное поведение системы: изменение конфигурации через админ-панель и реакцию `engine` без рестарта.

## Модель БД (UML class diagram)
```mermaid
classDiagram
    class users {
      UUID id
      TEXT email
      TEXT password_hash
      TEXT role
      BOOLEAN is_active
      TIMESTAMPTZ created_at
    }

    class settings {
      INT id
      NUMERIC global_spread_threshold
      BIGINT config_version
      TIMESTAMPTZ updated_at
    }

    class chains {
      UUID id
      TEXT code
      TEXT kind
      TEXT rpc_http_url
      TEXT rpc_ws_url
      BOOLEAN ws_enabled
      NUMERIC poll_interval_sec
      BOOLEAN is_enabled
      JSONB meta
    }

    class venues {
      UUID id
      TEXT code
      TEXT kind
      TEXT network
      UUID chain_id
    }

    class dex_protocols {
      UUID id
      TEXT code
      TEXT chain_kind
      BOOLEAN is_enabled
      JSONB meta
    }

    class pairs {
      UUID id
      TEXT symbol
      TEXT network
      UUID cex_venue_id
      TEXT cex_symbol
      UUID dex_venue_id
      UUID protocol_id
      TEXT pool_address
      NUMERIC spread_threshold_override
      BOOLEAN is_enabled
      JSONB meta
    }

    class price_snapshot {
      UUID pair_id
      TEXT symbol
      TEXT network
      DOUBLE cex_price
      DOUBLE dex_price
      DOUBLE spread_pct
      JSONB details
      TIMESTAMPTZ updated_at
    }

    class opportunities {
      UUID id
      UUID pair_id
      TEXT symbol
      TEXT network
      DOUBLE cex_price
      DOUBLE dex_price
      DOUBLE spread_pct
      JSONB details
      NUMERIC quality_score
      TIMESTAMPTZ detected_at
    }

    chains "1" --> "0..*" venues : chain_id
    venues "1" --> "0..*" pairs : cex_venue_id / dex_venue_id
    dex_protocols "1" --> "0..*" pairs : protocol_id
    pairs "1" --> "0..1" price_snapshot : pair_id
    pairs "1" --> "0..*" opportunities : pair_id
```

Краткое пояснение:
- В БД реализовано больше 5 сущностей, включая конфигурационную часть (`chains`, `venues`, `dex_protocols`, `pairs`, `settings`) и операционную часть (`price_snapshot`, `opportunities`, `users`).
- Введены инварианты целостности на уровне БД:
  - `venues.network` синхронизируется из `chains.code` для `kind='dex'`, а для `kind='cex'` принудительно `NULL`;
  - `pairs.network` синхронизируется из сети `dex_venue_id`;
  - `pairs.cex_venue_id` обязан ссылаться на `venues.kind='cex'`;
  - `pairs.dex_venue_id` обязан ссылаться на `venues.kind='dex'` с валидной `chain_id`;


## Применение основных принципов разработки

### KISS
1. Конфигурация читается из окружения и валидируется простыми проверками в `load_settings()` (`services/backend-api/app.py`, `services/engine/app.py`).
2. Простая и понятная модель `hot reload`: сравнение `settings.config_version` без сложных механизмов синхронизации.

Фрагмент:
```python
if not database_url:
    raise RuntimeError("DATABASE_URL is required")
```

### YAGNI
1. В фабрике DEX-источников `ton` явно помечен как не реализованный, чтобы не усложнять MVP заранее.

Фрагмент (`services/engine/price_sources/dex/common/factory.py`):
```python
if chain_type == "ton":
    raise NotImplementedError("TonDexSource will be implemented on the next step")
```

### DRY
1. Единая логика авторизованных HTTP-запросов на фронтенде через функцию `apiRequest` (в обоих UI).
2. Повторно используемые SQL-шаблоны и `ON CONFLICT` для idempotent bootstrap/seed в backend и engine store.

Фрагмент (`services/frontend-user/src/App.jsx`):
```javascript
async function apiRequest(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  // ...
}
```

### SOLID
1. **S (Single Responsibility):**
`SignalQualityGate` отвечает только за правила качества сигнала, `PostgresStore` только за слой хранения, `MexcClient` только за интеграцию с CEX API.
2. **O (Open/Closed):**
DEX-источники расширяются через `create_dex_source` без изменения существующей логики вызова в оркестраторе.
3. **L (Liskov):**
Возврат из фабрики через общий контракт `DexPriceSource` позволяет взаимозаменять конкретные реализации.
4. **I (Interface Segregation):**
Небольшие модели запросов/ответов (`Pydantic`-классы) разделяют интерфейсы API по endpoint-ам.
5. **D (Dependency Inversion):**
Бизнес-уровень зависит от абстракций/контрактов (`DexPriceSource`, `Mapping`-конфиги), а не от конкретных протоколов напрямую.

Фрагмент (`services/engine/core/quality_gate.py`):
```python
class SignalQualityGate:
    def check(self, pair_id, pair_config, pair_state, now_ts):
        # фильтрация по качеству данных
        ...
```