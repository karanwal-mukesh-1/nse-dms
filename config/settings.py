"""
config/settings.py
==================
Single source of truth for all configuration.
Change anything here — nothing else needs touching.
"""

from dataclasses import dataclass, field
from typing import Dict, List


# ─── SCORING WEIGHTS ──────────────────────────────────────────────────────────
# Must sum to 1.0
SCORE_WEIGHTS: Dict[str, float] = {
    "volatility": 0.20,
    "trend":      0.20,
    "momentum":   0.20,
    "breadth":    0.15,
    "macro":      0.10,
    "smart_money":0.10,
    "lifecycle":  0.05,  # sector lifecycle stage bonus
}

# ─── DECISION THRESHOLDS ──────────────────────────────────────────────────────
DECISION_THRESHOLDS = {
    "strong_yes": 82,   # composite + conviction both high
    "yes":        72,
    "caution":    58,
    # below caution = NO
}

CONVICTION_THRESHOLD_FOR_STRONG = 65  # conviction score needed alongside 82+ composite

# ─── NSE INDEX SYMBOLS (Yahoo Finance) ────────────────────────────────────────
INDEX_SYMBOLS: Dict[str, str] = {
    "nifty50":   "^NSEI",
    "banknifty": "^NSEBANK",
    "midcap":    "^NSMIDCP",
    "india_vix": "^INDIAVIX",
    "dxy":       "DX-Y.NYB",
}

# ─── SECTOR DEFINITIONS ───────────────────────────────────────────────────────
SECTORS = [
    {
        "sym":     "^CNXIT",
        "name":    "Nifty IT",
        "short":   "IT",
        "stocks":  ["INFY.NS","TCS.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS"],
        "commodity_proxy": None,
        "rate_sensitivity": -1,   # -1=benefits from rate CUTS, +1=hurt by cuts
    },
    {
        "sym":     "^NSEBANK",
        "name":    "Nifty Bank",
        "short":   "BANK",
        "stocks":  ["HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS"],
        "commodity_proxy": None,
        "rate_sensitivity": +1,
    },
    {
        "sym":     "^CNXPHARMA",
        "name":    "Nifty Pharma",
        "short":   "PHARMA",
        "stocks":  ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","APOLLOHOSP.NS"],
        "commodity_proxy": None,
        "rate_sensitivity": 0,
    },
    {
        "sym":     "^CNXFMCG",
        "name":    "Nifty FMCG",
        "short":   "FMCG",
        "stocks":  ["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS"],
        "commodity_proxy": "CL=F",   # crude affects input costs
        "rate_sensitivity": -1,
    },
    {
        "sym":     "^CNXAUTO",
        "name":    "Nifty Auto",
        "short":   "AUTO",
        "stocks":  ["MARUTI.NS","M&M.NS","TATAMOTORS.NS","BAJAJ-AUTO.NS","EICHERMOT.NS"],
        "commodity_proxy": "HG=F",   # copper (wiring)
        "rate_sensitivity": -1,
    },
    {
        "sym":     "^CNXMETAL",
        "name":    "Nifty Metal",
        "short":   "METAL",
        "stocks":  ["TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","COALINDIA.NS","VEDL.NS"],
        "commodity_proxy": "HG=F",   # copper
        "rate_sensitivity": 0,
    },
    {
        "sym":     "^CNXREALTY",
        "name":    "Nifty Realty",
        "short":   "REALTY",
        "stocks":  ["DLF.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS","BRIGADE.NS"],
        "commodity_proxy": None,
        "rate_sensitivity": -2,  # strongly benefits from rate cuts
    },
    {
        "sym":     "^CNXPSUbank",
        "name":    "Nifty PSU Bank",
        "short":   "PSU",
        "stocks":  ["SBIN.NS","PNB.NS","BANKBARODA.NS","CANARABANK.NS","UNIONBANK.NS"],
        "commodity_proxy": None,
        "rate_sensitivity": +1,
    },
    {
        "sym":     "^CNXENERGY",
        "name":    "Nifty Energy",
        "short":   "ENERGY",
        "stocks":  ["RELIANCE.NS","ONGC.NS","NTPC.NS","POWERGRID.NS","BPCL.NS"],
        "commodity_proxy": "CL=F",   # crude oil
        "rate_sensitivity": 0,
    },
    {
        "sym":     "^CNXINFRA",
        "name":    "Nifty Infra",
        "short":   "INFRA",
        "stocks":  ["LT.NS","ADANIPORTS.NS","LTIM.NS","IRFC.NS","RECLTD.NS"],
        "commodity_proxy": "HG=F",
        "rate_sensitivity": -1,
    },
]

# ─── GLOBAL COMMODITIES PANEL ─────────────────────────────────────────────────
COMMODITIES: Dict[str, Dict] = {
    "CL=F":  {"name": "Crude Oil",    "unit": "$/bbl",   "nse_sectors": ["ENERGY","FMCG"],     "direction": +1},
    "HG=F":  {"name": "Copper",       "unit": "$/lb",    "nse_sectors": ["METAL","AUTO","INFRA"],"direction": +1},
    "SI=F":  {"name": "Silver",       "unit": "$/oz",    "nse_sectors": ["METAL"],              "direction": +1},
    "GC=F":  {"name": "Gold",         "unit": "$/oz",    "nse_sectors": [],                     "direction": 0},
    "ZW=F":  {"name": "Wheat",        "unit": "$/bu",    "nse_sectors": ["FMCG"],               "direction": -1},
    "NG=F":  {"name": "Natural Gas",  "unit": "$/mmBtu", "nse_sectors": ["ENERGY"],             "direction": +1},
}

# ─── RATE CYCLE STAGES & SECTOR PLAYBOOK ──────────────────────────────────────
RATE_CYCLE_PLAYBOOK = {
    "cutting_aggressive": {
        "description": "RBI cutting rates aggressively (>50bps in 6 months)",
        "outperform":  ["REALTY","AUTO","BANK","INFRA","FMCG"],
        "underperform":["IT","PHARMA"],
        "positioning": "Cyclicals over defensives. Rate-sensitives lead.",
    },
    "cutting_moderate": {
        "description": "RBI cutting slowly (25-50bps in 6 months)",
        "outperform":  ["BANK","AUTO","INFRA"],
        "underperform":["IT"],
        "positioning": "Selective cyclicals. Quality bias.",
    },
    "neutral": {
        "description": "RBI on hold",
        "outperform":  ["IT","PHARMA","FMCG"],
        "underperform":["REALTY","INFRA"],
        "positioning": "Defensives and earners. Avoid rate-sensitives.",
    },
    "hiking": {
        "description": "RBI hiking rates",
        "outperform":  ["IT","PHARMA","PSU"],
        "underperform":["REALTY","AUTO","BANK"],
        "positioning": "Defensives. Reduce cyclicals. Cash is attractive.",
    },
}

# ─── SECTOR LIFECYCLE STAGES ──────────────────────────────────────────────────
LIFECYCLE_STAGES = {
    "neglected":   {"label": "NEGLECTED",    "color": "#4a9eff", "score_bonus": +10},
    "discovered":  {"label": "DISCOVERED",   "color": "#00ff88", "score_bonus": +5},
    "consensus":   {"label": "CONSENSUS",    "color": "#ffb300", "score_bonus": 0},
    "crowded":     {"label": "CROWDED",      "color": "#ff8844", "score_bonus": -5},
    "abandoned":   {"label": "ABANDONED",    "color": "#ff4444", "score_bonus": +8},  # contrarian
}

# ─── SMART MONEY FACTOR WEIGHTS ───────────────────────────────────────────────
SM_FACTOR_WEIGHTS = {
    "vol_ratio":    0.25,
    "price_trend":  0.20,
    "range_comp":   0.15,
    "vol_trend":    0.15,
    "vs_20ma":      0.15,
    "delivery_pct": 0.10,   # 0 if delivery data unavailable
}

# ─── NSE NIFTY50 CONSTITUENTS (for real breadth) ──────────────────────────────
NIFTY50_STOCKS = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","BHARTIARTL.NS","ICICIBANK.NS",
    "INFOSYS.NS","SBIN.NS","HINDUNILVR.NS","ITC.NS","LT.NS",
    "KOTAKBANK.NS","AXISBANK.NS","BAJFINANCE.NS","ASIANPAINT.NS","MARUTI.NS",
    "SUNPHARMA.NS","TITAN.NS","NESTLEIND.NS","WIPRO.NS","HCLTECH.NS",
    "ULTRACEMCO.NS","POWERGRID.NS","NTPC.NS","TATAMOTORS.NS","ADANIPORTS.NS",
    "BAJAJFINSV.NS","ONGC.NS","M&M.NS","TECHM.NS","DRREDDY.NS",
]

# ─── UI COLOUR TOKENS ─────────────────────────────────────────────────────────
COLORS = {
    "bg_base":    "#030712",
    "bg_panel":   "#060f1e",
    "bg_raised":  "#0a1628",
    "border":     "#0f2440",
    "text_dim":   "#3a5a7f",
    "text_base":  "#b8d4ec",
    "text_full":  "#e2eef8",
    "green":      "#00ff88",
    "amber":      "#ffb300",
    "red":        "#ff4444",
    "blue":       "#4a9eff",
}

SM_SIGNAL_COLORS = {
    "ACCUMULATION":   "#00ff88",
    "COILING":        "#00cc55",
    "STEALTH ACCUM":  "#88ff44",
    "MOMENTUM":       "#4a9eff",
    "NEUTRAL":        "#4a6a8a",
    "WEAKNESS":       "#ff8844",
    "DISTRIBUTION":   "#ff4444",
    "NO DATA":        "#2a4a6f",
}

DECISION_COLORS = {
    "STRONG YES": {"color":"#00ff88","bg":"#001a0d","border":"#00ff88"},
    "YES":        {"color":"#00dd77","bg":"#001508","border":"#00dd77"},
    "CAUTION":    {"color":"#ffb300","bg":"#1a1200","border":"#ffb300"},
    "NO":         {"color":"#ff4444","bg":"#1a0000","border":"#ff4444"},
}

PHASE_COLORS = {
    "STRONG TREND":  "#00ff88",
    "EARLY TREND":   "#44dd88",
    "LATE TREND":    "#ffb300",
    "DISTRIBUTION":  "#ff4444",
    "CONSOLIDATION": "#4a9eff",
    "TRANSITION":    "#ffb300",
    "UNKNOWN":       "#4a9eff",
}
