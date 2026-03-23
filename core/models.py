"""
core/models.py
==============
All data structures as Pydantic models.
Every module communicates through these — no raw dicts.
This is what makes the system auditable and type-safe.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ─── RAW MARKET DATA ──────────────────────────────────────────────────────────

class QuoteData(BaseModel):
    symbol:  str
    price:   float
    prev:    float
    closes:  List[float]
    volumes: List[float] = Field(default_factory=list)
    h52:     Optional[float] = None
    l52:     Optional[float] = None
    loaded:  bool = True

    @property
    def chg_pct(self) -> float:
        if not self.prev:
            return 0.0
        return ((self.price - self.prev) / self.prev) * 100


class CommodityQuote(BaseModel):
    symbol:     str
    name:       str
    price:      float
    chg_pct:    float
    chg_5d_pct: float
    loaded:     bool = True
    nse_sectors: List[str] = Field(default_factory=list)
    direction:  int = 0   # +1 = rising helps these sectors, -1 = hurts


# ─── FEATURE OUTPUTS ──────────────────────────────────────────────────────────

class SmartMoneyResult(BaseModel):
    signal:    str
    score:     float          # 0-100
    factors:   Dict[str, Any] = Field(default_factory=dict)
    # Individual factor scores for transparency
    vol_ratio:       float = 1.0
    range_comp:      float = 1.0
    vol_expanding:   bool  = False
    vs_20ma_pct:     float = 0.0
    delivery_pct:    Optional[float] = None  # None = not available
    label_honest:    str = "volume-proxy"  # always remind caller this is proxy


class SectorData(BaseModel):
    sym:         str
    name:        str
    short:       str
    stocks:      List[str]
    chg:         float = 0.0
    return5d:    float = 0.0
    return20d:   float = 0.0
    return60d:   float = 0.0
    rs_vs_nifty: float = 0.0   # relative strength vs Nifty 20D
    strength:    float = 0.0   # composite rotation strength
    pos52:       Optional[float] = None
    sm:          SmartMoneyResult = Field(default_factory=lambda: SmartMoneyResult(signal="NO DATA", score=50))
    valid:       bool  = False
    lifecycle:   str   = "unknown"
    rate_sensitivity: int = 0
    commodity_proxy:  Optional[str] = None


class BreadthData(BaseModel):
    pct_above_50ma:  float
    pct_above_200ma: float
    total_stocks:    int
    source:          str   # "real_nifty50" | "sector_proxy"
    timestamp:       datetime = Field(default_factory=datetime.now)


class BulkDeal(BaseModel):
    date:        str
    symbol:      str
    name:        str
    client:      str
    deal_type:   str   # "BUY" | "SELL"
    quantity:    float
    price:       float
    value_cr:    float
    sector:      Optional[str] = None
    # Signal classification
    signal_type: str   = "NEUTRAL"  # "INSTITUTIONAL_BUY"|"FII_BUY"|"PROMOTER_SELL"|etc
    conviction:  int   = 0          # 0-3


class InsiderActivity(BaseModel):
    date:          str
    symbol:        str
    name:          str
    person:        str
    designation:   str
    transaction:   str     # "Buy" | "Sell" | "Pledge" | "Revoke"
    quantity:      float
    price:         Optional[float] = None
    value_cr:      Optional[float] = None
    # Derived signal
    signal_type:   str = "NEUTRAL"   # "CLUSTER_BUY"|"REVOKE"|"INVOKE"|"PROMOTER_BUY"
    near_52w_low:  bool = False


class MacroIndicator(BaseModel):
    name:      str
    value:     float
    prev:      Optional[float] = None
    unit:      str = ""
    trend:     str = "FLAT"    # "RISING"|"FALLING"|"FLAT"
    signal:    str = "NEUTRAL"
    source:    str = ""
    as_of:     str = ""


# ─── INTELLIGENCE OUTPUTS ─────────────────────────────────────────────────────

class ConvictionScore(BaseModel):
    score:     float     # 0-100
    label:     str       # HIGH | MODERATE | LOW
    bull:      int       # count of bullish signals
    bear:      int       # count of bearish signals
    direction: str       # BULLISH | BEARISH | MIXED


class Contradiction(BaseModel):
    severity:  str       # "danger" | "warn" | "info"
    msg:       str
    signals:   List[str] = Field(default_factory=list)  # which signals conflict


class ReflexivityReading(BaseModel):
    """
    Soros reflexivity meter per sector.
    Measures gap between price momentum and fundamental improvement rate.
    """
    sector:            str
    price_momentum:    float   # 60D price return
    fundamental_score: float   # earnings + revenue trend proxy
    gap:               float   # price_momentum - fundamental_score
    stage:             str     # "EARLY_LOOP"|"MATURING_LOOP"|"LOOP_TOP"|"BUST_RISK"
    conviction:        str     # HIGH | MEDIUM | LOW


class SectorLifecycle(BaseModel):
    sector:    str
    stage:     str     # neglected|discovered|consensus|crowded|abandoned
    evidence:  List[str] = Field(default_factory=list)
    rs_3yr:    Optional[float] = None
    mf_alloc_trend: str = "UNKNOWN"  # INCREASING|DECREASING|STABLE
    score_bonus: int = 0


class StockOpportunity(BaseModel):
    """A specific stock with a full scorecard and trade setup."""
    symbol:      str
    name:        str
    sector:      str
    price:       float
    score:       int          # 0-100 composite

    # Technical factors
    chg_1d:      float = 0.0
    return_5d:   float = 0.0
    return_20d:  float = 0.0
    vs_20ma:     Optional[float] = None
    vs_50ma:     Optional[float] = None
    vs_200ma:    Optional[float] = None
    rsi:         Optional[float] = None
    vol_ratio:   Optional[float] = None
    pos_52w:     Optional[float] = None
    rs_vs_sector: float = 0.0

    # Fundamental factors
    smart_money: SmartMoneyResult = Field(default_factory=lambda: SmartMoneyResult(signal="NEUTRAL", score=50))
    bulk_deal:   Optional[BulkDeal]     = None
    insider:     Optional[InsiderActivity] = None

    # Trade setup (generated by AI or rule engine)
    setup_type:  str   = ""    # "BREAKOUT_WATCH"|"PULLBACK_BUY"|"MOMENTUM"|"REVERSAL"
    watch_level: Optional[float] = None   # price level to watch
    stop_level:  Optional[float] = None
    confluence:  int   = 0    # 0-5 factors aligned
    thesis:      str   = ""   # one-sentence explanation


class MarketIntelligence(BaseModel):
    """
    The complete output of the intelligence engine.
    This is what every UI component consumes.
    Everything flows from this one object.
    """
    # Core decision
    composite:    float
    decision:     str           # STRONG YES | YES | CAUTION | NO
    conviction:   ConvictionScore
    phase:        str

    # Component scores (0-100 each)
    vol_score:      float
    trend_score:    float
    mom_score:      float
    breadth_score:  float
    macro_score:    float
    sm_score:       float
    lifecycle_bonus: float = 0.0

    # Transparency
    breadth_source:  str = "proxy"
    score_version:   str = "v2"

    # Raw readings
    vix_level:    Optional[float] = None
    vix_pct:      Optional[float] = None
    vix_slope:    Optional[float] = None
    n20:          Optional[float] = None
    n50:          Optional[float] = None
    n200:         Optional[float] = None
    nrsi:         Optional[float] = None
    bk50:         Optional[float] = None
    nifty_r20:    float = 0.0
    dxy_slope:    Optional[float] = None

    # Sector intelligence
    sector_data:  List[SectorData]
    ranked:       List[SectorData]
    sm_signal:    str
    sm_avg:       float

    # Advanced intelligence
    contradictions: List[Contradiction] = Field(default_factory=list)
    reflexivity:    List[ReflexivityReading] = Field(default_factory=list)
    lifecycles:     List[SectorLifecycle] = Field(default_factory=list)
    commodities:    List[CommodityQuote] = Field(default_factory=list)
    bulk_deals:     List[BulkDeal] = Field(default_factory=list)
    insider_activity: List[InsiderActivity] = Field(default_factory=list)
    macro_indicators: List[MacroIndicator] = Field(default_factory=list)

    # Opportunities (top stocks)
    opportunities: List[StockOpportunity] = Field(default_factory=list)

    # Index prices for sidebar
    nifty_price:  Optional[float] = None
    bank_price:   Optional[float] = None
    vix_price:    Optional[float] = None
    valid_count:  int = 0

    # Groq AI structured output
    ai_output:    Optional[Dict[str, Any]] = None

    # Timestamp
    as_of:        datetime = Field(default_factory=datetime.now)


# ─── AI OUTPUT STRUCTURE ──────────────────────────────────────────────────────

class AIDecisionOutput(BaseModel):
    """Structured output from Groq — fields drive UI directly."""
    narrative:          str = ""
    q1_environment:     str = ""
    q2_flow:            str = ""
    q3_risks:           str = ""
    q4_observe:         str = ""
    top_opportunity:    str = ""   # "ENERGY — ONGC above ₹285 with vol expansion"
    stop_condition:     str = ""   # what invalidates the thesis
    watch_condition:    str = ""   # what to monitor next session
    anomaly_detected:   bool = False
    anomaly_description:str = ""
    lifecycle_alert:    str = ""   # "PSU Banks transitioning Consensus→Crowded"
    reflexivity_warning:str = ""   # "IT sector: price 2.8x fundamental improvement rate"
    confidence:         str = "LOW"
    regime_shift_risk:  bool = False
