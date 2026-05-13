from dataclasses import dataclass
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, CacheEntry[object]] = {}

    def get(self, key: str) -> object | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at <= monotonic():
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        self._store[key] = CacheEntry(
            value=value,
            expires_at=monotonic() + (ttl_seconds or self.ttl_seconds),
        )
