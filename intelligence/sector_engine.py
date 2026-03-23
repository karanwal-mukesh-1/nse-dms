"""
intelligence/sector_engine.py
==============================
Sector-level intelligence:
  - Relative strength ranking vs Nifty
  - Lifecycle classification (Neglected→Discovered→Consensus→Crowded→Abandoned)
  - Reflexivity meter (Soros: price vs fundamentals gap)
  - Rate cycle playbook mapping
  - Commodity spillover mapping
"""

from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np

from core.models import (
    QuoteData, SectorData, SectorLifecycle,
    ReflexivityReading, CommodityQuote, SmartMoneyResult
)
from core.math_utils import (
    sma, return_n, pct_change, pct_of_range, momentum_score, reflexivity_gap
)
from intelligence.scoring import score_smart_money
from config.settings import (
    SECTORS, LIFECYCLE_STAGES, RATE_CYCLE_PLAYBOOK
)


# ─── SECTOR DATA BUILDER ─────────────────────────────────────────────────────

def build_sector_data(quotes: Dict[str, QuoteData],
                       nifty_r20: float,
                       nifty_r5:  float) -> List[SectorData]:
    """
    Build SectorData for all sectors from raw quotes.
    Includes RS vs Nifty, smart money, 52W position.
    """
    result = []
    for s_def in SECTORS:
        sym = s_def["sym"]
        q   = quotes.get(sym)

        if not q or not q.loaded:
            result.append(SectorData(
                sym=sym, name=s_def["name"], short=s_def["short"],
                stocks=s_def.get("stocks", []),
                rate_sensitivity=s_def.get("rate_sensitivity", 0),
                commodity_proxy=s_def.get("commodity_proxy"),
                valid=False,
            ))
            continue

        chg    = pct_change(q.price, q.prev)
        r5     = return_n(q.closes, 5)
        r20    = return_n(q.closes, 20)
        r60    = return_n(q.closes, 60)

        # Relative strength vs Nifty — key upgrade
        rs_vs_nifty = r20 - nifty_r20
        rs_5d       = r5 - nifty_r5

        # Composite rotation strength: RS-based
        strength = rs_vs_nifty * 0.6 + rs_5d * 0.4

        sm    = score_smart_money(q)
        pos52 = pct_of_range(q.price, q.l52, q.h52)

        result.append(SectorData(
            sym=sym,
            name=s_def["name"],
            short=s_def["short"],
            stocks=s_def.get("stocks", []),
            chg=round(chg, 2),
            return5d=round(r5, 2),
            return20d=round(r20, 2),
            return60d=round(r60, 2),
            rs_vs_nifty=round(rs_vs_nifty, 2),
            strength=round(strength, 2),
            pos52=pos52,
            sm=sm,
            valid=True,
            rate_sensitivity=s_def.get("rate_sensitivity", 0),
            commodity_proxy=s_def.get("commodity_proxy"),
        ))

    return result


def rank_sectors(sector_list: List[SectorData]) -> List[SectorData]:
    """Sort by composite strength (RS-based). Strongest first."""
    valid = [s for s in sector_list if s.valid]
    return sorted(valid, key=lambda x: x.strength, reverse=True)


# ─── SECTOR LIFECYCLE CLASSIFIER ─────────────────────────────────────────────

def classify_lifecycle(sector: SectorData,
                        ranked_now: List[SectorData],
                        prev_ranked: Optional[List[SectorData]] = None) -> SectorLifecycle:
    """
    Classify sector into: neglected / discovered / consensus / crowded / abandoned
    Based on:
      - RS rank position (top/bottom)
      - RS 20d vs RS 60d trajectory
      - Rank change direction
    """
    evidence  = []
    rs20   = sector.rs_vs_nifty
    rs60   = sector.return60d - (ranked_now[0].return60d if ranked_now else 0)  # rough proxy
    rank   = next((i for i, s in enumerate(ranked_now) if s.short == sector.short), 5)
    n      = len(ranked_now) if ranked_now else 10

    # Rank movement
    prev_rank = None
    if prev_ranked:
        prev_rank = next((i for i, s in enumerate(prev_ranked) if s.short == sector.short), None)

    rank_improving = (prev_rank is not None and rank < prev_rank)
    rank_falling   = (prev_rank is not None and rank > prev_rank)

    # Classification logic
    if rank >= n - 2 and rs20 < -5:
        stage = "abandoned"
        evidence.append(f"Bottom {n - rank} of {n} sectors by RS")
        evidence.append(f"20D RS vs Nifty: {rs20:+.1f}%")
    elif rank >= n - 2 and rs20 > -2:
        stage = "neglected"
        evidence.append("Low rank but RS stabilising — potential bottoming")
        if rank_improving:
            evidence.append("Rank improving — early recovery signal")
    elif rank <= 2 and rs20 > 5 and rs60 > 8:
        stage = "crowded"
        evidence.append(f"Top {rank+1} of {n} sectors")
        evidence.append(f"RS 20D: {rs20:+.1f}% — price significantly ahead of peers")
        if rank_falling:
            evidence.append("⚠ Rank starting to fall — possible topping")
    elif rank <= 3 and rs20 > 2 and rank_improving:
        stage = "discovered"
        evidence.append(f"Rising rank ({rank+1} of {n}) with improving RS")
        evidence.append("Institutional interest building")
    elif rank <= 5 and rs20 > 0:
        stage = "consensus"
        evidence.append(f"Mid-table position ({rank+1} of {n})")
        evidence.append("Broad market awareness — edge diminishing")
    else:
        stage = "transition"
        evidence.append("Unclear lifecycle position")

    bonus = LIFECYCLE_STAGES.get(stage, {}).get("score_bonus", 0)
    return SectorLifecycle(
        sector=sector.short,
        stage=stage,
        evidence=evidence,
        rs_3yr=None,  # would need 3Y data
        score_bonus=bonus,
    )


# ─── REFLEXIVITY METER ───────────────────────────────────────────────────────

def compute_reflexivity(sector: SectorData,
                         quotes: Dict[str, QuoteData]) -> ReflexivityReading:
    """
    Soros reflexivity: gap between price momentum and fundamental proxy.

    Fundamental proxy (without paid data):
      - Earnings proxy: sector earnings growth estimated from price/volume trend
      - Revenue proxy: return consistency (low volatility in positive returns)

    This is a proxy, not actual earnings data. Labelled clearly.
    """
    q = quotes.get(sector.sym)
    if not q or not q.loaded:
        return ReflexivityReading(
            sector=sector.short,
            price_momentum=0,
            fundamental_score=50,
            gap=0,
            stage="UNKNOWN",
            conviction="LOW",
        )

    closes = q.closes

    # Price momentum: 60-day return
    price_momentum = sector.return60d

    # Fundamental proxy score:
    # 1. Consistency of positive returns (rolling 20-day Sharpe-like)
    daily_rets = [pct_change(closes[i], closes[i-1]) for i in range(-60, 0) if len(closes) >= 60]
    if daily_rets:
        mean_r = np.mean(daily_rets)
        std_r  = np.std(daily_rets)
        consistency = (mean_r / std_r * 100) if std_r > 0 else 0
        consistency = max(-100, min(100, consistency))
    else:
        consistency = 0

    # 2. Volume confirmation (is volume growing with price?)
    vols = q.volumes
    vol_confirmation = 0
    if len(vols) >= 20:
        vol_trend = return_n(vols, 20) if len(vols) >= 20 else 0
        vol_confirmation = 20 if vol_trend > 5 else -20 if vol_trend < -5 else 0

    fundamental_score = round(50 + consistency + vol_confirmation, 1)
    fundamental_score = max(0, min(100, fundamental_score))

    gap_data = reflexivity_gap(price_momentum, fundamental_score)
    gap      = gap_data["gap"]
    stage    = gap_data["stage"]

    conviction = "HIGH" if abs(gap) > 15 else "MEDIUM" if abs(gap) > 7 else "LOW"

    return ReflexivityReading(
        sector=sector.short,
        price_momentum=round(price_momentum, 1),
        fundamental_score=round(fundamental_score, 1),
        gap=round(gap, 1),
        stage=stage,
        conviction=conviction,
    )


# ─── RATE CYCLE POSITIONING ───────────────────────────────────────────────────

def get_rate_cycle_stage(vix_slope: Optional[float],
                          nifty_r20: float,
                          india_yield: Optional[float]) -> Dict:
    """
    Infer RBI rate cycle stage from available signals.
    Returns playbook for sector positioning.
    """
    # Simple heuristic: use yield trend as proxy for rate direction
    # In production: parse RBI MPC minutes or rate history
    if india_yield is None:
        return RATE_CYCLE_PLAYBOOK["neutral"]

    # India 10Y yield interpretation
    if india_yield > 7.5:
        stage = "hiking"
    elif india_yield < 6.8:
        stage = "cutting_aggressive"
    elif india_yield < 7.2:
        stage = "cutting_moderate"
    else:
        stage = "neutral"

    playbook = RATE_CYCLE_PLAYBOOK[stage].copy()
    playbook["current_stage"] = stage
    playbook["yield_level"]   = india_yield
    return playbook


# ─── COMMODITY SPILLOVER ─────────────────────────────────────────────────────

def compute_commodity_spillover(commodities: List[CommodityQuote],
                                  sectors: List[SectorData]) -> List[Dict]:
    """
    Maps commodity moves to affected NSE sectors.
    Returns list of spillover alerts.
    """
    alerts = []
    for comm in commodities:
        if abs(comm.chg_5d_pct) < 2:  # only flag significant moves
            continue

        direction = "positive" if comm.chg_5d_pct * comm.direction > 0 else "negative"
        affected  = [s for s in sectors if s.short in comm.nse_sectors]

        if not affected:
            continue

        alerts.append({
            "commodity":       comm.name,
            "chg_5d":          comm.chg_5d_pct,
            "direction":       direction,
            "affected_sectors":[s.short for s in affected],
            "message": (
                f"{comm.name} {'up' if comm.chg_5d_pct > 0 else 'down'} "
                f"{abs(comm.chg_5d_pct):.1f}% in 5 days — "
                f"{'positive' if direction=='positive' else 'negative'} for "
                f"{', '.join(s.short for s in affected)}"
            ),
            "urgency": "HIGH" if abs(comm.chg_5d_pct) > 5 else "MEDIUM",
        })

    return sorted(alerts, key=lambda x: abs(x["chg_5d"]), reverse=True)
