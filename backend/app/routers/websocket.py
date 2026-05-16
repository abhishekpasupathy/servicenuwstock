import asyncio
import json
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.services.data_fetcher import get_quote
from app.services.realtime_feed import feed

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/ws/quote/{ticker}")
async def quote_ws(websocket: WebSocket, ticker: str):
    await websocket.accept()
    ticker = ticker.upper().strip()
    queue = await feed.subscribe(ticker)

    try:
        while True:
            try:
                update = await asyncio.wait_for(queue.get(), timeout=25)
                await websocket.send_text(json.dumps(update))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "heartbeat", "ticker": ticker, "timestamp": datetime.now(UTC).isoformat()}))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error for %s: %s", ticker, exc)
    finally:
        await feed.unsubscribe(ticker, queue)
