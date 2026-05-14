from datetime import UTC, date, datetime, timedelta
from time import sleep
from typing import Any, Callable, TypeVar

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from app.core.config import get_settings
from app.schemas.market import (
    HistoryPoint,
    HistoryResponse,
    ProfileResponse,
    QuoteResponse,
    SnapshotMetadata,
    SnapshotResponse,
)
from app.utils.cache import TTLCache
from app.utils.persistent_cache import PersistentCache

settings = get_settings()
cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)
persistent_cache = PersistentCache(settings.sqlite_path)
SUCCESS_CACHE_TTL_SECONDS = max(
    settings.cache_ttl_seconds,
    settings.market_cache_ttl_seconds,
)
FALLBACK_CACHE_TTL_SECONDS = settings.market_fallback_cache_ttl_seconds
RETRY_DELAYS_SECONDS = (0.6, 1.4, 2.8)
T = TypeVar("T")

FALLBACK_ANCHORS: dict[str, dict[str, Any]] = {
    "NOW": {
        "name": "ServiceNow Inc.",
        "price": 87.0,
        "market_cap": 90_000_000_000,
        "volume": 20_000_000,
        "currency": "USD",
        "exchange": "Sample",
        "website": "https://www.servicenow.com",
        "sector": "Technology",
        "industry": "Software - Application",
        "country": "United States",
    },
}


class MarketDataError(Exception):
    pass


class UpstreamProviderError(Exception):
    pass


class UpstreamRateLimitError(UpstreamProviderError):
    pass


def normalize_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not normalized or len(normalized) > 12 or not normalized.replace(".", "").replace("-", "").isalnum():
        raise MarketDataError("Ticker must be 1-12 letters, numbers, dots, or hyphens.")
    return normalized


def _clean_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _clean_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def _with_retry(operation: Callable[[], T]) -> T:
    last_error: Exception | None = None

    for attempt, delay in enumerate((*RETRY_DELAYS_SECONDS, 0.0), start=1):
        try:
            return operation()
        except YFRateLimitError as exc:
            last_error = exc
            if attempt <= len(RETRY_DELAYS_SECONDS):
                sleep(delay)
                continue
            raise UpstreamRateLimitError(
                "Yahoo Finance is temporarily rate limiting market data requests."
            ) from exc
        except Exception as exc:
            message = str(exc)
            last_error = exc
            if "Too Many Requests" in message or "429" in message:
                if attempt <= len(RETRY_DELAYS_SECONDS):
                    sleep(delay)
                    continue
                raise UpstreamRateLimitError(
                    "Yahoo Finance is temporarily rate limiting market data requests."
                ) from exc
            if attempt <= len(RETRY_DELAYS_SECONDS):
                sleep(delay)
                continue
            raise UpstreamProviderError(
                "Yahoo Finance is temporarily unavailable. Showing fallback data when possible."
            ) from exc

    raise UpstreamProviderError("Market data provider request failed.") from last_error


def _ticker_info(ticker: str) -> dict[str, Any]:
    info = _with_retry(lambda: yf.Ticker(ticker).info)
    if not info or info.get("quoteType") is None:
        raise MarketDataError(f"No market data found for ticker '{ticker}'.")
    return info


def _get_cached_response(cache_key: str, model_type: type[T]) -> T | None:
    cached = cache.get(cache_key)
    if isinstance(cached, model_type):
        if _is_unusable_cached_fallback(cached):
            return None
        return cached

    payload = persistent_cache.get(cache_key)
    if payload is None:
        return None

    response = model_type.model_validate_json(payload)  # type: ignore[attr-defined]
    if _is_unusable_cached_fallback(response):
        return None
    cache.set(cache_key, response)
    return response


def _anchor_for(ticker: str) -> dict[str, Any]:
    if ticker in FALLBACK_ANCHORS:
        return FALLBACK_ANCHORS[ticker]

    seed = sum(ord(char) for char in ticker)
    return {
        "name": f"{ticker} sample quote",
        "price": 75.0 + (seed % 65),
        "market_cap": None,
        "volume": 750_000 + (seed % 900) * 1_000,
        "currency": "USD",
        "exchange": "Sample",
        "website": None,
        "sector": None,
        "industry": None,
        "country": None,
    }


def _is_unusable_cached_fallback(response: object) -> bool:
    if not isinstance(response, QuoteResponse):
        return False
    if not response.is_degraded:
        return False
    anchor = FALLBACK_ANCHORS.get(response.ticker)
    if anchor is None or response.price is None:
        return False
    anchor_price = float(anchor["price"])
    return response.price < anchor_price * 0.55 or response.price > anchor_price * 1.45


def _set_cached_response(cache_key: str, response: object, ttl_seconds: int) -> None:
    cache.set(cache_key, response, ttl_seconds=ttl_seconds)
    if hasattr(response, "model_dump_json"):
        persistent_cache.set(
            cache_key,
            response.model_dump_json(),  # type: ignore[attr-defined]
            ttl_seconds=ttl_seconds,
        )


def _build_quote_from_info(ticker: str, info: dict[str, Any]) -> QuoteResponse:
    return QuoteResponse(
        ticker=ticker,
        name=info.get("longName") or info.get("shortName"),
        currency=info.get("currency"),
        exchange=info.get("exchange"),
        price=_clean_float(
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        ),
        previous_close=_clean_float(info.get("previousClose")),
        open=_clean_float(info.get("open")),
        day_high=_clean_float(info.get("dayHigh")),
        day_low=_clean_float(info.get("dayLow")),
        volume=_clean_int(info.get("volume")),
        market_cap=_clean_int(info.get("marketCap")),
        fifty_two_week_high=_clean_float(info.get("fiftyTwoWeekHigh")),
        fifty_two_week_low=_clean_float(info.get("fiftyTwoWeekLow")),
        fetched_at=datetime.now(UTC),
    )


def _build_profile_from_info(ticker: str, info: dict[str, Any]) -> ProfileResponse:
    return ProfileResponse(
        ticker=ticker,
        name=info.get("longName") or info.get("shortName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        country=info.get("country"),
        website=info.get("website"),
        employees=_clean_int(info.get("fullTimeEmployees")),
        business_summary=info.get("longBusinessSummary"),
        fetched_at=datetime.now(UTC),
    )


def _sample_profile(ticker: str, message: str) -> ProfileResponse:
    anchor = _anchor_for(ticker)
    return ProfileResponse(
        ticker=ticker,
        name=anchor["name"],
        sector=anchor["sector"],
        industry=anchor["industry"],
        country=anchor["country"],
        website=anchor["website"],
        employees=None,
        business_summary=(
            "Sample company profile shown because the upstream market data provider "
            "is temporarily unavailable."
        ),
        source="sample",
        is_degraded=True,
        provider_message=message,
        fetched_at=datetime.now(UTC),
    )


def _sample_quote(ticker: str, message: str) -> QuoteResponse:
    anchor = _anchor_for(ticker)
    base_price = float(anchor["price"])
    previous_close = round(base_price * 0.997, 2)
    return QuoteResponse(
        ticker=ticker,
        name=anchor["name"],
        currency=anchor["currency"],
        exchange=anchor["exchange"],
        price=round(base_price, 2),
        previous_close=previous_close,
        open=round(previous_close * 1.001, 2),
        day_high=round(base_price * 1.012, 2),
        day_low=round(base_price * 0.988, 2),
        volume=int(anchor["volume"]),
        market_cap=anchor["market_cap"],
        fifty_two_week_high=round(base_price * 1.14, 2),
        fifty_two_week_low=round(base_price * 0.86, 2),
        source="sample",
        is_degraded=True,
        provider_message=message,
        fetched_at=datetime.now(UTC),
    )


def _period_days(period: str) -> int:
    return {
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "max": 365 * 5,
    }.get(period, 365)


def _sample_history(ticker: str, period: str, interval: str, message: str) -> HistoryResponse:
    days = _period_days(period)
    step = 7 if period == "max" else 1
    start = date.today() - timedelta(days=days)
    anchor = _anchor_for(ticker)
    base_price = float(anchor["price"])
    base_volume = int(anchor["volume"])
    points: list[HistoryPoint] = []

    for offset in range(0, days + 1, step):
        current_date = start + timedelta(days=offset)
        cycle = ((offset % 21) - 10) / 10
        slow_wave = ((offset % 89) - 44) / 44
        close = round(base_price * (1 + cycle * 0.018 + slow_wave * 0.045), 2)
        open_price = round(close * (1 + (((offset % 7) - 3) / 3_000)), 2)
        intraday_range = 0.008 + abs(cycle) * 0.004
        points.append(
            HistoryPoint(
                date=current_date,
                open=open_price,
                high=round(max(open_price, close) * (1 + intraday_range), 2),
                low=round(min(open_price, close) * (1 - intraday_range), 2),
                close=close,
                adj_close=close,
                volume=round(base_volume * (0.78 + ((offset + len(ticker)) % 20) / 50)),
            )
        )

    return HistoryResponse(
        ticker=ticker,
        period=period,
        interval=interval,
        points=points,
        source="sample",
        is_degraded=True,
        provider_message=message,
        fetched_at=datetime.now(UTC),
    )


def _quote_from_history(
    ticker: str,
    history: HistoryResponse,
    message: str,
) -> QuoteResponse | None:
    points = history.points
    if len(points) < 2:
        return None

    anchor = _anchor_for(ticker)
    last = points[-1]
    previous = points[-2]
    recent = points[-252:] if len(points) >= 252 else points
    volume_window = points[-20:] if len(points) >= 20 else points
    average_volume = int(
        sum(point.volume for point in volume_window) / max(len(volume_window), 1)
    )

    return QuoteResponse(
        ticker=ticker,
        name=anchor["name"],
        currency=anchor["currency"],
        exchange=anchor["exchange"],
        price=round(last.close, 2),
        previous_close=round(previous.close, 2),
        open=round(last.open, 2),
        day_high=round(max(last.high, last.open, last.close), 2),
        day_low=round(min(last.low, last.open, last.close), 2),
        volume=average_volume,
        market_cap=anchor["market_cap"],
        fifty_two_week_high=round(max(point.high for point in recent), 2),
        fifty_two_week_low=round(min(point.low for point in recent), 2),
        source=history.source,
        is_degraded=True,
        provider_message=message,
        fetched_at=datetime.now(UTC),
    )


def get_quote(ticker: str) -> QuoteResponse:
    ticker = normalize_ticker(ticker)
    cache_key = f"quote:{ticker}"
    cached = _get_cached_response(cache_key, QuoteResponse)
    if cached is not None:
        return cached

    try:
        info = _ticker_info(ticker)
    except UpstreamProviderError as exc:
        message = str(exc)
        history = get_history(ticker, "1y", "1d")
        response = _quote_from_history(ticker, history, message) or _sample_quote(
            ticker,
            message,
        )
        _set_cached_response(cache_key, response, FALLBACK_CACHE_TTL_SECONDS)
        return response

    response = _build_quote_from_info(ticker, info)
    _set_cached_response(cache_key, response, SUCCESS_CACHE_TTL_SECONDS)
    return response


def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> HistoryResponse:
    ticker = normalize_ticker(ticker)
    cache_key = f"history:{ticker}:{period}:{interval}"
    cached = _get_cached_response(cache_key, HistoryResponse)
    if cached is not None:
        return cached

    try:
        frame = _with_retry(
            lambda: yf.Ticker(ticker).history(
                period=period,
                interval=interval,
                auto_adjust=False,
            )
        )
    except UpstreamProviderError as exc:
        response = _sample_history(ticker, period, interval, str(exc))
        _set_cached_response(cache_key, response, FALLBACK_CACHE_TTL_SECONDS)
        return response

    if frame.empty:
        response = _sample_history(
            ticker,
            period,
            interval,
            f"No historical data found for ticker '{ticker}'. Showing fallback data.",
        )
        _set_cached_response(cache_key, response, FALLBACK_CACHE_TTL_SECONDS)
        return response

    points: list[HistoryPoint] = []
    for index, row in frame.reset_index().iterrows():
        timestamp = row.get("Date") or row.get("Datetime")
        if timestamp is None:
            continue
        points.append(
            HistoryPoint(
                date=timestamp.date(),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                adj_close=_clean_float(row.get("Adj Close")),
                volume=int(row["Volume"]),
            )
        )

    response = HistoryResponse(
        ticker=ticker,
        period=period,
        interval=interval,
        points=points,
        fetched_at=datetime.now(UTC),
    )
    _set_cached_response(cache_key, response, SUCCESS_CACHE_TTL_SECONDS)
    return response


def get_profile(ticker: str) -> ProfileResponse:
    ticker = normalize_ticker(ticker)
    cache_key = f"profile:{ticker}"
    cached = _get_cached_response(cache_key, ProfileResponse)
    if cached is not None:
        return cached

    try:
        info = _ticker_info(ticker)
    except UpstreamProviderError as exc:
        response = _sample_profile(ticker, str(exc))
        _set_cached_response(cache_key, response, FALLBACK_CACHE_TTL_SECONDS)
        return response

    response = _build_profile_from_info(ticker, info)
    _set_cached_response(cache_key, response, SUCCESS_CACHE_TTL_SECONDS)
    return response


def get_snapshot(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> SnapshotResponse:
    ticker = normalize_ticker(ticker)
    quote_key = f"quote:{ticker}"
    profile_key = f"profile:{ticker}"

    quote = _get_cached_response(quote_key, QuoteResponse)
    profile = _get_cached_response(profile_key, ProfileResponse)

    if quote is None or profile is None:
        try:
            info = _ticker_info(ticker)
            if quote is None:
                quote = _build_quote_from_info(ticker, info)
                _set_cached_response(quote_key, quote, SUCCESS_CACHE_TTL_SECONDS)
            if profile is None:
                profile = _build_profile_from_info(ticker, info)
                _set_cached_response(profile_key, profile, SUCCESS_CACHE_TTL_SECONDS)
        except UpstreamProviderError as exc:
            message = str(exc)
            if quote is None:
                quote = _sample_quote(ticker, message)
                _set_cached_response(quote_key, quote, FALLBACK_CACHE_TTL_SECONDS)
            if profile is None:
                profile = _sample_profile(ticker, message)
                _set_cached_response(profile_key, profile, FALLBACK_CACHE_TTL_SECONDS)

    history = get_history(ticker, period, interval)
    if quote.is_degraded:
        history_quote = _quote_from_history(
            ticker,
            history,
            quote.provider_message or history.provider_message or "Using fallback market data.",
        )
        if history_quote is not None:
            quote = history_quote
            _set_cached_response(quote_key, quote, FALLBACK_CACHE_TTL_SECONDS)

    is_degraded = quote.is_degraded or profile.is_degraded or history.is_degraded
    provider_message = (
        quote.provider_message or profile.provider_message or history.provider_message
    )
    sources = sorted({quote.source, profile.source, history.source})

    return SnapshotResponse(
        quote=quote,
        profile=profile,
        history=history,
        metadata=SnapshotMetadata(
            ticker=ticker,
            period=period,
            interval=interval,
            source=",".join(sources),
            is_degraded=is_degraded,
            provider_message=provider_message,
            fetched_at=datetime.now(UTC),
        ),
    )
