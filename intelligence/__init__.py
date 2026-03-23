from .master_engine import run_intelligence
from .ai_engine import call_groq, get_groq_key
from .scoring import (
    score_volatility, score_trend, score_momentum,
    score_breadth, score_macro, compute_conviction, detect_phase
)
from .sector_engine import (
    build_sector_data, rank_sectors,
    classify_lifecycle, compute_reflexivity,
    get_rate_cycle_stage, compute_commodity_spillover
)
from .opportunity_engine import screen_opportunities, score_stock
from .contradiction_engine import detect_contradictions, detect_reflexivity_warnings
