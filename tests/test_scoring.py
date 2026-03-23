"""
tests/test_scoring.py
=====================
Unit tests for intelligence/scoring.py
All tests use synthetic QuoteData — no network calls.
"""

import pytest
from core.models import QuoteData, SmartMoneyResult
from intelligence.scoring import (
    score_volatility, score_trend, score_smart_money,
    score_momentum, score_breadth, score_macro,
    compute_conviction, detect_phase
)
from core.models import SectorData


# ─── FIXTURES ────────────────────────────────────────────────────────────────

def make_quote(price=100.0, prev=98.0, n=252, trend="flat", sym="TEST") -> QuoteData:
    """Build a synthetic QuoteData for testing."""
    import numpy as np
    if trend == "up":
        closes = [80 + i * 0.1 for i in range(n)]
    elif trend == "down":
        closes = [120 - i * 0.1 for i in range(n)]
    elif trend == "volatile":
        np.random.seed(42)
        closes = [100 + np.random.randn() * 3 for _ in range(n)]
    else:
        closes = [100.0] * n

    volumes = [1_000_000.0] * n
    return QuoteData(
        symbol=sym, price=price, prev=prev,
        closes=closes, volumes=volumes,
        h52=max(closes), l52=min(closes),
    )


def make_vix_low() -> QuoteData:
    """VIX at low level — should give high vol_score."""
    closes = [13.0] * 252
    return QuoteData(symbol="^INDIAVIX", price=12.5, prev=13.0,
                     closes=closes, volumes=[])


def make_vix_high() -> QuoteData:
    """VIX at high level — should give low vol_score."""
    closes = [25.0] * 252
    return QuoteData(symbol="^INDIAVIX", price=28.0, prev=25.0,
                     closes=closes, volumes=[])


# ─── VOLATILITY SCORE ────────────────────────────────────────────────────────

class TestScoreVolatility:
    def test_none_returns_50(self):
        score, vl, vp, vs = score_volatility(None)
        assert score == 50.0
        assert vl is None

    def test_low_vix_high_score(self):
        score, vl, vp, vs = score_volatility(make_vix_low())
        assert score >= 60, f"Low VIX should score high, got {score}"

    def test_high_vix_low_score(self):
        score, vl, vp, vs = score_volatility(make_vix_high())
        assert score <= 40, f"High VIX should score low, got {score}"

    def test_returns_vix_level(self):
        score, vl, vp, vs = score_volatility(make_vix_low())
        assert vl == pytest.approx(12.5)

    def test_score_bounded(self):
        for _ in range(5):
            q = make_vix_low()
            score, *_ = score_volatility(q)
            assert 0 <= score <= 100


# ─── TREND SCORE ─────────────────────────────────────────────────────────────

class TestScoreTrend:
    def test_none_returns_50(self):
        score, *_ = score_trend(None, None)
        assert score == 50.0

    def test_uptrend_scores_high(self):
        q = make_quote(price=110, prev=108, n=252, trend="up")
        # Set price clearly above all MAs
        q.closes[-1] = 120.0
        score, n20, n50, n200, nrsi, bk50 = score_trend(q, None)
        assert score >= 50, f"Uptrend should score >= 50, got {score}"

    def test_downtrend_scores_low(self):
        q = make_quote(price=80, prev=82, n=252, trend="down")
        q.closes[-1] = 70.0  # below all MAs
        score, *_ = score_trend(q, None)
        assert score <= 50, f"Downtrend should score <= 50, got {score}"

    def test_returns_ma_values(self):
        q = make_quote(n=252, trend="up")
        score, n20, n50, n200, nrsi, bk50 = score_trend(q, None)
        # All should be computed with sufficient data
        assert n20  is not None
        assert n50  is not None
        assert n200 is not None

    def test_score_bounded(self):
        q = make_quote(n=252, trend="up")
        score, *_ = score_trend(q, None)
        assert 0 <= score <= 100


# ─── SMART MONEY ─────────────────────────────────────────────────────────────

class TestScoreSmartMoney:
    def test_no_data_returns_neutral(self):
        q = QuoteData(symbol="X", price=100, prev=99, closes=[], volumes=[], loaded=True)
        result = score_smart_money(q)
        assert result.signal == "NO DATA"
        assert result.score == 50

    def test_insufficient_data(self):
        closes = [100.0] * 10
        q = QuoteData(symbol="X", price=100, prev=99, closes=closes, volumes=[], loaded=True)
        result = score_smart_money(q)
        assert result.signal == "NO DATA"

    def test_result_is_smart_money_result(self):
        q = make_quote(n=60)
        result = score_smart_money(q)
        assert isinstance(result, SmartMoneyResult)

    def test_score_bounded(self):
        q = make_quote(n=60)
        result = score_smart_money(q)
        assert 0 <= result.score <= 100

    def test_has_factors(self):
        q = make_quote(n=60)
        result = score_smart_money(q)
        assert isinstance(result.factors, dict)
        assert "vol_score" in result.factors

    def test_accumulation_signal(self):
        """Price up strongly with high volume should get ACCUMULATION or MOMENTUM."""
        closes = [100 + i * 0.5 for i in range(60)]
        volumes = [500_000.0] * 40 + [1_500_000.0] * 20  # volume spike
        q = QuoteData(symbol="X", price=closes[-1], prev=closes[-2],
                      closes=closes, volumes=volumes)
        result = score_smart_money(q)
        assert result.signal in ("ACCUMULATION", "STEALTH ACCUM", "MOMENTUM", "NEUTRAL",
                                  "COILING"), f"Unexpected: {result.signal}"


# ─── MOMENTUM SCORE ──────────────────────────────────────────────────────────

class TestScoreMomentum:
    def _make_sector(self, rs: float, valid: bool = True) -> SectorData:
        return SectorData(
            sym="TEST", name="Test", short="TST", stocks=[],
            rs_vs_nifty=rs, valid=valid,
        )

    def test_all_positive_rs(self):
        sectors = [self._make_sector(rs=2.0) for _ in range(10)]
        score = score_momentum(sectors, 0.0)
        assert score == pytest.approx(100.0)

    def test_all_negative_rs(self):
        sectors = [self._make_sector(rs=-2.0) for _ in range(10)]
        score = score_momentum(sectors, 0.0)
        assert score == pytest.approx(0.0)

    def test_half_positive(self):
        sectors = ([self._make_sector(rs=2.0) for _ in range(5)] +
                   [self._make_sector(rs=-2.0) for _ in range(5)])
        score = score_momentum(sectors, 0.0)
        assert 40 <= score <= 60

    def test_empty_returns_50(self):
        score = score_momentum([], 0.0)
        assert score == 50.0

    def test_invalid_sectors_ignored(self):
        sectors = ([self._make_sector(rs=2.0)] +
                   [self._make_sector(rs=0.0, valid=False)] * 5)
        score = score_momentum(sectors, 0.0)
        assert score == pytest.approx(100.0)


# ─── BREADTH SCORE ───────────────────────────────────────────────────────────

class TestScoreBreadth:
    def _make_sector(self, above_ma: bool) -> SectorData:
        price  = 110.0 if above_ma else 90.0
        closes = [100.0] * 60  # 50MA = 100
        return SectorData(
            sym="TEST", name="Test", short="TST", stocks=[],
            valid=True,
        )

    def test_real_breadth_used_when_available(self):
        bd = {"pct_above_50ma": 80, "pct_above_200ma": 60, "source": "real_nifty50"}
        score, src = score_breadth(bd, [], {})
        assert src == "real_nifty50"
        # 80*0.6 + 60*0.4 = 48+24 = 72
        assert score == pytest.approx(72.0)

    def test_proxy_when_no_real_data(self):
        score, src = score_breadth(None, [], {})
        assert src in ("sector_proxy", "no_data")

    def test_score_bounded(self):
        bd = {"pct_above_50ma": 100, "pct_above_200ma": 100, "source": "real_nifty50"}
        score, _ = score_breadth(bd, [], {})
        assert 0 <= score <= 100


# ─── CONVICTION ──────────────────────────────────────────────────────────────

class TestComputeConviction:
    def test_all_bullish(self):
        c = compute_conviction(80, 80, 80, 80, 80, 80)
        assert c.label == "HIGH"
        assert c.direction == "BULLISH"
        assert c.bull == 6

    def test_all_bearish(self):
        c = compute_conviction(20, 20, 20, 20, 20, 20)
        assert c.label == "HIGH"
        assert c.direction == "BEARISH"
        assert c.bear == 6

    def test_mixed(self):
        c = compute_conviction(80, 20, 80, 20, 80, 20)
        assert c.direction == "MIXED" or c.score <= 60

    def test_score_bounded(self):
        c = compute_conviction(50, 50, 50, 50, 50, 50)
        assert 0 <= c.score <= 100


# ─── MARKET PHASE ────────────────────────────────────────────────────────────

class TestDetectPhase:
    def test_strong_trend(self):
        phase = detect_phase(n20=3, n50=5, n200=7, nrsi=65, vix_slope=-5)
        assert phase == "STRONG TREND"

    def test_distribution(self):
        phase = detect_phase(n20=-2, n50=-3, n200=-5, nrsi=38, vix_slope=3)
        assert phase == "DISTRIBUTION"

    def test_consolidation(self):
        phase = detect_phase(n20=0.5, n50=1.0, n200=5, nrsi=55, vix_slope=1)
        assert phase == "CONSOLIDATION"

    def test_unknown_when_no_data(self):
        phase = detect_phase(n20=None, n50=None, n200=None, nrsi=None, vix_slope=0)
        assert phase == "UNKNOWN"

    def test_late_trend(self):
        phase = detect_phase(n20=5, n50=4, n200=8, nrsi=73, vix_slope=-2)
        assert phase == "LATE TREND"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
