# ЛР4 — REST API (CEX/DEX Arbitrage Monitor)

## Запуск
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn src.server:app --reload
```

## Авторизация (демо)
Передавайте заголовок `X-API-Key`:

- `demo-user` — роль USER
- `demo-admin` — роль ADMIN
- `service-engine` — роль SERVICE (internal ingest)
- `service-notify` — роль SERVICE (internal ingest)

## OpenAPI
После запуска: `/docs` и `/openapi.json`
