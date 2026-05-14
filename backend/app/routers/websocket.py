import asyncio
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.cache import cache_get
from app.core.logging import get_logger
from app.services.realtime_feed import feed


logger = get_logger(__name__)
router = APIRouter(tags=["realtime"])


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, ws: WebSocket, ticker: str) -> None:
        await ws.accept()
        self.active.setdefault(ticker, []).append(ws)

    def disconnect(self, ws: WebSocket, ticker: str) -> None:
        sockets = self.active.get(ticker, [])
        if ws in sockets:
            sockets.remove(ws)
        if not sockets:
            self.active.pop(ticker, None)

    async def broadcast(self, ticker: str, data: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.active.get(ticker, []):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, ticker)


manager = ConnectionManager()


def _ticker(value: str) -> str:
    ticker = value.strip().upper()
    if not ticker or len(ticker) > 12 or not ticker.replace(".", "").replace("-", "").isalnum():
        raise ValueError("Invalid ticker")
    return ticker


async def _enrich_update(ticker: str, update: dict) -> dict:
    cached_signals = await cache_get(f"signals:{ticker}")
    return {
        "type": "quote",
        "ticker": ticker,
        "price": update["price"],
        "change": update["change"],
        "change_pct": update["change_pct"],
        "volume": update["volume"],
        "bid": update.get("bid"),
        "ask": update.get("ask"),
        "timestamp": update["timestamp"],
        "provider": update.get("provider", update.get("source", "unknown")),
        "source": update.get("source", "unknown"),
        "delayed": bool(update.get("delayed")),
        "stale": bool(update.get("stale")),
        "raw_type": update.get("raw_type"),
        "signal": cached_signals.get("action") if isinstance(cached_signals, dict) else None,
        "composite_score": cached_signals.get("composite_score") if isinstance(cached_signals, dict) else None,
    }


@router.websocket("/ws/quote/{ticker}")
async def ws_quote(websocket: WebSocket, ticker: str):
    ticker = _ticker(ticker)
    await manager.connect(websocket, ticker)
    queue = await feed.subscribe(ticker)
    try:
        while True:
            try:
                update = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(await _enrich_update(ticker, update))
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat", "timestamp": datetime.now(UTC).isoformat()})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket quote stream failed for %s: %s", ticker, exc)
    finally:
        await feed.unsubscribe(ticker, queue)
        manager.disconnect(websocket, ticker)


@router.get("/sse/quote/{ticker}")
async def sse_quote(ticker: str, request: Request):
    ticker = _ticker(ticker)

    async def event_stream():
        queue = await feed.subscribe(ticker)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(await _enrich_update(ticker, update))}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now(UTC).isoformat()})}\n\n"
        finally:
            await feed.unsubscribe(ticker, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
