from fastapi import APIRouter, HTTPException

from app.database import add_holding, delete_holding, list_holdings, update_holding
from app.services.data_fetcher import get_quote

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio/holdings")
async def holdings():
    rows = []
    for item in list_holdings():
        quote = await get_quote(item["ticker"])
        value = item["shares"] * quote["price"]
        invested = item["shares"] * item["avg_buy_price"]
        rows.append(
            {
                **item,
                "current_price": quote["price"],
                "total_value": round(value, 2),
                "pnl": round(value - invested, 2),
                "pnl_pct": round((value / invested - 1) * 100, 2) if invested else 0,
            }
        )
    return rows


@router.post("/portfolio/holdings")
async def create_holding(payload: dict):
    return add_holding(payload)


@router.put("/portfolio/holdings/{holding_id}")
async def put_holding(holding_id: int, payload: dict):
    item = update_holding(holding_id, payload)
    if not item:
        raise HTTPException(404, "Holding not found")
    return item


@router.delete("/portfolio/holdings/{holding_id}")
async def remove_holding(holding_id: int):
    if not delete_holding(holding_id):
        raise HTTPException(404, "Holding not found")
    return {"deleted": True}
