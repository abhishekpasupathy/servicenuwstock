import sqlite3
from pathlib import Path
from time import time


class PersistentCache:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.sqlite_path)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_market_cache_expires_at ON market_cache (expires_at)"
            )

    def get(self, cache_key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload, expires_at FROM market_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()

            if row is None:
                return None

            payload, expires_at = row
            if float(expires_at) <= time():
                connection.execute(
                    "DELETE FROM market_cache WHERE cache_key = ?",
                    (cache_key,),
                )
                return None

            return str(payload)

    def set(self, cache_key: str, payload: str, ttl_seconds: int) -> None:
        now = time()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO market_cache (cache_key, payload, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    expires_at = excluded.expires_at,
                    created_at = excluded.created_at
                """,
                (cache_key, payload, now + ttl_seconds, now),
            )
