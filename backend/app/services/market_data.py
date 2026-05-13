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
        return cached

    payload = persistent_cache.get(cache_key)
    if payload is None:
        return None

    response = model_type.model_validate_json(payload)  # type: ignore[attr-defined]
    cache.set(cache_key, response)
    return response


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
    name = "ServiceNow Inc." if ticker == "NOW" else f"{ticker} sample profile"
    return ProfileResponse(
        ticker=ticker,
        name=name,
        sector="Technology",
        industry="Software - Application",
        country="United States",
        website="https://www.servicenow.com" if ticker == "NOW" else None,
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
    base_price = 734.25 if ticker == "NOW" else 100.0 + (sum(ord(char) for char in ticker) % 250)
    previous_close = round(base_price * 0.992, 2)
    return QuoteResponse(
        ticker=ticker,
        name="ServiceNow Inc." if ticker == "NOW" else f"{ticker} sample quote",
        currency="USD",
        exchange="Sample",
        price=round(base_price, 2),
        previous_close=previous_close,
        open=round(previous_close * 1.002, 2),
        day_high=round(base_price * 1.018, 2),
        day_low=round(base_price * 0.982, 2),
        volume=1_250_000 + (sum(ord(char) for char in ticker) * 1_000),
        market_cap=None,
        fifty_two_week_high=round(base_price * 1.24, 2),
        fifty_two_week_low=round(base_price * 0.72, 2),
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
    base_price = 734.25 if ticker == "NOW" else 100.0 + (sum(ord(char) for char in ticker) % 250)
    points: list[HistoryPoint] = []

    for offset in range(0, days + 1, step):
        current_date = start + timedelta(days=offset)
        drift = offset / max(days, 1)
        wave = ((offset % 23) - 11) / 250
        close = round(base_price * (0.82 + drift * 0.24 + wave), 2)
        points.append(
            HistoryPoint(
                date=current_date,
                open=round(close * 0.996, 2),
                high=round(close * 1.012, 2),
                low=round(close * 0.988, 2),
                close=close,
                adj_close=close,
                volume=950_000 + ((offset + len(ticker)) % 40) * 18_000,
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


def get_quote(ticker: str) -> QuoteResponse:
    ticker = normalize_ticker(ticker)
    cache_key = f"quote:{ticker}"
    cached = _get_cached_response(cache_key, QuoteResponse)
    if cached is not None:
        return cached

    try:
        info = _ticker_info(ticker)
    except UpstreamProviderError as exc:
        response = _sample_quote(ticker, str(exc))
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
        raise MarketDataError(f"No historical data found for ticker '{ticker}'.")

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
