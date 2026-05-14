import asyncio
import json
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

import websockets
from websockets.client import WebSocketClientProtocol

from app.cache import cache_set
from app.config import get_settings
from app.core.logging import get_logger
from app.services.data_fetcher import get_quote


settings = get_settings()
logger = get_logger(__name__)


class AlpacaRealtimeFeed:
    WS_URL = "wss://stream.data.alpaca.markets/v2/iex"
    FINNHUB_WS_URL = "wss://ws.finnhub.io"

    def __init__(self, api_key: str, api_secret: str, finnhub_api_key: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.finnhub_api_key = finnhub_api_key
        self.subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self.last_quotes: dict[str, dict[str, Any]] = {}
        self.ws: WebSocketClientProtocol | None = None
        self.running = False
        self.provider = "alpaca" if api_key and api_secret else "finnhub" if finnhub_api_key else "yfinance"
        self._task: asyncio.Task[None] | None = None
        self._fallback_tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    @property
    def has_stream_provider(self) -> bool:
        return self.provider in {"alpaca", "finnhub"}

    async def connect(self) -> None:
        if not self.has_stream_provider:
            logger.info("Realtime feed using yfinance fallback polling; no Alpaca/Finnhub key configured")
            return
        if self._task and not self._task.done():
            return
        self.running = True
        self._task = asyncio.create_task(self._message_loop())

    async def stop(self) -> None:
        self.running = False
        if self.ws is not None:
            await self.ws.close()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        for task in list(self._fallback_tasks.values()):
            task.cancel()
        self._fallback_tasks.clear()

    async def subscribe(self, ticker: str) -> asyncio.Queue[dict[str, Any]]:
        ticker = ticker.upper().strip()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=10)
        async with self._lock:
            self.subscribers.setdefault(ticker, set()).add(queue)
            if self.has_stream_provider:
                await self.connect()
                await self._send_subscription("subscribe", [ticker])
            elif ticker not in self._fallback_tasks:
                self._fallback_tasks[ticker] = asyncio.create_task(self._fallback_loop(ticker))

        if ticker in self.last_quotes:
            await self._safe_put(queue, self.last_quotes[ticker])
        else:
            initial = await self._fallback_poll(ticker)
            self.last_quotes[ticker] = initial
            await self._safe_put(queue, initial)
        return queue

    async def unsubscribe(self, ticker: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        ticker = ticker.upper().strip()
        async with self._lock:
            queues = self.subscribers.get(ticker)
            if queues:
                queues.discard(queue)
                if not queues:
                    self.subscribers.pop(ticker, None)
                    await self._send_subscription("unsubscribe", [ticker])
                    task = self._fallback_tasks.pop(ticker, None)
                    if task:
                        task.cancel()

    async def _send_subscription(self, action: str, tickers: list[str]) -> None:
        if not tickers or self.ws is None or self.ws.closed:
            return
        try:
            if self.provider == "alpaca":
                await self.ws.send(json.dumps({"action": action, "quotes": tickers, "trades": tickers, "bars": tickers}))
            elif self.provider == "finnhub":
                for ticker in tickers:
                    await self.ws.send(json.dumps({"type": action, "symbol": ticker}))
        except Exception as exc:
            logger.warning("Realtime subscription update failed: %s", exc)

    async def _message_loop(self) -> None:
        backoff = 1
        while self.running and self.has_stream_provider:
            try:
                await self._connect_once()
                backoff = 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("%s realtime stream disconnected: %s", self.provider, exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _connect_once(self) -> None:
        url = self.WS_URL if self.provider == "alpaca" else f"{self.FINNHUB_WS_URL}?token={self.finnhub_api_key}"
        async with websockets.connect(url, ping_interval=30, ping_timeout=20) as ws:
            self.ws = ws
            if self.provider == "alpaca":
                await ws.send(json.dumps({"action": "auth", "key": self.api_key, "secret": self.api_secret}))
            async with self._lock:
                tickers = list(self.subscribers)
            if tickers:
                await self._send_subscription("subscribe", tickers)

            async for raw_message in ws:
                await self._handle_raw_message(raw_message)

    async def _handle_raw_message(self, raw_message: str | bytes) -> None:
        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError:
            return
        messages = payload if isinstance(payload, list) else [payload]
        for message in messages:
            if not isinstance(message, dict):
                continue
            update = await self._normalize_stream_message(message)
            if update is not None:
                await self._publish(update["ticker"], update)

    async def _normalize_stream_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        if self.provider == "alpaca":
            msg_type = message.get("T")
            ticker = str(message.get("S") or "").upper()
            if msg_type not in {"q", "t", "b"} or not ticker:
                return None
            previous = self.last_quotes.get(ticker, {})
            price = _num(message.get("ap") or message.get("bp") or message.get("p") or message.get("c") or previous.get("price"))
            if price <= 0:
                return None
            volume = _num(message.get("s") or message.get("v") or previous.get("volume"))
            return self._shape_update(
                ticker=ticker,
                price=price,
                volume=volume,
                bid=_num_or_none(message.get("bp")),
                ask=_num_or_none(message.get("ap")),
                timestamp=str(message.get("t") or datetime.now(UTC).isoformat()),
                provider="alpaca",
                delayed=False,
                raw_type=str(msg_type),
            )

        if self.provider == "finnhub" and message.get("type") == "trade":
            rows = message.get("data")
            if not isinstance(rows, list):
                return None
            for row in rows:
                if not isinstance(row, dict):
                    continue
                ticker = str(row.get("s") or "").upper()
                price = _num(row.get("p"))
                if ticker and price > 0:
                    return self._shape_update(
                        ticker=ticker,
                        price=price,
                        volume=_num(row.get("v")),
                        bid=None,
                        ask=None,
                        timestamp=_millis_to_iso(row.get("t")),
                        provider="finnhub",
                        delayed=False,
                        raw_type="trade",
                    )
        return None

    def _shape_update(
        self,
        ticker: str,
        price: float,
        volume: float,
        bid: float | None,
        ask: float | None,
        timestamp: str,
        provider: str,
        delayed: bool,
        raw_type: str,
    ) -> dict[str, Any]:
        previous = self.last_quotes.get(ticker, {})
        prev_close = _num(previous.get("prev_close") or previous.get("previous_close") or price)
        if previous.get("price"):
            prev_close = _num(previous.get("prev_close") or previous.get("previous_close") or previous.get("price"))
        change = round(price - prev_close, 4)
        change_pct = round((change / prev_close) * 100, 4) if prev_close else 0.0
        return {
            "type": "quote",
            "ticker": ticker,
            "price": round(price, 4),
            "change": change,
            "change_pct": change_pct,
            "volume": int(volume or previous.get("volume") or 0),
            "bid": bid,
            "ask": ask,
            "timestamp": timestamp,
            "provider": provider,
            "source": provider,
            "delayed": delayed,
            "stale": provider in {"cache", "synthetic"},
            "raw_type": raw_type,
        }

    async def _publish(self, ticker: str, update: dict[str, Any]) -> None:
        self.last_quotes[ticker] = update
        await cache_set(f"realtime:{ticker}", update, 60)
        queues = list(self.subscribers.get(ticker, set()))
        for queue in queues:
            await self._safe_put(queue, update)

    async def _safe_put(self, queue: asyncio.Queue[dict[str, Any]], update: dict[str, Any]) -> None:
        if queue.full():
            with suppress(asyncio.QueueEmpty):
                queue.get_nowait()
        await queue.put(update)

    async def _fallback_loop(self, ticker: str) -> None:
        while ticker in self.subscribers:
            update = await self._fallback_poll(ticker)
            await self._publish(ticker, update)
            await asyncio.sleep(15)

    async def _fallback_poll(self, ticker: str) -> dict[str, Any]:
        try:
            quote = await get_quote(ticker)
            provider = "cache" if quote.get("source") == "cache" else "yfinance"
            return {
                "type": "quote",
                "ticker": ticker,
                "price": _num(quote.get("price")),
                "change": _num(quote.get("change")),
                "change_pct": _num(quote.get("change_pct")),
                "volume": int(_num(quote.get("volume"))),
                "prev_close": _num(quote.get("prev_close")),
                "bid": None,
                "ask": None,
                "timestamp": str(quote.get("timestamp") or datetime.now(UTC).isoformat()),
                "provider": provider,
                "source": provider,
                "delayed": provider == "yfinance",
                "stale": bool(quote.get("stale") or provider == "cache"),
                "raw_type": "poll",
            }
        except Exception as exc:
            logger.warning("Realtime fallback poll failed for %s: %s", ticker, exc)
            previous = self.last_quotes.get(ticker, {})
            price = _num(previous.get("price"), 85.0)
            return {
                "type": "quote",
                "ticker": ticker,
                "price": price,
                "change": _num(previous.get("change")),
                "change_pct": _num(previous.get("change_pct")),
                "volume": int(_num(previous.get("volume"))),
                "bid": None,
                "ask": None,
                "timestamp": datetime.now(UTC).isoformat(),
                "provider": "synthetic",
                "source": "synthetic",
                "delayed": True,
                "stale": True,
                "raw_type": "fallback",
            }


def _num(value: Any, fallback: float = 0.0) -> float:
    try:
        result = float(value)
        return result if result == result else fallback
    except Exception:
        return fallback


def _num_or_none(value: Any) -> float | None:
    result = _num(value, 0.0)
    return result if result > 0 else None


def _millis_to_iso(value: Any) -> str:
    millis = _num(value)
    if millis <= 0:
        return datetime.now(UTC).isoformat()
    return datetime.fromtimestamp(millis / 1000, UTC).isoformat()


feed = AlpacaRealtimeFeed(
    api_key=settings.alpaca_api_key or "",
    api_secret=settings.alpaca_api_secret or "",
    finnhub_api_key=settings.finnhub_api_key or "",
)
