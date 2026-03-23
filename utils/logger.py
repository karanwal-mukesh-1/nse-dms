"""
utils/logger.py
================
Structured logging for the DMS.
Every data fetch, score computation, and AI call is logged with:
  - timestamp
  - module
  - outcome (success/fail/fallback)
  - duration

This is what separates a production system from a demo:
you can see exactly what failed, why, and when.
"""

from __future__ import annotations
import logging
import time
import functools
from typing import Callable, Any
from datetime import datetime


# ─── CONFIGURE ROOT LOGGER ────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Use module __name__ as the name."""
    return logging.getLogger(name)


# ─── TIMING DECORATOR ────────────────────────────────────────────────────────

def timed(logger_name: str = ""):
    """
    Decorator that logs function call duration and outcome.
    Usage:
        @timed("data.market_data")
        def fetch_market_data(): ...
    """
    def decorator(fn: Callable) -> Callable:
        log = get_logger(logger_name or fn.__module__)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result   = fn(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                log.info(f"{fn.__name__} → OK ({duration:.0f}ms)")
                return result
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                log.warning(f"{fn.__name__} → FAILED ({duration:.0f}ms): {e}")
                raise
        return wrapper
    return decorator


# ─── DATA FETCH LOGGER ───────────────────────────────────────────────────────

class FetchLog:
    """
    Tracks data fetch outcomes across a session.
    Displayed in the sidebar as a data quality indicator.
    """

    def __init__(self):
        self._log: list[dict] = []

    def record(self, source: str, outcome: str, detail: str = "", rows: int = 0):
        """
        Record a data fetch outcome.
        outcome: 'ok' | 'fallback' | 'failed' | 'blocked'
        """
        self._log.append({
            "time":    datetime.now().strftime("%H:%M:%S"),
            "source":  source,
            "outcome": outcome,
            "detail":  detail,
            "rows":    rows,
        })

    def summary(self) -> dict:
        ok       = sum(1 for r in self._log if r["outcome"] == "ok")
        fallback = sum(1 for r in self._log if r["outcome"] == "fallback")
        failed   = sum(1 for r in self._log if r["outcome"] in ("failed", "blocked"))
        return {"ok": ok, "fallback": fallback, "failed": failed, "total": len(self._log)}

    def recent(self, n: int = 10) -> list[dict]:
        return self._log[-n:]

    def clear(self):
        self._log.clear()


# Module-level instance — imported by data modules
fetch_log = FetchLog()
