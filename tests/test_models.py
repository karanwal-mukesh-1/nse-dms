"""
tests/test_models.py
====================
Unit tests for core/models.py
Validates model construction, validation, and computed properties.
"""

import pytest
from datetime import datetime
from core.models import (
    QuoteData, SmartMoneyResult, SectorData, BulkDeal,
    InsiderActivity, ConvictionScore, MarketIntelligence,
    AIDecisionOutput, StockOpportunity
)


class TestQuoteData:
    def test_basic_construction(self):
        q = QuoteData(symbol="NSEI", price=22000.0, prev=21800.0,
                      closes=[21000, 21500, 22000], volumes=[])
        assert q.symbol == "NSEI"
        assert q.loaded is True

    def test_chg_pct_positive(self):
        q = QuoteData(symbol="X", price=110.0, prev=100.0,
                      closes=[100, 110], volumes=[])
        assert q.chg_pct == pytest.approx(10.0)

    def test_chg_pct_negative(self):
        q = QuoteData(symbol="X", price=90.0, prev=100.0,
                      closes=[100, 90], volumes=[])
        assert q.chg_pct == pytest.approx(-10.0)

    def test_chg_pct_zero_prev(self):
        q = QuoteData(symbol="X", price=100.0, prev=0.0,
                      closes=[100], volumes=[])
        assert q.chg_pct == 0.0

    def test_h52_l52_optional(self):
        q = QuoteData(symbol="X", price=100.0, prev=99.0,
                      closes=[100], volumes=[])
        assert q.h52 is None
        assert q.l52 is None


class TestSmartMoneyResult:
    def test_default_construction(self):
        sm = SmartMoneyResult(signal="NEUTRAL", score=50)
        assert sm.signal == "NEUTRAL"
        assert sm.score == 50
        assert sm.label_honest == "volume-proxy"

    def test_factors_dict(self):
        sm = SmartMoneyResult(signal="ACCUMULATION", score=80,
                               factors={"vol_score": 75, "trend_score": 80})
        assert sm.factors["vol_score"] == 75

    def test_score_is_float(self):
        sm = SmartMoneyResult(signal="NEUTRAL", score=50)
        assert isinstance(sm.score, float)


class TestSectorData:
    def test_basic_construction(self):
        s = SectorData(sym="^CNXIT", name="Nifty IT", short="IT",
                       stocks=["INFY.NS", "TCS.NS"])
        assert s.short == "IT"
        assert s.valid is False  # default

    def test_rs_vs_nifty_default_zero(self):
        s = SectorData(sym="X", name="Test", short="TST", stocks=[])
        assert s.rs_vs_nifty == 0.0

    def test_valid_flag(self):
        s = SectorData(sym="X", name="Test", short="TST", stocks=[], valid=True)
        assert s.valid is True


class TestBulkDeal:
    def test_construction(self):
        d = BulkDeal(
            date="2025-01-15", symbol="SBIN", name="SBI",
            client="LIC of India", deal_type="BUY",
            quantity=1000000, price=820.0, value_cr=82.0,
            signal_type="DII_BUY", conviction=2,
        )
        assert d.deal_type == "BUY"
        assert d.conviction == 2

    def test_defaults(self):
        d = BulkDeal(
            date="", symbol="X", name="X", client="Y",
            deal_type="BUY", quantity=0, price=0, value_cr=0,
        )
        assert d.signal_type == "NEUTRAL"
        assert d.conviction == 0
        assert d.sector is None


class TestInsiderActivity:
    def test_construction(self):
        a = InsiderActivity(
            date="2025-01-15", symbol="HDFC", name="HDFC Ltd",
            person="Deepak Parekh", designation="Chairman",
            transaction="BUY", quantity=10000,
            signal_type="PROMOTER_BUY",
        )
        assert a.signal_type == "PROMOTER_BUY"
        assert a.near_52w_low is False

    def test_optional_fields(self):
        a = InsiderActivity(
            date="", symbol="X", name="X", person="Y",
            designation="Director", transaction="BUY", quantity=0,
        )
        assert a.price is None
        assert a.value_cr is None


class TestConvictionScore:
    def test_construction(self):
        c = ConvictionScore(score=80, label="HIGH", bull=5, bear=1, direction="BULLISH")
        assert c.direction == "BULLISH"

    def test_low_conviction(self):
        c = ConvictionScore(score=30, label="LOW", bull=1, bear=2, direction="BEARISH")
        assert c.label == "LOW"


class TestMarketIntelligence:
    def _make_intel(self, **kwargs) -> MarketIntelligence:
        defaults = dict(
            composite=70, decision="YES",
            conviction=ConvictionScore(score=70, label="MODERATE",
                                        bull=4, bear=1, direction="BULLISH"),
            phase="EARLY TREND",
            vol_score=70, trend_score=72, mom_score=65,
            breadth_score=60, macro_score=58, sm_score=65,
            sector_data=[], ranked=[],
            sm_signal="NEUTRAL", sm_avg=55.0,
        )
        defaults.update(kwargs)
        return MarketIntelligence(**defaults)

    def test_construction(self):
        intel = self._make_intel()
        assert intel.decision == "YES"
        assert intel.composite == 70

    def test_defaults(self):
        intel = self._make_intel()
        assert intel.contradictions == []
        assert intel.reflexivity == []
        assert intel.opportunities == []
        assert isinstance(intel.as_of, datetime)

    def test_strong_yes(self):
        intel = self._make_intel(decision="STRONG YES", composite=85)
        assert intel.decision == "STRONG YES"

    def test_breadth_source_default(self):
        intel = self._make_intel()
        assert intel.breadth_source == "proxy"


class TestAIDecisionOutput:
    def test_defaults(self):
        ai = AIDecisionOutput()
        assert ai.confidence == "LOW"
        assert ai.anomaly_detected is False
        assert ai.regime_shift_risk is False

    def test_with_content(self):
        ai = AIDecisionOutput(
            narrative="Market in strong uptrend.",
            top_opportunity="ENERGY — ONGC above ₹285",
            confidence="HIGH",
            anomaly_detected=True,
            anomaly_description="FII distribution in IT despite price rise",
        )
        assert ai.confidence == "HIGH"
        assert ai.anomaly_detected is True


class TestStockOpportunity:
    def test_basic(self):
        from core.models import SmartMoneyResult
        opp = StockOpportunity(
            symbol="SBIN.NS", name="SBIN", sector="PSU",
            price=820.0, score=80,
            smart_money=SmartMoneyResult(signal="ACCUMULATION", score=78),
        )
        assert opp.score == 80
        assert opp.symbol == "SBIN.NS"

    def test_optional_fields(self):
        from core.models import SmartMoneyResult
        opp = StockOpportunity(
            symbol="X.NS", name="X", sector="TST",
            price=100.0, score=50,
            smart_money=SmartMoneyResult(signal="NEUTRAL", score=50),
        )
        assert opp.bulk_deal is None
        assert opp.setup_type == ""
        assert opp.confluence == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
