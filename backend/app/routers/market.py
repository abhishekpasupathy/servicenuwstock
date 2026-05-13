import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.schemas.market import (
    HistoryResponse,
    ProfileResponse,
    QuoteResponse,
    SnapshotResponse,
)
from app.services.market_data import (
    MarketDataError,
    UpstreamProviderError,
    UpstreamRateLimitError,
    get_history,
    get_profile,
    get_quote,
    get_snapshot,
)

router = APIRouter(tags=["market-data"])


@router.get("/snapshot/{ticker}", response_model=SnapshotResponse)
async def snapshot(
    ticker: str,
    period: str = Query(default="1y", pattern="^[0-9]+(d|mo|y)$|^(ytd|max)$"),
    interval: str = Query(default="1d", pattern="^[0-9]+(m|h|d|wk|mo)$"),
) -> SnapshotResponse:
    try:
        return await asyncio.to_thread(get_snapshot, ticker, period, interval)
    except MarketDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UpstreamRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except UpstreamProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="The market data provider returned an unexpected snapshot response.",
        ) from exc


@router.get("/quote/{ticker}", response_model=QuoteResponse)
async def quote(ticker: str) -> QuoteResponse:
    try:
        return await asyncio.to_thread(get_quote, ticker)
    except MarketDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UpstreamRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except UpstreamProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="The market data provider returned an unexpected quote response.",
        ) from exc


@router.get("/history/{ticker}", response_model=HistoryResponse)
async def history(
    ticker: str,
    period: str = Query(default="1y", pattern="^[0-9]+(d|mo|y)$|^(ytd|max)$"),
    interval: str = Query(default="1d", pattern="^[0-9]+(m|h|d|wk|mo)$"),
) -> HistoryResponse:
    try:
        return await asyncio.to_thread(get_history, ticker, period, interval)
    except MarketDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UpstreamRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except UpstreamProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="The market data provider returned an unexpected history response.",
        ) from exc


@router.get("/profile/{ticker}", response_model=ProfileResponse)
async def profile(ticker: str) -> ProfileResponse:
    try:
        return await asyncio.to_thread(get_profile, ticker)
    except MarketDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UpstreamRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except UpstreamProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="The market data provider returned an unexpected profile response.",
        ) from exc
