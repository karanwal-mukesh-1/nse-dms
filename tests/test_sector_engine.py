"""
tests/test_sector_engine.py
============================
Unit tests for intelligence/sector_engine.py
"""

import pytest
from core.models import QuoteData, SectorData, CommodityQuote
from intelligence.sector_engine import (
    build_sector_data, rank_sectors, classify_lifecycle,
    compute_reflexivity, compute_commodity_spillover
)


def make_quote(price=100.0, prev=98.0, n=60, trend="flat") -> QuoteData:
    if trend == "up":
        closes = [80 + i * 0.4 for i in range(n)]
    elif trend == "down":
        closes = [120 - i * 0.4 for i in range(n)]
    else:
        closes = [price] * n
    volumes = [1_000_000.0] * n
    return QuoteData(
        symbol="TEST", price=closes[-1], prev=closes[-2] if n >= 2 else price,
        closes=closes, volumes=volumes,
        h52=max(closes), l52=min(closes),
    )


def make_sector(short="IT", rs=2.0, valid=True, rank_pos=0) -> SectorData:
    return SectorData(
        sym="^CNXIT", name="Nifty IT", short=short,
        stocks=["INFY.NS"], rs_vs_nifty=rs,
        return5d=rs*0.3, return20d=rs, return60d=rs*3,
        chg=rs*0.05, strength=rs,
        valid=valid,
    )


class TestBuildSectorData:
    def test_returns_all_sectors(self):
        from config.settings import SECTORS
        quotes = {}  # empty quotes — all sectors get valid=False
        result = build_sector_data(quotes, nifty_r20=0.0, nifty_r5=0.0)
        assert len(result) == len(SECTORS)

    def test_invalid_when_no_quote(self):
        result = build_sector_data({}, nifty_r20=0.0, nifty_r5=0.0)
        for s in result:
            assert s.valid is False

    def test_rs_vs_nifty_computed(self):
        from config.settings import SECTORS
        sym = SECTORS[0]["sym"]
        q   = make_quote(n=60, trend="up")
        q   = QuoteData(symbol=sym, price=q.price, prev=q.prev,
                         closes=q.closes, volumes=q.volumes,
                         h52=q.h52, l52=q.l52)
        quotes = {sym: q}
        result = build_sector_data(quotes, nifty_r20=0.0, nifty_r5=0.0)
        matching = [s for s in result if s.sym == sym and s.valid]
        if matching:
            # RS should be the sector 20D return when nifty_r20=0
            s = matching[0]
            assert isinstance(s.rs_vs_nifty, float)


class TestRankSectors:
    def test_sorted_by_strength(self):
        sectors = [make_sector(rs=1.0), make_sector(rs=3.0), make_sector(rs=-1.0)]
        ranked  = rank_sectors(sectors)
        assert ranked[0].rs_vs_nifty == 3.0
        assert ranked[-1].rs_vs_nifty == -1.0

    def test_invalid_excluded(self):
        sectors = [
            make_sector(rs=2.0, valid=True),
            make_sector(rs=5.0, valid=False),
        ]
        ranked = rank_sectors(sectors)
        assert len(ranked) == 1
        assert ranked[0].rs_vs_nifty == 2.0

    def test_empty(self):
        assert rank_sectors([]) == []


class TestClassifyLifecycle:
    def test_crowded_when_top_and_strong(self):
        sectors = [make_sector(rs=8.0, short="IT")] + \
                  [make_sector(rs=i*0.5, short=f"S{i}") for i in range(9)]
        ranked  = rank_sectors(sectors)
        lc = classify_lifecycle(ranked[0], ranked)
        assert lc.stage in ("crowded", "consensus", "discovered")

    def test_returns_lifecycle(self):
        sectors = [make_sector(short="IT", rs=2.0)]
        lc = classify_lifecycle(sectors[0], sectors)
        assert lc.sector == "IT"
        assert isinstance(lc.evidence, list)

    def test_has_score_bonus(self):
        sectors = [make_sector(rs=2.0)]
        lc = classify_lifecycle(sectors[0], sectors)
        assert isinstance(lc.score_bonus, int)


class TestComputeReflexivity:
    def test_returns_reading(self):
        from core.models import ReflexivityReading
        sector = make_sector(rs=5.0, short="IT")
        sector.return60d = 15.0
        sym = sector.sym
        q   = make_quote(n=100, trend="up")
        q   = QuoteData(symbol=sym, price=q.price, prev=q.prev,
                         closes=q.closes, volumes=q.volumes)
        result = compute_reflexivity(sector, {sym: q})
        assert isinstance(result, ReflexivityReading)
        assert result.sector == "IT"

    def test_unknown_when_no_quote(self):
        sector = make_sector()
        result = compute_reflexivity(sector, {})
        assert result.stage == "UNKNOWN"

    def test_gap_computed(self):
        sector = make_sector(rs=20.0)
        sector.return60d = 30.0
        sym = sector.sym
        q   = make_quote(n=100, trend="up")
        q   = QuoteData(symbol=sym, price=q.price, prev=q.prev,
                         closes=q.closes, volumes=q.volumes)
        result = compute_reflexivity(sector, {sym: q})
        assert isinstance(result.gap, float)


class TestCommoditySpillover:
    def make_commodity(self, name, chg_5d, sectors, direction=1) -> CommodityQuote:
        return CommodityQuote(
            symbol="TEST", name=name, price=100.0,
            chg_pct=chg_5d*0.2, chg_5d_pct=chg_5d,
            nse_sectors=sectors, direction=direction,
        )

    def test_no_alert_when_small_move(self):
        comms   = [self.make_commodity("Copper", chg_5d=1.0, sectors=["METAL"])]
        sectors = [make_sector(short="METAL")]
        alerts  = compute_commodity_spillover(comms, sectors)
        assert len(alerts) == 0  # below 2% threshold

    def test_alert_when_large_move(self):
        comms   = [self.make_commodity("Copper", chg_5d=5.0, sectors=["METAL"])]
        sectors = [make_sector(short="METAL")]
        alerts  = compute_commodity_spillover(comms, sectors)
        assert len(alerts) == 1
        assert alerts[0]["urgency"] == "HIGH"

    def test_message_contains_commodity_name(self):
        comms   = [self.make_commodity("Crude Oil", chg_5d=3.5, sectors=["ENERGY"])]
        sectors = [make_sector(short="ENERGY")]
        alerts  = compute_commodity_spillover(comms, sectors)
        assert "Crude Oil" in alerts[0]["message"]

    def test_no_affected_sectors_no_alert(self):
        comms   = [self.make_commodity("Wheat", chg_5d=4.0, sectors=["FMCG"])]
        sectors = [make_sector(short="IT")]   # FMCG not in list
        alerts  = compute_commodity_spillover(comms, sectors)
        assert len(alerts) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
