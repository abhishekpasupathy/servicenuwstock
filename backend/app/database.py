from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


settings = get_settings()
engine = create_async_engine(settings.postgres_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

_holdings: dict[int, dict[str, Any]] = {}
_alerts: dict[int, dict[str, Any]] = {}
_ids = defaultdict(int)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


def next_id(kind: str) -> int:
    _ids[kind] += 1
    return _ids[kind]


def list_holdings() -> list[dict[str, Any]]:
    return list(_holdings.values())


def add_holding(payload: dict[str, Any]) -> dict[str, Any]:
    item = {
        "id": next_id("holding"),
        "ticker": payload.get("ticker", "NOW").upper(),
        "shares": float(payload.get("shares", 0)),
        "avg_buy_price": float(payload.get("avg_buy_price", payload.get("avgBuyPrice", 85))),
        "date_purchased": payload.get("date_purchased") or payload.get("datePurchased") or str(date.today()),
    }
    _holdings[item["id"]] = item
    return item


def update_holding(holding_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    if holding_id not in _holdings:
        return None
    _holdings[holding_id].update(payload)
    return _holdings[holding_id]


def delete_holding(holding_id: int) -> bool:
    return _holdings.pop(holding_id, None) is not None


def list_alerts() -> list[dict[str, Any]]:
    return list(_alerts.values())


def add_alert(payload: dict[str, Any]) -> dict[str, Any]:
    item = {"id": next_id("alert"), "ticker": payload.get("ticker", "NOW").upper(), **payload}
    _alerts[item["id"]] = item
    return item


def delete_alert(alert_id: int) -> bool:
    return _alerts.pop(alert_id, None) is not None
