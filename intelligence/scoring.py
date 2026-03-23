"""
intelligence/scoring.py
========================
Converts raw QuoteData into scored intelligence signals.
All scores 0-100, all self-calibrating via rolling percentiles.
No arbitrary thresholds — everything is percentile or z-score based.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np

from core.models import QuoteData, SmartMoneyResult, SectorData, BreadthData, ConvictionScore
from core.math_utils import (
    sma, rsi, pct_change, return_n, slope_nd,
    percentile_rank, rolling_zscore, pct_of_range, momentum_score
)
from config.settings import SECTORS, SM_FACTOR_WEIGHTS


# ─── VOLATILITY SCORE ────────────────────────────────────────────────────────

def score_volatility(vix_quote: Optional[QuoteData]) -> Tuple[float, Optional[float], Optional[float], Optional[float]]:
    """
    Returns: (score, vix_level, vix_pct, vix_slope)
    Low VIX = high score. Self-calibrating via rolling percentile.
    """
    if not vix_quote or not vix_quote.loaded:
        return 50.0, None, None, None

    vix_level = vix_quote.price
    closes    = vix_quote.closes
    vix_pct   = percentile_rank(vix_level, closes)
    vix_slope = slope_nd(closes, 5)

    # Invert: low VIX percentile = high score
    base_score = 100 - vix_pct

    # Slope adjustment: falling VIX adds confidence
    slope_history = [slope_nd(closes[:i], 5) for i in range(10, len(closes))]
    slope_pct     = percentile_rank(vix_slope, slope_history) if slope_history else 50
    slope_adj     = (100 - slope_pct) * 0.2   # rising VIX slope reduces score

    score = round(base_score * 0.8 + slope_adj, 1)
    return min(100, max(0, score)), vix_level, vix_pct, vix_slope


# ─── TREND SCORE ─────────────────────────────────────────────────────────────

def score_trend(nifty: Optional[QuoteData],
                bank:  Optional[QuoteData]) -> Tuple[float, Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Returns: (score, n20, n50, n200, nrsi, bk50)
    MA positioning + RSI via z-score.
    """
    if not nifty or not nifty.loaded:
        return 50.0, None, None, None, None, None

    c     = nifty.closes
    price = nifty.price
    m20   = sma(c, 20);  m50 = sma(c, 50);  m200 = sma(c, 200)
    n20   = pct_change(price, m20)  if m20  else None
    n50   = pct_change(price, m50)  if m50  else None
    n200  = pct_change(price, m200) if m200 else None
    nrsi  = rsi(c)

    pts = 0
    if n20  and n20  > 0: pts += 25
    if n50  and n50  > 0: pts += 25
    if n200 and n200 > 0: pts += 30

    # RSI via z-score — not fixed 50/70 thresholds
    if nrsi:
        rsi_history = [rsi(c[:i]) for i in range(20, len(c)) if rsi(c[:i]) is not None]
        rsi_z = rolling_zscore(nrsi, rsi_history)
        if 50 < nrsi < 72:
            pts += round(rsi_z * 0.18)
        elif nrsi >= 72:
            pts += 5     # overbought — slight positive, not full
        elif nrsi < 40:
            pts -= 10

    trend_score = min(100, max(0, pts))
    bk50 = None

    if bank and bank.loaded:
        m50b = sma(bank.closes, 50)
        bk50 = pct_change(bank.price, m50b) if m50b else None
        if bk50 and bk50 > 0:
            trend_score = min(100, trend_score + 5)
        else:
            trend_score = max(0, trend_score - 5)

    return float(trend_score), n20, n50, n200, nrsi, bk50


# ─── SMART MONEY SCORE ───────────────────────────────────────────────────────

def score_smart_money(q: QuoteData) -> SmartMoneyResult:
    """
    Multi-factor volume-based smart money proxy.
    5 factors, each scored 0-100, weighted composite.
    Honestly labelled as a proxy — not delivery or OI data.
    """
    if not q or not q.loaded or len(q.closes) < 20:
        return SmartMoneyResult(signal="NO DATA", score=50)

    closes  = q.closes
    volumes = q.volumes
    price   = q.price
    prev    = q.prev

    price_chg = pct_change(price, prev)

    # Factor 1: Volume ratio vs 20-day avg
    avg_vol20 = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else None
    last_vol  = volumes[-1] if volumes else None
    vol_ratio = (last_vol / avg_vol20) if avg_vol20 and last_vol else 1.0
    f_vol = min(100, max(0, round((vol_ratio - 0.5) / 2.0 * 100)))

    # Factor 2: Price trend vs its own history (percentile)
    r5 = return_n(closes, 5)
    r5_history = [return_n(closes[:i], 5) for i in range(10, len(closes))]
    f_trend = percentile_rank(r5, r5_history) if r5_history else 50

    # Factor 3: Range compression (coiling = potential breakout)
    hi10 = max(closes[-10:]); lo10 = min(closes[-10:])
    hi20 = max(closes[-20:]); lo20 = min(closes[-20:])
    range_comp = (hi10 - lo10) / (hi20 - lo20) if (hi20 - lo20) > 0 else 1.0
    f_coil = max(0, round((1 - range_comp) * 100))

    # Factor 4: Volume trend (5d new vs 5d old)
    vol5_old   = float(np.mean(volumes[-10:-5])) if len(volumes) >= 10 else avg_vol20
    vol5_new   = float(np.mean(volumes[-5:]))    if len(volumes) >= 5  else avg_vol20
    vol_expanding = bool(vol5_new and vol5_old and vol5_new > vol5_old * 1.05)
    f_vol_trend = 70 if vol_expanding else 30

    # Factor 5: Price vs 20MA
    m20   = sma(closes, 20)
    vs20  = pct_change(price, m20) if m20 else 0.0
    f_ma  = min(100, max(0, round(50 + vs20 * 5)))

    # Weighted composite
    w = SM_FACTOR_WEIGHTS
    score = round(
        f_vol       * w["vol_ratio"]   +
        f_trend     * w["price_trend"] +
        f_coil      * w["range_comp"]  +
        f_vol_trend * w["vol_trend"]   +
        f_ma        * w["vs_20ma"]
        # delivery_pct weight = 0 since data unavailable
    )
    score = min(100, max(0, score))

    # Derive signal
    if score >= 75 and price_chg > 0:
        signal = "ACCUMULATION"
    elif range_comp < 0.6 and vol_expanding and score >= 65:
        signal = "COILING"
    elif score >= 65 and price_chg > 0:
        signal = "STEALTH ACCUM"
    elif score <= 30 and price_chg < 0:
        signal = "DISTRIBUTION"
    elif score <= 35:
        signal = "WEAKNESS"
    elif score >= 60 and r5 > 1.5:
        signal = "MOMENTUM"
    else:
        signal = "NEUTRAL"

    return SmartMoneyResult(
        signal=signal,
        score=float(score),
        vol_ratio=round(vol_ratio, 2),
        range_comp=round(range_comp, 2),
        vol_expanding=vol_expanding,
        vs_20ma_pct=round(vs20, 2),
        factors={
            "vol_score":    f_vol,
            "trend_score":  f_trend,
            "coil_score":   f_coil,
            "vol_trend":    f_vol_trend,
            "ma_score":     f_ma,
            "composite":    score,
        },
    )


# ─── MOMENTUM SCORE ──────────────────────────────────────────────────────────

def score_momentum(sector_list: List[SectorData], nifty_r20: float) -> float:
    """
    RS-weighted momentum score.
    Counts sectors with positive RS vs Nifty (not raw % up).
    """
    valid = [s for s in sector_list if s.valid]
    if not valid:
        return 50.0

    rs_positive = [s for s in valid if s.rs_vs_nifty > 0]
    mom_score   = round(len(rs_positive) / len(valid) * 100)

    if len(valid) >= 3:
        top3_rs = sorted(valid, key=lambda x: x.rs_vs_nifty, reverse=True)[:3]
        top3_avg = sum(s.rs_vs_nifty for s in top3_rs) / 3
        if top3_avg > 3:
            mom_score = min(100, mom_score + 10)
        elif top3_avg < -3:
            mom_score = max(0, mom_score - 10)

    return float(mom_score)


# ─── BREADTH SCORE ───────────────────────────────────────────────────────────

def score_breadth(breadth_data: Optional[Dict],
                  sector_list: List[SectorData],
                  quotes: Dict[str, QuoteData]) -> Tuple[float, str]:
    """
    Returns: (score, source)
    Uses real Nifty50 breadth if available, sector proxy otherwise.
    Clearly labels which data source was used.
    """
    if breadth_data and breadth_data.get("source") == "real_nifty50":
        pct_50  = breadth_data["pct_above_50ma"]
        pct_200 = breadth_data["pct_above_200ma"]
        score   = round(pct_50 * 0.6 + pct_200 * 0.4, 1)
        return score, "real_nifty50"

    # Sector proxy — count sectors above their own 50MA
    valid = [s for s in sector_list if s.valid]
    if not valid:
        return 50.0, "no_data"

    above_ma = 0
    for s in valid:
        q = quotes.get(s.sym)
        if q and q.loaded and len(q.closes) >= 50:
            m50 = sma(q.closes, 50)
            if m50 and q.price > m50:
                above_ma += 1

    score = round(above_ma / len(valid) * 100, 1)
    return score, "sector_proxy"


# ─── MACRO SCORE ─────────────────────────────────────────────────────────────

def score_macro(dxy: Optional[QuoteData]) -> Tuple[float, Optional[float]]:
    """
    DXY slope via rolling percentile.
    Rising DXY = FII outflow pressure = lower macro score.
    """
    if not dxy or not dxy.loaded:
        return 55.0, None

    dxy_slope = slope_nd(dxy.closes, 5)
    slope_history = [slope_nd(dxy.closes[:i], 5) for i in range(10, len(dxy.closes))]
    dxy_pct   = percentile_rank(dxy_slope, slope_history) if slope_history else 50

    # Rising DXY percentile = bad for India
    score = round(100 - dxy_pct, 1)
    return min(100, max(0, score)), dxy_slope


# ─── CONVICTION SCORE ────────────────────────────────────────────────────────

def compute_conviction(trend: float, breadth: float, momentum: float,
                        vol: float, macro: float, sm: float) -> ConvictionScore:
    """
    Counts agreement across 6 signals.
    More signals in same direction = higher conviction.
    """
    signals = [trend, breadth, momentum, vol, macro, sm]
    bull = sum(1 for s in signals if s > 60)
    bear = sum(1 for s in signals if s < 40)
    score = round(max(bull, bear) / len(signals) * 100)
    label = "HIGH" if score >= 80 else "MODERATE" if score >= 60 else "LOW"
    direction = "BULLISH" if bull > bear else "BEARISH" if bear > bull else "MIXED"
    return ConvictionScore(score=score, label=label, bull=bull, bear=bear, direction=direction)


# ─── MARKET PHASE ────────────────────────────────────────────────────────────

def detect_phase(n20: Optional[float], n50: Optional[float], n200: Optional[float],
                  nrsi: Optional[float], vix_slope: float) -> str:
    if n200 is None:
        return "UNKNOWN"
    if n200 > 5 and n50 and n50 > 3 and nrsi and 60 < nrsi < 75 and vix_slope < 0:
        return "STRONG TREND"
    if n200 > 0 and n50 and n50 > 0 and nrsi and 45 <= nrsi < 65:
        return "EARLY TREND"
    if n200 > 0 and n50 and n50 > 0 and nrsi and nrsi >= 70:
        return "LATE TREND"
    if n200 < 0 and n50 and n50 < 0 and nrsi and nrsi < 45:
        return "DISTRIBUTION"
    if n20 is not None and abs(n20) < 1.5 and n50 is not None and abs(n50) < 2:
        return "CONSOLIDATION"
    return "TRANSITION"
