from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")
OPEN_TIME = time(9, 30)
CLOSE_TIME = time(16, 0)

NYSE_HOLIDAYS = {
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    "2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
}


def _is_trading_day(value: datetime) -> bool:
    local = value.astimezone(ET)
    return local.weekday() < 5 and local.date().isoformat() not in NYSE_HOLIDAYS


def _session_bounds(value: datetime) -> tuple[datetime, datetime]:
    local = value.astimezone(ET)
    return (
        datetime.combine(local.date(), OPEN_TIME, ET),
        datetime.combine(local.date(), CLOSE_TIME, ET),
    )


def _next_trading_day_start(value: datetime) -> datetime:
    cursor = value.astimezone(ET) + timedelta(days=1)
    cursor = cursor.replace(hour=9, minute=30, second=0, microsecond=0)
    while not _is_trading_day(cursor):
        cursor += timedelta(days=1)
    return cursor


def _duration_message(prefix: str, target: datetime, now: datetime) -> str:
    seconds = max(0, int((target - now.astimezone(ET)).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"{prefix} in {hours}h {minutes}m"
    return f"{prefix} in {minutes}m"


def is_market_open(now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    if not _is_trading_day(current):
        return False
    open_at, close_at = _session_bounds(current)
    local = current.astimezone(ET)
    return open_at <= local < close_at


def get_market_status(now: datetime | None = None) -> dict:
    current = now or datetime.now(UTC)
    local = current.astimezone(ET)

    if not _is_trading_day(current):
        next_open = _next_trading_day_start(current)
        return {
            "is_open": False,
            "status": "CLOSED",
            "next_open": next_open.astimezone(UTC).isoformat(),
            "next_close": None,
            "message": _duration_message("Market opens", next_open, current),
            "timestamp": current.astimezone(UTC).isoformat(),
        }

    open_at, close_at = _session_bounds(current)
    if local < open_at:
        return {
            "is_open": False,
            "status": "PRE_MARKET",
            "next_open": open_at.astimezone(UTC).isoformat(),
            "next_close": close_at.astimezone(UTC).isoformat(),
            "message": _duration_message("Market opens", open_at, current),
            "timestamp": current.astimezone(UTC).isoformat(),
        }
    if local >= close_at:
        next_open = _next_trading_day_start(current)
        return {
            "is_open": False,
            "status": "AFTER_HOURS",
            "next_open": next_open.astimezone(UTC).isoformat(),
            "next_close": None,
            "message": _duration_message("Market opens", next_open, current),
            "timestamp": current.astimezone(UTC).isoformat(),
        }

    return {
        "is_open": True,
        "status": "OPEN",
        "next_open": open_at.astimezone(UTC).isoformat(),
        "next_close": close_at.astimezone(UTC).isoformat(),
        "message": _duration_message("Market closes", close_at, current),
        "timestamp": current.astimezone(UTC).isoformat(),
    }
