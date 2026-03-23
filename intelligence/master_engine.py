"""
intelligence/master_engine.py
==============================
Orchestrates all intelligence modules.
Single entry point: run_intelligence() → MarketIntelligence

This is the pipeline:
  Data Layer → Feature Engineering → Intelligence Modules → MarketIntelligence

Nothing in the UI calls individual modules directly.
Everything goes through this orchestrator.
"""

from __future__ import annotations
import streamlit as st
from typing import Dict, Optional

from core.models import MarketIntelligence, QuoteData
from core.math_utils import return_n

from intelligence.scoring import (
    score_volatility, score_trend, score_momentum,
    score_breadth, score_macro, compute_conviction, detect_phase
)
from intelligence.sector_engine import (
    build_sector_data, rank_sectors,
    classify_lifecycle, compute_reflexivity,
    get_rate_cycle_stage, compute_commodity_spillover
)
from intelligence.contradiction_engine import (
    detect_contradictions, detect_reflexivity_warnings
)
from intelligence.opportunity_engine import screen_opportunities
from intelligence.ai_engine import call_groq, get_groq_key

from data.market_data import (
    fetch_market_data, fetch_nifty50_breadth,
    fetch_commodities, fetch_india_10y_yield,
)
from data.nse_data import (
    fetch_bulk_deals, fetch_block_deals,
    fetch_insider_activity, detect_insider_clusters,
)

from config.settings import INDEX_SYMBOLS, SCORE_WEIGHTS, DECISION_THRESHOLDS, CONVICTION_THRESHOLD_FOR_STRONG
from utils.logger import get_logger, fetch_log

_log = get_logger(__name__)


@st.cache_data(ttl=300, show_spinner=False)
def _compute_intelligence_cached() -> MarketIntelligence:
    """
    Core intelligence pipeline — cached 5 minutes.
    Does NOT call Groq (stateful, not cacheable).
    Called internally by run_intelligence().
    """
    # ── LAYER 1: Fetch all market data ───────────────────────────────────────
    quotes        = fetch_market_data()
    breadth_raw   = fetch_nifty50_breadth()
    commodities   = fetch_commodities()
    india_yield   = fetch_india_10y_yield()
    bulk_deals    = fetch_bulk_deals()
    block_deals   = fetch_block_deals()
    insider_acts  = fetch_insider_activity()
    all_deals     = bulk_deals + block_deals

    nifty = quotes.get(INDEX_SYMBOLS["nifty50"])
    bank  = quotes.get(INDEX_SYMBOLS["banknifty"])
    vix   = quotes.get(INDEX_SYMBOLS["india_vix"])
    dxy   = quotes.get(INDEX_SYMBOLS["dxy"])

    # ── LAYER 2: Core index scores ────────────────────────────────────────────
    vol_score, vix_level, vix_pct, vix_slope = score_volatility(vix)
    trend_score, n20, n50, n200, nrsi, bk50  = score_trend(nifty, bank)
    macro_score, dxy_slope                   = score_macro(dxy)

    phase     = detect_phase(n20, n50, n200, nrsi, vix_slope or 0)
    nifty_r20 = return_n(nifty.closes, 20) if nifty and nifty.loaded else 0.0
    nifty_r5  = return_n(nifty.closes, 5)  if nifty and nifty.loaded else 0.0

    # ── LAYER 3: Sector intelligence ─────────────────────────────────────────
    sector_data = build_sector_data(quotes, nifty_r20, nifty_r5)
    ranked      = rank_sectors(sector_data)

    mom_score                   = score_momentum(sector_data, nifty_r20)
    breadth_score, breadth_src  = score_breadth(breadth_raw, sector_data, quotes)

    # Smart money aggregate
    valid_sm     = [s for s in sector_data if s.valid]
    sm_scores    = [s.sm.score for s in valid_sm]
    sm_avg       = float(sum(sm_scores) / len(sm_scores)) if sm_scores else 50.0
    sm_signal    = ("ACCUMULATION" if sm_avg >= 65
                    else "DISTRIBUTION" if sm_avg <= 38
                    else "NEUTRAL")
    sm_score_agg = round(sm_avg)

    # ── LAYER 4: Advanced intelligence ───────────────────────────────────────
    # Lifecycle per sector
    lifecycles = [
        classify_lifecycle(s, ranked)
        for s in sector_data if s.valid
    ]
    lifecycle_bonus = sum(lc.score_bonus for lc in lifecycles) / max(len(lifecycles), 1)

    # Reflexivity per sector
    reflexivity = [
        compute_reflexivity(s, quotes)
        for s in ranked[:5]   # top 5 only to save compute
    ]

    # Commodity spillover alerts
    comm_alerts = compute_commodity_spillover(commodities, sector_data)

    # Rate cycle playbook
    rate_playbook = get_rate_cycle_stage(vix_slope, nifty_r20, india_yield)

    # ── LAYER 5: Composite score ──────────────────────────────────────────────
    composite = round(
        vol_score    * SCORE_WEIGHTS["volatility"]   +
        trend_score  * SCORE_WEIGHTS["trend"]        +
        mom_score    * SCORE_WEIGHTS["momentum"]     +
        breadth_score* SCORE_WEIGHTS["breadth"]      +
        macro_score  * SCORE_WEIGHTS["macro"]        +
        sm_score_agg * SCORE_WEIGHTS["smart_money"]  +
        min(10, lifecycle_bonus) * SCORE_WEIGHTS["lifecycle"]
    )
    composite = round(min(100, max(0, composite)))

    conviction = compute_conviction(
        trend_score, breadth_score, mom_score,
        vol_score, macro_score, sm_score_agg
    )

    # ── LAYER 6: Decision ─────────────────────────────────────────────────────
    if composite >= DECISION_THRESHOLDS["strong_yes"] and conviction.score >= CONVICTION_THRESHOLD_FOR_STRONG:
        decision = "STRONG YES"
    elif composite >= DECISION_THRESHOLDS["yes"]:
        decision = "YES"
    elif composite >= DECISION_THRESHOLDS["caution"]:
        decision = "CAUTION"
    else:
        decision = "NO"

    # ── LAYER 7: Contradictions ───────────────────────────────────────────────
    contradictions = detect_contradictions(
        trend_score, breadth_score, composite,
        vix_level, vix_slope, sm_signal, phase,
        mom_score, sm_score_agg, nifty_r20,
    )
    reflexivity_warnings = detect_reflexivity_warnings(reflexivity)

    # ── LAYER 8: Stock opportunities (only when market is active) ─────────────
    opportunities = []
    if decision in ("STRONG YES", "YES", "CAUTION") and ranked:
        opportunities = screen_opportunities(
            top_sectors=ranked[:3],
            quotes=quotes,
            bulk_deals=all_deals,
            insider_acts=insider_acts,
        )

    # ── LAYER 9: Insider clusters ─────────────────────────────────────────────
    clusters = detect_insider_clusters(insider_acts)

    # ── ASSEMBLE ──────────────────────────────────────────────────────────────
    intel = MarketIntelligence(
        composite=composite,
        decision=decision,
        conviction=conviction,
        phase=phase,

        vol_score=round(vol_score, 1),
        trend_score=round(trend_score, 1),
        mom_score=round(mom_score, 1),
        breadth_score=round(breadth_score, 1),
        macro_score=round(macro_score, 1),
        sm_score=round(sm_score_agg, 1),
        lifecycle_bonus=round(lifecycle_bonus, 1),
        breadth_source=breadth_src,

        vix_level=vix_level,
        vix_pct=vix_pct,
        vix_slope=vix_slope,
        n20=n20, n50=n50, n200=n200, nrsi=nrsi, bk50=bk50,
        nifty_r20=round(nifty_r20, 2),
        dxy_slope=dxy_slope,

        sector_data=sector_data,
        ranked=ranked,
        sm_signal=sm_signal,
        sm_avg=round(sm_avg, 1),

        contradictions=contradictions,
        reflexivity=reflexivity,
        lifecycles=lifecycles,
        commodities=commodities,
        bulk_deals=all_deals,
        insider_activity=insider_acts,

        opportunities=opportunities,

        nifty_price=nifty.price if nifty and nifty.loaded else None,
        bank_price= bank.price  if bank  and bank.loaded  else None,
        vix_price=  vix.price   if vix   and vix.loaded   else None,
        valid_count=len(valid_sm),
    )

    _log.info(f"Intelligence computed: {intel.decision} score={intel.composite} phase={intel.phase}")
    return intel


def run_intelligence() -> MarketIntelligence:
    """
    Public entry point for all pages.
    Wraps the cached computation and handles Groq (stateful, not cached).
    """
    intel = _compute_intelligence_cached()

    # Attach Groq AI output (outside cache — stateful)
    groq_key = get_groq_key()
    if groq_key and "groq_analysis" not in st.session_state:
        try:
            ai_out = call_groq(groq_key, intel)
            st.session_state["groq_analysis"] = ai_out
            intel.ai_output = ai_out.model_dump()
            _log.info("Groq analysis completed")
        except Exception as e:
            _log.warning(f"Groq call failed: {e}")

    if "groq_analysis" in st.session_state:
        cached = st.session_state["groq_analysis"]
        intel.ai_output = cached.model_dump() if hasattr(cached, "model_dump") else cached

    return intel
