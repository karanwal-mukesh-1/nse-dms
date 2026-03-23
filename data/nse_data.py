"""
data/nse_data.py
================
Fetches NSE-specific public data:
  - Bulk & Block Deals
  - Insider / Promoter Activity (SEBI PIT disclosures)
  - FII / DII provisional flow
  - Macro indicators: GST, Power consumption (where available)

All data is public. NSE requires browser-like session for some endpoints.
Failures are handled gracefully — all functions return empty lists / None.
"""

from __future__ import annotations
import streamlit as st
import requests
import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from core.models import BulkDeal, InsiderActivity, MacroIndicator
from config.settings import SECTORS
from utils.logger import get_logger, fetch_log

_log = get_logger(__name__)


# ─── SHARED SESSION ───────────────────────────────────────────────────────────

def _nse_session() -> requests.Session:
    """
    Create a browser-like session for NSE endpoints.
    NSE blocks non-browser requests — this mimics a Chrome browser.
    """
    session = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer":         "https://www.nseindia.com/",
        "Origin":          "https://www.nseindia.com",
    }
    session.headers.update(headers)
    try:
        # Prime the session with a cookie hit
        session.get("https://www.nseindia.com", timeout=8)
    except Exception as e:
        _log.debug(f"NSE session prime failed (non-critical): {e}")
    return session


# ─── BULK & BLOCK DEALS ───────────────────────────────────────────────────────

def _classify_bulk_deal(client: str, deal_type: str, value_cr: float) -> tuple[str, int]:
    """
    Classify a bulk deal by buyer/seller identity.
    Returns (signal_type, conviction 0-3).
    """
    client_upper = client.upper()

    # FII / Foreign institution keywords
    fii_keywords = ["FII", "FPI", "FOREIGN", "MORGAN", "GOLDMAN", "CITI", "MACQUARIE",
                     "NOMURA", "BARCLAYS", "MERRILL", "DEUTSCHE", "UBS", "CREDIT SUISSE",
                     "SOCIETE", "BNP", "HSBC", "JPMORGAN", "J.P.", "BLACKROCK",
                     "VANGUARD", "FIDELITY", "INVESCO", "ABERDEEN"]
    # DII / Domestic institution keywords
    dii_keywords  = ["LIC", "HDFC MF", "SBI MF", "ICICI PRU", "AXIS MF", "KOTAK MF",
                     "NIPPON", "UTI", "BIRLA", "RELIANCE MF", "EDELWEISS",
                     "INSURANCE", "PENSION", "NPS"]
    # Promoter keywords
    prom_keywords = ["PROMOTER", "CHAIRMAN", "MD ", "CEO", "DIRECTOR", "FAMILY",
                     "TRUST", "HOLDING", "CAPITAL RESEARCH"]

    is_fii   = any(k in client_upper for k in fii_keywords)
    is_dii   = any(k in client_upper for k in dii_keywords)
    is_prom  = any(k in client_upper for k in prom_keywords)

    if deal_type.upper() == "BUY":
        if is_fii:
            conviction = 3 if value_cr > 100 else 2
            return "FII_BUY", conviction
        elif is_dii:
            conviction = 2 if value_cr > 50 else 1
            return "DII_BUY", conviction
        elif is_prom:
            return "PROMOTER_BUY", 3
        else:
            return "INSTITUTIONAL_BUY", 1
    else:  # SELL
        if is_prom:
            conviction = 3 if value_cr > 50 else 1
            return "PROMOTER_SELL", conviction
        elif is_fii:
            return "FII_SELL", 2
        else:
            return "INSTITUTIONAL_SELL", 1


def _map_to_sector(symbol: str) -> Optional[str]:
    """Map a stock symbol to its sector short name."""
    sym_clean = symbol.upper().replace(".NS", "").replace(".BO", "")
    for sector in SECTORS:
        for stock in sector.get("stocks", []):
            if sym_clean in stock.upper():
                return sector["short"]
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bulk_deals(days_back: int = 5) -> List[BulkDeal]:
    """
    Fetch recent bulk deals from NSE.
    NSE endpoint: /api/snapshot-capital-market-largedeal
    Classified by buyer identity and mapped to sectors.
    """
    deals: List[BulkDeal] = []
    session = _nse_session()

    try:
        url  = "https://www.nseindia.com/api/snapshot-capital-market-largedeal"
        resp = session.get(url, timeout=10)

        if resp.status_code != 200:
            return deals

        data = resp.json()
        rows = data.get("data", data) if isinstance(data, dict) else data

        for row in rows[:50]:   # last 50 deals
            try:
                qty   = float(str(row.get("tdcoquantity", row.get("quantity", 0))).replace(",", ""))
                price = float(str(row.get("tdcoprice", row.get("price", 0))).replace(",", ""))
                val   = round(qty * price / 1e7, 2)  # in crores

                deal_type = str(row.get("tdcobuyersellerflag", row.get("dealType", "B"))).upper()
                deal_type = "BUY" if deal_type.startswith("B") else "SELL"

                client = str(row.get("tdcoclientname", row.get("client", "")))
                symbol = str(row.get("tdcosymbol", row.get("symbol", "")))

                signal_type, conviction = _classify_bulk_deal(client, deal_type, val)
                sector = _map_to_sector(symbol)

                deals.append(BulkDeal(
                    date=str(row.get("tdcotradedate", row.get("date", ""))),
                    symbol=symbol,
                    name=str(row.get("tdcosecname", symbol)),
                    client=client,
                    deal_type=deal_type,
                    quantity=qty,
                    price=price,
                    value_cr=val,
                    sector=sector,
                    signal_type=signal_type,
                    conviction=conviction,
                ))
            except Exception:
                continue

    except Exception as e:
        _log.warning(f"fetch_bulk_deals failed: {e}")
        fetch_log.record("nse_bulk_deals", "failed", str(e))

    return deals


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_block_deals(days_back: int = 5) -> List[BulkDeal]:
    """
    Fetch block deals (negotiated large trades).
    NSE endpoint: /api/block-deal
    """
    deals: List[BulkDeal] = []
    session = _nse_session()

    try:
        url  = "https://www.nseindia.com/api/block-deal"
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            return deals

        data = resp.json()
        rows = data.get("data", []) if isinstance(data, dict) else data

        for row in rows[:30]:
            try:
                qty   = float(str(row.get("quantity", 0)).replace(",", ""))
                price = float(str(row.get("price", 0)).replace(",", ""))
                val   = round(qty * price / 1e7, 2)
                deal_type = "BUY" if str(row.get("BuyQty", "0")) != "0" else "SELL"
                client    = str(row.get("clientName", row.get("client", "")))
                symbol    = str(row.get("symbol", ""))
                signal_type, conviction = _classify_bulk_deal(client, deal_type, val)
                sector = _map_to_sector(symbol)

                deals.append(BulkDeal(
                    date=str(row.get("date", "")),
                    symbol=symbol,
                    name=symbol,
                    client=client,
                    deal_type=deal_type,
                    quantity=qty,
                    price=price,
                    value_cr=val,
                    sector=sector,
                    signal_type=signal_type,
                    conviction=conviction,
                ))
            except Exception:
                continue
    except Exception as e:
        _log.warning(f"fetch_block_deals failed: {e}")

    return deals


# ─── INSIDER / PROMOTER ACTIVITY ──────────────────────────────────────────────

def _classify_insider(transaction: str, person: str, designation: str,
                       near_52w_low: bool) -> str:
    """Classify insider transaction type and signal."""
    txn = transaction.upper()
    des = designation.upper()

    is_promoter = any(k in des for k in ["PROMOTER", "CHAIRMAN", "MD", "CEO",
                                          "DIRECTOR", "FOUNDER"])

    if "REVOK" in txn or "RELEASE" in txn:
        return "PLEDGE_REVOKED"     # positive signal
    if "INVOK" in txn or "PLEDG" in txn:
        return "PLEDGE_INVOKED"     # danger signal
    if txn.startswith("BUY") or txn == "ACQUISITION":
        if is_promoter and near_52w_low:
            return "PROMOTER_BUY_NEAR_LOW"   # highest conviction
        elif is_promoter:
            return "PROMOTER_BUY"
        else:
            return "INSIDER_BUY"
    if txn.startswith("SELL") or txn == "DISPOSAL":
        if is_promoter:
            return "PROMOTER_SELL"
        return "INSIDER_SELL"
    return "NEUTRAL"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_insider_activity(days_back: int = 10) -> List[InsiderActivity]:
    """
    Fetch SEBI PIT (Prohibition of Insider Trading) disclosures from NSE.
    """
    activities: List[InsiderActivity] = []
    session = _nse_session()

    try:
        url  = "https://www.nseindia.com/api/corporates-pit"
        params = {"index": "equities", "limit": 100}
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return activities

        data = resp.json()
        rows = data.get("data", []) if isinstance(data, dict) else data

        for row in rows[:80]:
            try:
                symbol = str(row.get("symbol", ""))
                person = str(row.get("personName", row.get("acqName", "")))
                desig  = str(row.get("personCategory", row.get("personType", "")))
                txn    = str(row.get("transactionType", row.get("acqMode", "")))
                qty    = float(str(row.get("secAcq", row.get("noSecAcq", "0"))).replace(",", ""))
                price  = float(str(row.get("tradedPrice", row.get("secType", "0"))).replace(",", "")) if row.get("tradedPrice") else None
                val    = round(qty * price / 1e7, 3) if price and qty else None

                signal_type = _classify_insider(txn, person, desig, near_52w_low=False)

                activities.append(InsiderActivity(
                    date=str(row.get("date", row.get("acqfromDt", ""))),
                    symbol=symbol,
                    name=str(row.get("companyName", symbol)),
                    person=person,
                    designation=desig,
                    transaction=txn,
                    quantity=qty,
                    price=price,
                    value_cr=val,
                    signal_type=signal_type,
                    near_52w_low=False,
                ))
            except Exception:
                continue

    except Exception as e:
        _log.warning(f"fetch_insider_activity failed: {e}")
        fetch_log.record("nse_insider", "failed", str(e))

    return activities


# ─── FII / DII FLOW ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fii_dii_flow(days: int = 10) -> Optional[List[Dict]]:
    """
    NSE FII/DII provisional daily activity.
    """
    session = _nse_session()
    try:
        url  = "https://www.nseindia.com/api/fiidiiTradeReact"
        resp = session.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        rows = []
        for item in data[:days]:
            try:
                rows.append({
                    "date":    item.get("date", ""),
                    "fii_net": float(str(item.get("fiinet", "0")).replace(",", "")),
                    "dii_net": float(str(item.get("diinet", "0")).replace(",", "")),
                    "fii_buy": float(str(item.get("fiibuy", "0")).replace(",", "")),
                    "fii_sell":float(str(item.get("fiisell","0")).replace(",", "")),
                    "dii_buy": float(str(item.get("diibuy", "0")).replace(",", "")),
                    "dii_sell":float(str(item.get("diisell","0")).replace(",", "")),
                })
            except Exception:
                continue
        return rows if rows else None
    except Exception as e:
        _log.warning(f"fetch_fii_dii_flow failed: {e}")
        fetch_log.record("nse_fii_dii", "failed", str(e))
        return None


# ─── MACRO INDICATORS ─────────────────────────────────────────────────────────

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_macro_indicators() -> List[MacroIndicator]:
    """
    Fetch available macro indicators.
    Sources: RBI, Finance Ministry, Ministry of Power (where accessible).
    Many of these are updated monthly — cached 24 hours.
    """
    indicators: List[MacroIndicator] = []

    # GST Collections — Finance Ministry public data
    try:
        resp = requests.get(
            "https://www.gstcouncil.gov.in/gst-revenue-collection-data",
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        # Parse if successful — structure varies, use as fallback
        # For now we add a placeholder that explains data source
        indicators.append(MacroIndicator(
            name="GST Collections",
            value=0.0,
            unit="₹ Cr",
            trend="UNKNOWN",
            signal="NEUTRAL",
            source="gstcouncil.gov.in",
            as_of="",
        ))
    except Exception as e:
        _log.debug(f"fetch_macro_indicators: {e}")

    return indicators


# ─── CLUSTER ANALYSIS ─────────────────────────────────────────────────────────

def detect_insider_clusters(activities: List[InsiderActivity],
                              window_days: int = 10) -> List[Dict]:
    """
    Detect cluster insider buying: 3+ insiders buying within window_days.
    This is the highest-conviction insider signal.
    """
    if not activities:
        return []

    # Group by symbol
    by_symbol: Dict[str, List[InsiderActivity]] = {}
    for a in activities:
        if a.symbol not in by_symbol:
            by_symbol[a.symbol] = []
        by_symbol[a.symbol].append(a)

    clusters = []
    for symbol, acts in by_symbol.items():
        buys = [a for a in acts if "BUY" in a.signal_type.upper() or
                                   a.transaction.upper() in ("BUY", "ACQUISITION")]
        if len(buys) >= 2:
            clusters.append({
                "symbol":  symbol,
                "name":    buys[0].name,
                "count":   len(buys),
                "buyers":  [b.person for b in buys],
                "total_value_cr": sum(b.value_cr or 0 for b in buys),
                "signal":  "CLUSTER_BUY" if len(buys) >= 3 else "MULTI_BUY",
                "conviction": 3 if len(buys) >= 3 else 2,
            })

    return sorted(clusters, key=lambda x: x["conviction"], reverse=True)
