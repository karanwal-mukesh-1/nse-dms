"""
data/market_data.py
===================
Fetches all price/volume data from Yahoo Finance.
Responsibility: raw data only. No scoring, no signals.
All other modules receive QuoteData objects, never raw yfinance frames.
"""

from __future__ import annotations
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from core.models import QuoteData, CommodityQuote
from config.settings import INDEX_SYMBOLS, SECTORS, COMMODITIES, NIFTY50_STOCKS


# ─── PRIMARY MARKET DATA ─────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_data() -> Dict[str, QuoteData]:
    """
    Fetch 1 year of daily OHLCV for all indices + sectors.
    Returns: symbol → QuoteData
    Cached 5 minutes.
    """
    syms = list(INDEX_SYMBOLS.values()) + [s["sym"] for s in SECTORS]
    results: Dict[str, QuoteData] = {}

    try:
        raw = yf.download(
            tickers=" ".join(syms),
            period="1y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        # Handle single vs multi-ticker response
        if isinstance(raw.columns, pd.MultiIndex):
            close_df  = raw["Close"]
            volume_df = raw.get("Volume", pd.DataFrame())
        else:
            # Single ticker edge case
            close_df  = raw[["Close"]].rename(columns={"Close": syms[0]})
            volume_df = raw[["Volume"]].rename(columns={"Volume": syms[0]}) if "Volume" in raw else pd.DataFrame()

        for sym in syms:
            try:
                c = close_df[sym].dropna() if sym in close_df else pd.Series(dtype=float)
                v = volume_df[sym].dropna() if sym in volume_df.columns else pd.Series(dtype=float)

                if len(c) < 20:
                    continue

                closes = c.values.tolist()
                volumes = v.values.tolist() if len(v) > 0 else []

                # 52-week high/low from rolling window
                roll = c.rolling(252, min_periods=20)
                h52 = float(roll.max().iloc[-1])
                l52 = float(roll.min().iloc[-1])

                results[sym] = QuoteData(
                    symbol=sym,
                    price=float(c.iloc[-1]),
                    prev=float(c.iloc[-2]) if len(c) >= 2 else float(c.iloc[-1]),
                    closes=closes,
                    volumes=volumes,
                    h52=h52,
                    l52=l52,
                    loaded=True,
                )
            except Exception:
                continue

    except Exception as e:
        st.warning(f"Market data fetch error: {e}")

    return results


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nifty50_breadth() -> Optional[Dict]:
    """
    Fetch Nifty50 constituent data for real breadth calculation.
    Cached 1 hour — heavy fetch, run once per session.
    Returns: pct above 50MA, pct above 200MA.
    """
    try:
        raw = yf.download(
            tickers=" ".join(NIFTY50_STOCKS[:30]),
            period="1y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if isinstance(raw.columns, pd.MultiIndex):
            close_df = raw["Close"]
        else:
            return None

        above_50 = 0; above_200 = 0; total = 0
        for sym in close_df.columns:
            c = close_df[sym].dropna().values.tolist()
            if len(c) < 50:
                continue
            price = c[-1]
            ma50  = float(np.mean(c[-50:]))
            total += 1
            if price > ma50:
                above_50 += 1
            if len(c) >= 200:
                ma200 = float(np.mean(c[-200:]))
                if price > ma200:
                    above_200 += 1

        if total == 0:
            return None

        return {
            "pct_above_50ma":  round(above_50  / total * 100, 1),
            "pct_above_200ma": round(above_200 / total * 100, 1),
            "total_stocks":    total,
            "source":          "real_nifty50",
        }
    except Exception:
        return None


# ─── STOCK-LEVEL DATA ─────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def fetch_stock_data(symbols: Tuple[str, ...]) -> Dict[str, QuoteData]:
    """
    Fetch 6 months of daily data for a list of stocks.
    Used by watchlist, sector drilldown, opportunity screener.
    Cached 10 minutes.
    """
    results: Dict[str, QuoteData] = {}
    if not symbols:
        return results

    try:
        if len(symbols) == 1:
            raw = yf.download(
                tickers=symbols[0],
                period="6mo",
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
            if raw.empty:
                return results
            c = raw["Close"].dropna()
            v = raw["Volume"].dropna() if "Volume" in raw else pd.Series(dtype=float)
            if len(c) >= 5:
                closes = c.values.tolist()
                h52 = float(max(closes[-252:]) if len(closes) >= 252 else max(closes))
                l52 = float(min(closes[-252:]) if len(closes) >= 252 else min(closes))
                results[symbols[0]] = QuoteData(
                    symbol=symbols[0],
                    price=float(c.iloc[-1]),
                    prev=float(c.iloc[-2]),
                    closes=closes,
                    volumes=v.values.tolist() if len(v) > 0 else [],
                    h52=h52, l52=l52,
                )
        else:
            raw = yf.download(
                tickers=" ".join(symbols),
                period="6mo",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            if isinstance(raw.columns, pd.MultiIndex):
                close_df  = raw["Close"]
                volume_df = raw.get("Volume", pd.DataFrame())
            else:
                return results

            for sym in symbols:
                try:
                    if sym not in close_df.columns:
                        continue
                    c = close_df[sym].dropna()
                    v = volume_df[sym].dropna() if sym in volume_df.columns else pd.Series(dtype=float)
                    if len(c) < 5:
                        continue
                    closes = c.values.tolist()
                    h52 = float(max(closes[-252:]) if len(closes) >= 252 else max(closes))
                    l52 = float(min(closes[-252:]) if len(closes) >= 252 else min(closes))
                    results[sym] = QuoteData(
                        symbol=sym,
                        price=float(c.iloc[-1]),
                        prev=float(c.iloc[-2]),
                        closes=closes,
                        volumes=v.values.tolist() if len(v) > 0 else [],
                        h52=h52, l52=l52,
                    )
                except Exception:
                    continue

    except Exception as e:
        pass

    return results


# ─── COMMODITIES ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_commodities() -> List[CommodityQuote]:
    """
    Fetch global commodity futures prices.
    Used by the Commodity Spillover panel.
    """
    results = []
    syms = list(COMMODITIES.keys())

    try:
        raw = yf.download(
            tickers=" ".join(syms),
            period="30d",
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        if isinstance(raw.columns, pd.MultiIndex):
            close_df = raw["Close"]
        else:
            return results

        for sym, meta in COMMODITIES.items():
            try:
                if sym not in close_df.columns:
                    continue
                c = close_df[sym].dropna()
                if len(c) < 5:
                    continue
                price   = float(c.iloc[-1])
                prev    = float(c.iloc[-2])
                chg     = ((price - prev) / prev) * 100 if prev else 0.0
                chg_5d  = ((price - float(c.iloc[-6])) / float(c.iloc[-6])) * 100 if len(c) >= 6 else chg

                results.append(CommodityQuote(
                    symbol=sym,
                    name=meta["name"],
                    price=round(price, 2),
                    chg_pct=round(chg, 2),
                    chg_5d_pct=round(chg_5d, 2),
                    loaded=True,
                    nse_sectors=meta.get("nse_sectors", []),
                    direction=meta.get("direction", 0),
                ))
            except Exception:
                continue

    except Exception:
        pass

    return results


# ─── MACRO DATA (RBI / GOVT) ──────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)  # cache 24 hours
def fetch_india_10y_yield() -> Optional[float]:
    """India 10-year G-Sec yield proxy via GSEC10Y=IN or ^TNX adjusted."""
    try:
        # Use US 10Y as proxy adjusted for India spread
        raw = yf.download("^TNX", period="5d", interval="1d", progress=False)
        if not raw.empty:
            us10y = float(raw["Close"].dropna().iloc[-1])
            # India-US spread historically ~3-4%. Use 3.5% as base.
            return round(us10y + 3.5, 2)
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_put_call_ratio() -> Optional[Dict]:
    """
    NSE options PCR — estimated from VIX trend as proxy.
    True PCR requires NSE options chain data (premium endpoint).
    Returns estimated PCR and signal.
    """
    try:
        market = fetch_market_data()
        vix_q = market.get("^INDIAVIX")
        if not vix_q:
            return None

        vix = vix_q.price
        vix_slope = ((vix_q.closes[-1] - vix_q.closes[-6]) / vix_q.closes[-6]) * 100 if len(vix_q.closes) >= 6 else 0

        # PCR interpretation proxy
        if vix < 14 and vix_slope < 0:
            signal = "COMPLACENT"   # Low PCR likely — retail buying calls, overconfident
            pcr_est = 0.75
        elif vix > 22:
            signal = "FEARFUL"      # High PCR likely — protective puts being bought
            pcr_est = 1.4
        else:
            signal = "NEUTRAL"
            pcr_est = 1.0

        return {
            "pcr_estimated": pcr_est,
            "signal": signal,
            "vix_used": vix,
            "note": "Estimated proxy — true PCR requires NSE options endpoint",
        }
    except Exception:
        return None
