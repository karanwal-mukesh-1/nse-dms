"""
tests/test_contradiction_engine.py
=====================================
Unit tests for intelligence/contradiction_engine.py
"""

import pytest
from intelligence.contradiction_engine import (
    detect_contradictions, detect_reflexivity_warnings
)
from core.models import ReflexivityReading


class TestDetectContradictions:
    def test_no_contradictions_clean_market(self):
        flags = detect_contradictions(
            trend_score=75, breadth_score=70, composite=75,
            vix_level=14, vix_slope=-2, sm_signal="ACCUMULATION",
            phase="EARLY TREND", mom_score=70, sm_score=72, nifty_r20=3.0,
        )
        assert len(flags) == 0

    def test_narrow_leadership_detected(self):
        flags = detect_contradictions(
            trend_score=78, breadth_score=38, composite=70,
            vix_level=14, vix_slope=-1, sm_signal="NEUTRAL",
            phase="STRONG TREND", mom_score=65, sm_score=65, nifty_r20=4.0,
        )
        msgs = [f.msg for f in flags]
        assert any("breadth" in m.lower() or "narrow" in m.lower() for m in msgs)

    def test_vix_contradiction_detected(self):
        flags = detect_contradictions(
            trend_score=70, breadth_score=65, composite=75,
            vix_level=25, vix_slope=3, sm_signal="NEUTRAL",
            phase="EARLY TREND", mom_score=65, sm_score=60, nifty_r20=2.0,
        )
        msgs = [f.msg for f in flags]
        assert any("vix" in m.lower() or "volatility" in m.lower() for m in msgs)

    def test_distribution_vs_trend_detected(self):
        flags = detect_contradictions(
            trend_score=72, breadth_score=60, composite=70,
            vix_level=16, vix_slope=0, sm_signal="DISTRIBUTION",
            phase="EARLY TREND", mom_score=65, sm_score=30, nifty_r20=3.0,
        )
        msgs = [f.msg for f in flags]
        assert any("distribut" in m.lower() for m in msgs)

    def test_late_trend_exhaustion_detected(self):
        flags = detect_contradictions(
            trend_score=72, breadth_score=65, composite=74,
            vix_level=15, vix_slope=-1, sm_signal="NEUTRAL",
            phase="LATE TREND", mom_score=80, sm_score=65, nifty_r20=5.0,
        )
        msgs = [f.msg for f in flags]
        assert any("late trend" in m.lower() or "exhaustion" in m.lower() for m in msgs)

    def test_vix_rising_sharply_detected(self):
        flags = detect_contradictions(
            trend_score=70, breadth_score=65, composite=68,
            vix_level=18, vix_slope=12, sm_signal="NEUTRAL",
            phase="EARLY TREND", mom_score=65, sm_score=60, nifty_r20=2.0,
        )
        msgs = [f.msg for f in flags]
        assert any("vix" in m.lower() and "rising" in m.lower() for m in msgs)

    def test_returns_contradiction_objects(self):
        from core.models import Contradiction
        flags = detect_contradictions(
            trend_score=78, breadth_score=38, composite=70,
            vix_level=14, vix_slope=-1, sm_signal="NEUTRAL",
            phase="STRONG TREND", mom_score=65, sm_score=65, nifty_r20=4.0,
        )
        assert all(isinstance(f, Contradiction) for f in flags)

    def test_contradiction_has_severity(self):
        flags = detect_contradictions(
            trend_score=78, breadth_score=38, composite=70,
            vix_level=14, vix_slope=-1, sm_signal="NEUTRAL",
            phase="STRONG TREND", mom_score=65, sm_score=65, nifty_r20=4.0,
        )
        for f in flags:
            assert f.severity in ("danger", "warn", "info")

    def test_multiple_contradictions(self):
        # Trigger multiple: narrow breadth + distribution + late trend + VIX rising
        flags = detect_contradictions(
            trend_score=78, breadth_score=38, composite=75,
            vix_level=24, vix_slope=10, sm_signal="DISTRIBUTION",
            phase="LATE TREND", mom_score=82, sm_score=28, nifty_r20=5.0,
        )
        assert len(flags) >= 3

    def test_no_vix_data_handled(self):
        # Should not crash when vix_level is None
        flags = detect_contradictions(
            trend_score=70, breadth_score=65, composite=70,
            vix_level=None, vix_slope=None, sm_signal="NEUTRAL",
            phase="EARLY TREND", mom_score=65, sm_score=60, nifty_r20=2.0,
        )
        assert isinstance(flags, list)


class TestReflexivityWarnings:
    def make_reading(self, sector, stage, conviction, gap) -> ReflexivityReading:
        return ReflexivityReading(
            sector=sector, price_momentum=gap+50,
            fundamental_score=50, gap=gap,
            stage=stage, conviction=conviction,
        )

    def test_loop_top_high_conviction_warned(self):
        readings = [self.make_reading("IT", "LOOP_TOP", "HIGH", 25)]
        warnings = detect_reflexivity_warnings(readings)
        assert len(warnings) == 1
        assert "IT" in warnings[0]

    def test_loop_top_low_conviction_ignored(self):
        readings = [self.make_reading("IT", "LOOP_TOP", "LOW", 25)]
        warnings = detect_reflexivity_warnings(readings)
        assert len(warnings) == 0

    def test_neglected_high_conviction_surfaced(self):
        readings = [self.make_reading("METAL", "NEGLECTED", "HIGH", -15)]
        warnings = detect_reflexivity_warnings(readings)
        assert len(warnings) == 1
        assert "METAL" in warnings[0]

    def test_early_loop_no_warning(self):
        readings = [self.make_reading("FMCG", "EARLY_LOOP", "MEDIUM", 5)]
        warnings = detect_reflexivity_warnings(readings)
        assert len(warnings) == 0

    def test_empty_input(self):
        warnings = detect_reflexivity_warnings([])
        assert warnings == []

    def test_multiple_readings(self):
        readings = [
            self.make_reading("IT",    "LOOP_TOP",  "HIGH",   30),
            self.make_reading("METAL", "NEGLECTED", "HIGH",  -20),
            self.make_reading("BANK",  "EARLY_LOOP","MEDIUM",  5),
        ]
        warnings = detect_reflexivity_warnings(readings)
        assert len(warnings) == 2   # IT (loop top) + METAL (neglected)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
