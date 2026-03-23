"""
tests/test_opportunity_engine.py
==================================
Unit tests for intelligence/opportunity_engine.py
"""

import pytest
from core.models import QuoteData, SectorData, BulkDeal, InsiderActivity, SmartMoneyResult
from intelligence.opportunity_engine import score_stock


def make_quote_for_stock(sym="SBIN.NS", trend="up", n=120) -> QuoteData:
    if trend == "up":
        closes = [80 + i * 0.3 for i in range(n)]
    elif trend == "down":
        closes = [120 - i * 0.3 for i in range(n)]
    else:
        closes = [100.0] * n
    volumes = [1_000_000.0] * n
    price   = closes[-1]
    return QuoteData(
        symbol=sym, price=price, prev=closes[-2],
        closes=closes, volumes=volumes,
        h52=max(closes), l52=min(closes),
    )


def make_sector(short="PSU", r20=5.0) -> SectorData:
    return SectorData(
        sym="^CNXPSUbank", name="Nifty PSU Bank", short=short,
        stocks=["SBIN.NS", "PNB.NS"],
        return20d=r20, rs_vs_nifty=r20 - 2, valid=True,
    )


def make_bulk_deal(symbol="SBIN", deal_type="BUY") -> BulkDeal:
    return BulkDeal(
        date="2025-01-15", symbol=symbol, name=symbol,
        client="LIC of India", deal_type=deal_type,
        quantity=5000000, price=820.0, value_cr=410.0,
        signal_type="DII_BUY", conviction=3,
    )


class TestScoreStock:
    def test_returns_opportunity(self):
        from core.models import StockOpportunity
        q   = make_quote_for_stock(trend="up")
        sec = make_sector()
        opp = score_stock("SBIN.NS", q, sec, [], [])
        assert isinstance(opp, StockOpportunity)

    def test_score_bounded(self):
        q   = make_quote_for_stock(trend="up")
        sec = make_sector()
        opp = score_stock("SBIN.NS", q, sec, [], [])
        assert 0 <= opp.score <= 100

    def test_bulk_deal_boosts_confluence(self):
        q    = make_quote_for_stock(trend="up")
        sec  = make_sector()
        deal = make_bulk_deal("SBIN")
        opp_with    = score_stock("SBIN.NS", q, sec, [deal], [])
        opp_without = score_stock("SBIN.NS", q, sec, [], [])
        # Bulk deal should increase confluence
        assert opp_with.confluence >= opp_without.confluence

    def test_bulk_deal_attached(self):
        q    = make_quote_for_stock(trend="up")
        sec  = make_sector()
        deal = make_bulk_deal("SBIN")
        opp  = score_stock("SBIN.NS", q, sec, [deal], [])
        assert opp.bulk_deal is not None
        assert opp.bulk_deal.symbol == "SBIN"

    def test_downtrend_scores_lower(self):
        q_up   = make_quote_for_stock(trend="up")
        q_down = make_quote_for_stock(trend="down")
        sec    = make_sector()
        opp_up   = score_stock("X.NS", q_up,   sec, [], [])
        opp_down = score_stock("X.NS", q_down, sec, [], [])
        assert opp_up.score >= opp_down.score

    def test_name_cleaned(self):
        q   = make_quote_for_stock("SBIN.NS")
        sec = make_sector()
        opp = score_stock("SBIN.NS", q, sec, [], [])
        assert opp.name == "SBIN"   # .NS removed

    def test_setup_type_generated_for_uptrend(self):
        q   = make_quote_for_stock(trend="up", n=120)
        sec = make_sector()
        opp = score_stock("SBIN.NS", q, sec, [], [])
        # Should generate some setup type for an uptrend stock
        assert isinstance(opp.setup_type, str)

    def test_sector_name_assigned(self):
        q   = make_quote_for_stock()
        sec = make_sector(short="PSU")
        opp = score_stock("SBIN.NS", q, sec, [], [])
        assert opp.sector == "PSU"

    def test_price_set_correctly(self):
        q   = make_quote_for_stock(trend="up", n=120)
        sec = make_sector()
        opp = score_stock("X.NS", q, sec, [], [])
        assert opp.price == pytest.approx(q.price)
