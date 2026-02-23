"""
ЛР №4 — Проектирование и реализация REST API (FastAPI)
Предметная область: мониторинг арбитражных ситуаций между CEX и DEX.

Внимание:
- Это учебная реализация (in-memory хранилище), моделирующая сущности согласно ERD:
  User, Exchange, TradingPair, CurrentPrice, ArbitrageOpportunity,
  NotificationRule, NotificationChannel, AlertLog.
- Публичное API: /api/v1/*
- Внутреннее API (для сервисов/воркеров): /internal/v1/*

Запуск:
  python -m venv .venv
  source .venv/bin/activate          # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  uvicorn src.server:app --reload

Простая авторизация (демо):
  X-API-Key: demo-user    -> роль USER (свои настройки + чтение арбитража)
  X-API-Key: demo-admin   -> роль ADMIN (управление биржами/парами)
  X-API-Key: service-engine -> SERVICE (internal: запись цен/оппортьюнити)
  X-API-Key: service-notify -> SERVICE (internal: запись логов уведомлений)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, condecimal, constr, conint


# -----------------------------
# App
# -----------------------------
app = FastAPI(
    title="CEX/DEX Arbitrage Monitor API",
    version="2.0.0",
    description="REST API для системы мониторинга арбитражных ситуаций между CEX и DEX.",
)

API_PREFIX = "/api/v1"
INTERNAL_PREFIX = "/internal/v1"


# -----------------------------
# Auth / RBAC (demo)
# -----------------------------
class Role(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SERVICE = "SERVICE"


API_KEYS: Dict[str, Role] = {
    "demo-user": Role.USER,
    "demo-admin": Role.ADMIN,
    "service-engine": Role.SERVICE,
    "service-notify": Role.SERVICE,
}


def get_role(x_api_key: Optional[str]) -> Role:
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return API_KEYS[x_api_key]


def require_roles(role: Role, allowed: List[Role]) -> None:
    if role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------
# Domain enums
# -----------------------------
class ExchangeType(str, Enum):
    CEX = "CEX"
    DEX = "DEX"


class ChannelType(str, Enum):
    TELEGRAM = "TELEGRAM"
    EMAIL = "EMAIL"


class SendStatus(str, Enum):
    SENT = "SENT"
    FAILED = "FAILED"


# -----------------------------
# ERD models (DTO)
# -----------------------------
class UserDTO(BaseModel):
    id: UUID
    email: constr(min_length=3, max_length=200)
    telegramId: Optional[constr(min_length=3, max_length=64)] = None
    createdAt: datetime


class UserPatchDTO(BaseModel):
    email: Optional[constr(min_length=3, max_length=200)] = None
    telegramId: Optional[constr(min_length=3, max_length=64)] = None


class ExchangeDTO(BaseModel):
    id: UUID
    name: constr(min_length=2, max_length=120)
    type: ExchangeType
    network: Optional[constr(min_length=2, max_length=80)] = None


class ExchangeCreateDTO(BaseModel):
    name: constr(min_length=2, max_length=120)
    type: ExchangeType
    network: Optional[constr(min_length=2, max_length=80)] = None


class TradingPairDTO(BaseModel):
    id: UUID
    base: constr(min_length=1, max_length=20)
    quote: constr(min_length=1, max_length=20)


class TradingPairCreateDTO(BaseModel):
    base: constr(min_length=1, max_length=20)
    quote: constr(min_length=1, max_length=20)


class CurrentPriceDTO(BaseModel):
    id: UUID
    exchangeId: UUID
    pairId: UUID
    bid: condecimal(max_digits=24, decimal_places=10)
    ask: condecimal(max_digits=24, decimal_places=10)
    timestamp: datetime


class CurrentPriceCreateDTO(BaseModel):
    exchangeId: UUID
    pairId: UUID
    bid: condecimal(max_digits=24, decimal_places=10)
    ask: condecimal(max_digits=24, decimal_places=10)
    timestamp: Optional[datetime] = None


class ArbitrageOpportunityDTO(BaseModel):
    id: UUID
    pairId: UUID
    buyExchangeId: UUID
    sellExchangeId: UUID
    spreadPct: condecimal(max_digits=10, decimal_places=4)
    estimatedProfitUsd: condecimal(max_digits=18, decimal_places=4)
    foundAt: datetime


class ArbitrageOpportunityCreateDTO(BaseModel):
    pairId: UUID
    buyExchangeId: UUID
    sellExchangeId: UUID
    spreadPct: condecimal(max_digits=10, decimal_places=4)
    estimatedProfitUsd: condecimal(max_digits=18, decimal_places=4)
    foundAt: Optional[datetime] = None


class NotificationRuleDTO(BaseModel):
    id: UUID
    userId: UUID
    pairId: Optional[UUID] = None
    minSpreadPct: condecimal(max_digits=10, decimal_places=4)
    cooldownSec: conint(ge=0, le=86400)


class NotificationRuleCreateDTO(BaseModel):
    pairId: Optional[UUID] = None
    minSpreadPct: condecimal(max_digits=10, decimal_places=4)
    cooldownSec: conint(ge=0, le=86400) = 60


class NotificationRulePatchDTO(BaseModel):
    pairId: Optional[UUID] = None
    minSpreadPct: Optional[condecimal(max_digits=10, decimal_places=4)] = None
    cooldownSec: Optional[conint(ge=0, le=86400)] = None


class NotificationChannelDTO(BaseModel):
    id: UUID
    userId: UUID
    type: ChannelType
    address: constr(min_length=3, max_length=256)
    isEnabled: bool


class NotificationChannelCreateDTO(BaseModel):
    type: ChannelType
    address: constr(min_length=3, max_length=256)
    isEnabled: bool = True


class NotificationChannelPatchDTO(BaseModel):
    address: Optional[constr(min_length=3, max_length=256)] = None
    isEnabled: Optional[bool] = None


class AlertLogDTO(BaseModel):
    id: UUID
    userId: UUID
    opportunityId: UUID
    channelId: UUID
    status: SendStatus
    sentAt: datetime


class AlertLogCreateDTO(BaseModel):
    userId: UUID
    opportunityId: UUID
    channelId: UUID
    status: SendStatus
    sentAt: Optional[datetime] = None


# -----------------------------
# In-memory storage
# -----------------------------
db_users: Dict[UUID, UserDTO] = {}
db_exchanges: Dict[UUID, ExchangeDTO] = {}
db_pairs: Dict[UUID, TradingPairDTO] = {}
db_prices: Dict[UUID, CurrentPriceDTO] = {}
db_opps: Dict[UUID, ArbitrageOpportunityDTO] = {}
db_rules: Dict[UUID, NotificationRuleDTO] = {}
db_channels: Dict[UUID, NotificationChannelDTO] = {}
db_alerts: Dict[UUID, AlertLogDTO] = {}

# Seed demo users
demo_user_id = uuid4()
demo_admin_id = uuid4()
db_users[demo_user_id] = UserDTO(id=demo_user_id, email="user@example.com", telegramId="123456", createdAt=now_utc())
db_users[demo_admin_id] = UserDTO(id=demo_admin_id, email="admin@example.com", telegramId=None, createdAt=now_utc())

# Key -> userId mapping
KEY_USER_MAP: Dict[str, UUID] = {
    "demo-user": demo_user_id,
    "demo-admin": demo_admin_id,
    "service-engine": demo_admin_id,
    "service-notify": demo_admin_id,
}


def current_user_id(x_api_key: str) -> UUID:
    return KEY_USER_MAP[x_api_key]


# Seed demo exchanges/pairs
def seed():
    ex1 = ExchangeDTO(id=uuid4(), name="Binance", type=ExchangeType.CEX, network=None)
    ex2 = ExchangeDTO(id=uuid4(), name="Bybit", type=ExchangeType.CEX, network=None)
    ex3 = ExchangeDTO(id=uuid4(), name="Uniswap", type=ExchangeType.DEX, network="Ethereum")
    for ex in (ex1, ex2, ex3):
        db_exchanges[ex.id] = ex

    p1 = TradingPairDTO(id=uuid4(), base="ETH", quote="USDT")
    p2 = TradingPairDTO(id=uuid4(), base="BTC", quote="USDT")
    for p in (p1, p2):
        db_pairs[p.id] = p

seed()


def assert_exists(store: Dict[UUID, Any], entity_id: UUID, name: str) -> None:
    if entity_id not in store:
        raise HTTPException(status_code=404, detail=f"{name} not found")


# -----------------------------
# Public API
# -----------------------------

@app.get(f"{API_PREFIX}/health")
def health():
    return {"status": "ok", "time": now_utc().isoformat()}


# Users
@app.get(f"{API_PREFIX}/users/me", response_model=UserDTO)
def get_me(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    return db_users[uid]


@app.patch(f"{API_PREFIX}/users/me", response_model=UserDTO)
def patch_me(payload: UserPatchDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    user = db_users[uid]
    data = user.model_dump()
    if payload.email is not None:
        data["email"] = payload.email
    if payload.telegramId is not None:
        data["telegramId"] = payload.telegramId
    db_users[uid] = UserDTO(**data)
    return db_users[uid]


# Exchanges (admin CRUD; users can read)
@app.get(f"{API_PREFIX}/exchanges", response_model=List[ExchangeDTO])
def list_exchanges(
    type: Optional[ExchangeType] = Query(default=None),
    network: Optional[str] = Query(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    items = list(db_exchanges.values())
    if type:
        items = [e for e in items if e.type == type]
    if network:
        items = [e for e in items if (e.network or "").lower() == network.lower()]
    return items


@app.post(f"{API_PREFIX}/exchanges", response_model=ExchangeDTO, status_code=201)
def create_exchange(payload: ExchangeCreateDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.ADMIN])
    ex = ExchangeDTO(id=uuid4(), **payload.model_dump())
    db_exchanges[ex.id] = ex
    return ex


@app.put(f"{API_PREFIX}/exchanges/{{exchange_id}}", response_model=ExchangeDTO)
def update_exchange(exchange_id: UUID, payload: ExchangeCreateDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.ADMIN])
    assert_exists(db_exchanges, exchange_id, "Exchange")
    ex = ExchangeDTO(id=exchange_id, **payload.model_dump())
    db_exchanges[exchange_id] = ex
    return ex


@app.delete(f"{API_PREFIX}/exchanges/{{exchange_id}}", status_code=204)
def delete_exchange(exchange_id: UUID, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.ADMIN])
    assert_exists(db_exchanges, exchange_id, "Exchange")
    del db_exchanges[exchange_id]
    return None


# Trading pairs
@app.get(f"{API_PREFIX}/pairs", response_model=List[TradingPairDTO])
def list_pairs(
    base: Optional[str] = Query(default=None),
    quote: Optional[str] = Query(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    items = list(db_pairs.values())
    if base:
        items = [p for p in items if p.base.lower() == base.lower()]
    if quote:
        items = [p for p in items if p.quote.lower() == quote.lower()]
    return items


@app.post(f"{API_PREFIX}/pairs", response_model=TradingPairDTO, status_code=201)
def create_pair(payload: TradingPairCreateDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.ADMIN])
    p = TradingPairDTO(id=uuid4(), **payload.model_dump())
    db_pairs[p.id] = p
    return p


@app.delete(f"{API_PREFIX}/pairs/{{pair_id}}", status_code=204)
def delete_pair(pair_id: UUID, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.ADMIN])
    assert_exists(db_pairs, pair_id, "TradingPair")
    del db_pairs[pair_id]
    return None


# Prices (read-only public)
@app.get(f"{API_PREFIX}/prices/latest", response_model=List[CurrentPriceDTO])
def latest_prices(
    pairId: Optional[UUID] = Query(default=None),
    exchangeId: Optional[UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    items = list(db_prices.values())
    if pairId:
        items = [x for x in items if x.pairId == pairId]
    if exchangeId:
        items = [x for x in items if x.exchangeId == exchangeId]
    # latest per (exchange,pair)
    latest_map: Dict[tuple, CurrentPriceDTO] = {}
    for it in items:
        k = (it.exchangeId, it.pairId)
        if k not in latest_map or it.timestamp > latest_map[k].timestamp:
            latest_map[k] = it
    out = sorted(latest_map.values(), key=lambda r: r.timestamp, reverse=True)[:limit]
    return out


@app.get(f"{API_PREFIX}/prices/history", response_model=List[CurrentPriceDTO])
def price_history(
    pairId: UUID,
    exchangeId: UUID,
    fromTs: Optional[datetime] = Query(default=None),
    toTs: Optional[datetime] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    items = [x for x in db_prices.values() if x.pairId == pairId and x.exchangeId == exchangeId]
    if fromTs:
        items = [x for x in items if x.timestamp >= fromTs]
    if toTs:
        items = [x for x in items if x.timestamp <= toTs]
    items = sorted(items, key=lambda r: r.timestamp, reverse=True)[:limit]
    return items


# Opportunities (read-only public)
@app.get(f"{API_PREFIX}/opportunities", response_model=List[ArbitrageOpportunityDTO])
def list_opportunities(
    pairId: Optional[UUID] = Query(default=None),
    minSpreadPct: Optional[float] = Query(default=None),
    buyExchangeId: Optional[UUID] = Query(default=None),
    sellExchangeId: Optional[UUID] = Query(default=None),
    fromTs: Optional[datetime] = Query(default=None),
    toTs: Optional[datetime] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    items = list(db_opps.values())
    if pairId:
        items = [o for o in items if o.pairId == pairId]
    if minSpreadPct is not None:
        items = [o for o in items if float(o.spreadPct) >= float(minSpreadPct)]
    if buyExchangeId:
        items = [o for o in items if o.buyExchangeId == buyExchangeId]
    if sellExchangeId:
        items = [o for o in items if o.sellExchangeId == sellExchangeId]
    if fromTs:
        items = [o for o in items if o.foundAt >= fromTs]
    if toTs:
        items = [o for o in items if o.foundAt <= toTs]
    items = sorted(items, key=lambda r: r.foundAt, reverse=True)[:limit]
    return items


@app.get(f"{API_PREFIX}/opportunities/{{opportunity_id}}", response_model=ArbitrageOpportunityDTO)
def get_opportunity(opportunity_id: UUID, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    assert_exists(db_opps, opportunity_id, "ArbitrageOpportunity")
    return db_opps[opportunity_id]


@app.get(f"{API_PREFIX}/opportunities/export")
def export_opportunities(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    items = list_opportunities(x_api_key=x_api_key)
    if format == "json":
        return {"items": [i.model_dump() for i in items]}
    # csv
    header = "id,pairId,buyExchangeId,sellExchangeId,spreadPct,estimatedProfitUsd,foundAt"
    lines = [header]
    for i in items:
        lines.append(
            f"{i.id},{i.pairId},{i.buyExchangeId},{i.sellExchangeId},{i.spreadPct},{i.estimatedProfitUsd},{i.foundAt.isoformat()}"
        )
    return {"csv": "\n".join(lines)}


# Notification channels (user-scoped)
@app.get(f"{API_PREFIX}/notification-channels", response_model=List[NotificationChannelDTO])
def list_channels(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    return [c for c in db_channels.values() if c.userId == uid]


@app.post(f"{API_PREFIX}/notification-channels", response_model=NotificationChannelDTO, status_code=201)
def create_channel(payload: NotificationChannelCreateDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    ch = NotificationChannelDTO(id=uuid4(), userId=uid, **payload.model_dump())
    db_channels[ch.id] = ch
    return ch


@app.patch(f"{API_PREFIX}/notification-channels/{{channel_id}}", response_model=NotificationChannelDTO)
def patch_channel(channel_id: UUID, payload: NotificationChannelPatchDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    assert_exists(db_channels, channel_id, "NotificationChannel")
    ch = db_channels[channel_id]
    if ch.userId != uid:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = ch.model_dump()
    if payload.address is not None:
        data["address"] = payload.address
    if payload.isEnabled is not None:
        data["isEnabled"] = payload.isEnabled
    db_channels[channel_id] = NotificationChannelDTO(**data)
    return db_channels[channel_id]


@app.delete(f"{API_PREFIX}/notification-channels/{{channel_id}}", status_code=204)
def delete_channel(channel_id: UUID, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    assert_exists(db_channels, channel_id, "NotificationChannel")
    if db_channels[channel_id].userId != uid:
        raise HTTPException(status_code=403, detail="Forbidden")
    del db_channels[channel_id]
    return None


# Notification rules (user-scoped)
@app.get(f"{API_PREFIX}/notification-rules", response_model=List[NotificationRuleDTO])
def list_rules(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    return [r for r in db_rules.values() if r.userId == uid]


@app.post(f"{API_PREFIX}/notification-rules", response_model=NotificationRuleDTO, status_code=201)
def create_rule(payload: NotificationRuleCreateDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    if payload.pairId is not None:
        assert_exists(db_pairs, payload.pairId, "TradingPair")
    rule = NotificationRuleDTO(id=uuid4(), userId=uid, **payload.model_dump())
    db_rules[rule.id] = rule
    return rule


@app.patch(f"{API_PREFIX}/notification-rules/{{rule_id}}", response_model=NotificationRuleDTO)
def patch_rule(rule_id: UUID, payload: NotificationRulePatchDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    assert_exists(db_rules, rule_id, "NotificationRule")
    rule = db_rules[rule_id]
    if rule.userId != uid:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = rule.model_dump()
    if payload.pairId is not None:
        assert_exists(db_pairs, payload.pairId, "TradingPair")
        data["pairId"] = payload.pairId
    if payload.minSpreadPct is not None:
        data["minSpreadPct"] = payload.minSpreadPct
    if payload.cooldownSec is not None:
        data["cooldownSec"] = payload.cooldownSec
    db_rules[rule_id] = NotificationRuleDTO(**data)
    return db_rules[rule_id]


@app.delete(f"{API_PREFIX}/notification-rules/{{rule_id}}", status_code=204)
def delete_rule(rule_id: UUID, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    assert_exists(db_rules, rule_id, "NotificationRule")
    if db_rules[rule_id].userId != uid:
        raise HTTPException(status_code=403, detail="Forbidden")
    del db_rules[rule_id]
    return None


# Alert logs (read-only public; user-scoped)
@app.get(f"{API_PREFIX}/alert-logs", response_model=List[AlertLogDTO])
def list_alert_logs(
    status_: Optional[SendStatus] = Query(default=None, alias="status"),
    fromTs: Optional[datetime] = Query(default=None),
    toTs: Optional[datetime] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    items = [a for a in db_alerts.values() if a.userId == uid]
    if status_:
        items = [a for a in items if a.status == status_]
    if fromTs:
        items = [a for a in items if a.sentAt >= fromTs]
    if toTs:
        items = [a for a in items if a.sentAt <= toTs]
    items = sorted(items, key=lambda r: r.sentAt, reverse=True)[:limit]
    return items


@app.get(f"{API_PREFIX}/alert-logs/{{alert_id}}", response_model=AlertLogDTO)
def get_alert_log(alert_id: UUID, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.USER, Role.ADMIN])
    uid = current_user_id(x_api_key)
    assert_exists(db_alerts, alert_id, "AlertLog")
    if db_alerts[alert_id].userId != uid:
        raise HTTPException(status_code=403, detail="Forbidden")
    return db_alerts[alert_id]


# -----------------------------
# Internal API (service-to-service)
# -----------------------------

@app.get(f"{INTERNAL_PREFIX}/health")
def internal_health(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.SERVICE, Role.ADMIN])
    return {"status": "ok", "scope": "internal", "time": now_utc().isoformat()}


@app.post(f"{INTERNAL_PREFIX}/prices", response_model=CurrentPriceDTO, status_code=201)
def ingest_price(payload: CurrentPriceCreateDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.SERVICE, Role.ADMIN])
    assert_exists(db_exchanges, payload.exchangeId, "Exchange")
    assert_exists(db_pairs, payload.pairId, "TradingPair")
    ts = payload.timestamp or now_utc()
    obj = CurrentPriceDTO(id=uuid4(), exchangeId=payload.exchangeId, pairId=payload.pairId, bid=payload.bid, ask=payload.ask, timestamp=ts)
    db_prices[obj.id] = obj
    return obj


@app.post(f"{INTERNAL_PREFIX}/opportunities", response_model=ArbitrageOpportunityDTO, status_code=201)
def ingest_opportunity(payload: ArbitrageOpportunityCreateDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.SERVICE, Role.ADMIN])
    assert_exists(db_pairs, payload.pairId, "TradingPair")
    assert_exists(db_exchanges, payload.buyExchangeId, "Exchange")
    assert_exists(db_exchanges, payload.sellExchangeId, "Exchange")
    ts = payload.foundAt or now_utc()
    obj = ArbitrageOpportunityDTO(id=uuid4(), pairId=payload.pairId, buyExchangeId=payload.buyExchangeId, sellExchangeId=payload.sellExchangeId,
                                 spreadPct=payload.spreadPct, estimatedProfitUsd=payload.estimatedProfitUsd, foundAt=ts)
    db_opps[obj.id] = obj
    return obj


@app.post(f"{INTERNAL_PREFIX}/alert-logs", response_model=AlertLogDTO, status_code=201)
def ingest_alert_log(payload: AlertLogCreateDTO, x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    role = get_role(x_api_key)
    require_roles(role, [Role.SERVICE, Role.ADMIN])
    assert_exists(db_users, payload.userId, "User")
    assert_exists(db_opps, payload.opportunityId, "ArbitrageOpportunity")
    assert_exists(db_channels, payload.channelId, "NotificationChannel")
    ts = payload.sentAt or now_utc()
    obj = AlertLogDTO(id=uuid4(), userId=payload.userId, opportunityId=payload.opportunityId, channelId=payload.channelId, status=payload.status, sentAt=ts)
    db_alerts[obj.id] = obj
    return obj
