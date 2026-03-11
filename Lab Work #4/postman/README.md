# Postman Tests

## Files

- `CEX-DEX-Backend.postman_collection.json` - коллекция с базовыми API-тестами.
- `local.postman_environment.json` - пример environment для локального запуска.

## What is covered

- Auth: `POST /api/auth/login`, `GET /api/auth/me`
- Admin reference: chains/venues/protocols
- Admin pairs: validate, create, patch, delete (soft)
- Admin settings: get + patch
- User: `GET /api/opportunities`

## Run in Postman UI

1. Import collection и environment.
2. Выбери environment `local`.
3. Проверь значения:
   - `baseUrl`
   - `adminEmail`
   - `adminPassword`
4. Запусти всю коллекцию через Collection Runner.

## Run in CLI (Newman)

```bash
npm i -g newman
newman run tests/postman/CEX-DEX-Backend.postman_collection.json \
  -e tests/postman/local.postman_environment.json
```

## Notes

- Коллекция автоматически сохраняет `accessToken` после login.
- Тест `Create Pair (test)` создает временную пару с рандомным символом.
- `Delete Pair (soft)` выключает созданную пару (`is_enabled=false`), физического удаления нет.
- `Patch Settings (no-op)` отправляет текущее значение `global_spread_threshold`.
