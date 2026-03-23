"""
intelligence/contradiction_engine.py
======================================
Detects contradictions and reflexivity warnings across all signals.
This is the "anomaly detector" — the thing that stops you from making
a confident trade when the signals disagree.
"""

from __future__ import annotations
from typing import List, Optional
from core.models import Contradiction, ReflexivityReading, SectorData, MarketIntelligence


def detect_contradictions(
    trend_score:    float,
    breadth_score:  float,
    composite:      float,
    vix_level:      Optional[float],
    vix_slope:      Optional[float],
    sm_signal:      str,
    phase:          str,
    mom_score:      float,
    sm_score:       float,
    nifty_r20:      float,
) -> List[Contradiction]:
    """
    Detect signal contradictions. Each contradiction has a severity and explanation.
    These are surfaced prominently in the UI as warnings.
    """
    flags: List[Contradiction] = []

    # 1. Strong price trend but breadth not confirming
    if trend_score > 72 and breadth_score < 45:
        flags.append(Contradiction(
            severity="danger",
            msg="Strong Nifty trend but only a minority of stocks participating — narrow leadership is fragile",
            signals=["TREND", "BREADTH"],
        ))

    # 2. High composite score but VIX elevated and rising
    if composite > 72 and vix_level and vix_level > 22:
        flags.append(Contradiction(
            severity="warn",
            msg=f"Score looks bullish ({composite:.0f}) but India VIX at {vix_level:.1f} — volatility contradicts",
            signals=["COMPOSITE", "VIX"],
        ))

    # 3. Price up but smart money distributing
    if sm_signal == "DISTRIBUTION" and trend_score > 65:
        flags.append(Contradiction(
            severity="danger",
            msg="Price trend positive but volume signals show distribution — institutions may be selling into strength",
            signals=["TREND", "SMART_MONEY"],
        ))

    # 4. Late trend phase with euphoric momentum
    if phase == "LATE TREND" and mom_score > 75:
        flags.append(Contradiction(
            severity="warn",
            msg="Late trend phase with very strong momentum — this often signals exhaustion, not new strength",
            signals=["PHASE", "MOMENTUM"],
        ))

    # 5. Breadth improving but index weak
    if breadth_score > 72 and trend_score < 42:
        flags.append(Contradiction(
            severity="info",
            msg="Broad market participation improving while index is weak — money rotating away from large caps to mid/small",
            signals=["BREADTH", "TREND"],
        ))

    # 6. VIX rising sharply while market still bullish
    if vix_slope and vix_slope > 8 and composite > 65:
        flags.append(Contradiction(
            severity="warn",
            msg=f"VIX rising sharply ({vix_slope:+.1f}% in 5 days) while market appears bullish — hedge or reduce size",
            signals=["VIX_SLOPE", "COMPOSITE"],
        ))

    # 7. Smart money score and price momentum deeply diverging
    if sm_score < 35 and mom_score > 70:
        flags.append(Contradiction(
            severity="warn",
            msg="Strong price momentum but smart money proxy shows weakness — possible retail-driven move without institutional support",
            signals=["SMART_MONEY", "MOMENTUM"],
        ))

    # 8. Nifty significantly extended above 200MA (historical reversion risk)
    # Extreme readings have historically preceded corrections
    # (would need n200 as parameter — skipping for now, handled in scoring)

    return flags


def detect_reflexivity_warnings(readings: List[ReflexivityReading]) -> List[str]:
    """
    Generate human-readable warnings from reflexivity readings.
    Surfaces when price has significantly outrun fundamentals.
    """
    warnings = []
    for r in readings:
        if r.stage == "LOOP_TOP" and r.conviction in ("HIGH", "MEDIUM"):
            warnings.append(
                f"⚠ {r.sector}: Price momentum ({r.price_momentum:+.1f}%) is running "
                f"{r.gap:.0f}pts ahead of fundamentals — reflexivity loop may be near top"
            )
        elif r.stage == "NEGLECTED" and r.conviction == "HIGH":
            warnings.append(
                f"◎ {r.sector}: Fundamentals improving but price lagging "
                f"({r.price_momentum:+.1f}% vs fundamental score {r.fundamental_score:.0f}) — "
                f"potential Neglected→Discovered transition"
            )
    return warnings
