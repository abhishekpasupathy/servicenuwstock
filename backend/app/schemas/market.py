from datetime import date, datetime

from pydantic import BaseModel, Field


class QuoteResponse(BaseModel):
    ticker: str
    name: str | None = None
    currency: str | None = None
    exchange: str | None = None
    price: float | None = None
    previous_close: float | None = None
    open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: int | None = None
    market_cap: int | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    source: str = "yfinance"
    is_degraded: bool = False
    provider_message: str | None = None
    fetched_at: datetime


class HistoryPoint(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    adj_close: float | None = None
    volume: int


class HistoryResponse(BaseModel):
    ticker: str
    period: str
    interval: str
    points: list[HistoryPoint]
    source: str = "yfinance"
    is_degraded: bool = False
    provider_message: str | None = None
    fetched_at: datetime


class ProfileResponse(BaseModel):
    ticker: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    website: str | None = None
    employees: int | None = None
    business_summary: str | None = Field(default=None, max_length=5000)
    source: str = "yfinance"
    is_degraded: bool = False
    provider_message: str | None = None
    fetched_at: datetime


class SnapshotMetadata(BaseModel):
    ticker: str
    period: str
    interval: str
    source: str
    is_degraded: bool
    provider_message: str | None = None
    fetched_at: datetime


class SnapshotResponse(BaseModel):
    quote: QuoteResponse
    profile: ProfileResponse
    history: HistoryResponse
    metadata: SnapshotMetadata
