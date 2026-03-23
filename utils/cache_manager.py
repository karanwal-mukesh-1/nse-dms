"""
utils/cache_manager.py
=======================
Cache management utilities.

Streamlit's @st.cache_data handles the caching itself.
This module manages:
  1. Cache key generation (consistent, reproducible)
  2. Selective invalidation (clear only what's stale)
  3. Cache health monitoring (what's cached, how old)
  4. Staggered TTLs (prices vs breadth vs NSE data)
"""

from __future__ import annotations
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional


# ─── TTL CONSTANTS ────────────────────────────────────────────────────────────
# These mirror the TTL values in data/*.py
# Change once here to change everywhere (eventually — for now also update @st.cache_data)

TTL = {
    "market_prices":    300,    # 5 min  — price data
    "stock_drilldown":  600,    # 10 min — individual stock data
    "nifty50_breadth":  3600,   # 1 hr   — heavy fetch
    "nse_bulk_deals":   3600,   # 1 hr   — NSE rate-limit friendly
    "nse_insider":      3600,   # 1 hr
    "nse_fii_dii":      3600,   # 1 hr
    "commodities":      300,    # 5 min
    "india_yield":      86400,  # 24 hr
    "groq_analysis":    None,   # manual only — user triggers regeneration
}


# ─── SESSION STATE CACHE LOG ──────────────────────────────────────────────────

def record_cache_hit(key: str):
    """Record when a cache was last populated."""
    if "cache_log" not in st.session_state:
        st.session_state["cache_log"] = {}
    st.session_state["cache_log"][key] = datetime.now()


def get_cache_age(key: str) -> Optional[timedelta]:
    """How old is this cache entry? None if never populated."""
    log = st.session_state.get("cache_log", {})
    if key not in log:
        return None
    return datetime.now() - log[key]


def is_stale(key: str) -> bool:
    """Is this cache entry past its TTL?"""
    age = get_cache_age(key)
    if age is None:
        return True
    ttl = TTL.get(key)
    if ttl is None:
        return False
    return age.total_seconds() > ttl


# ─── SELECTIVE INVALIDATION ───────────────────────────────────────────────────

def clear_price_cache():
    """Clear only price-sensitive caches, keep heavy fetches."""
    st.cache_data.clear()
    for key in list(st.session_state.get("cache_log", {}).keys()):
        if key in ("market_prices", "commodities"):
            st.session_state["cache_log"].pop(key, None)


def clear_all_cache():
    """Clear everything including heavy fetches. Used on full refresh."""
    st.cache_data.clear()
    st.session_state.pop("cache_log", None)
    st.session_state.pop("groq_analysis", None)


def clear_groq_cache():
    """Force Groq regeneration without clearing market data."""
    st.session_state.pop("groq_analysis", None)


# ─── CACHE STATUS REPORTER ────────────────────────────────────────────────────

def cache_status_html() -> str:
    """
    Returns HTML for cache status display in sidebar.
    Shows which data sources are fresh vs stale.
    """
    sources = {
        "Prices":      "market_prices",
        "Breadth":     "nifty50_breadth",
        "Bulk Deals":  "nse_bulk_deals",
        "Insider":     "nse_insider",
        "FII/DII":     "nse_fii_dii",
        "Commodities": "commodities",
    }
    rows = []
    for label, key in sources.items():
        age  = get_cache_age(key)
        ttl  = TTL.get(key, 300)

        if age is None:
            dot_col = "#3a5a7f"
            age_str = "not loaded"
        else:
            secs    = age.total_seconds()
            pct     = min(1.0, secs / ttl) if ttl else 0
            dot_col = "#00ff88" if pct < 0.5 else "#ffb300" if pct < 0.9 else "#ff4444"
            mins    = int(secs // 60)
            age_str = f"{mins}m ago" if mins > 0 else "just now"

        rows.append(
            f'<div style="display:flex;justify-content:space-between;margin-bottom:2px">'
            f'<span style="color:#3a5a7f;font-family:JetBrains Mono,monospace;font-size:8px">{label}</span>'
            f'<span style="color:{dot_col};font-family:JetBrains Mono,monospace;font-size:8px">{age_str}</span>'
            f'</div>'
        )
    return "\n".join(rows)
