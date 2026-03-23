"""
tests/test_math_utils.py
========================
Unit tests for core math functions.
Run: python -m pytest tests/ -v
"""

import pytest
from core.math_utils import (
    sma, ema, rsi, pct_change, return_n, slope_nd,
    percentile_rank, rolling_zscore, pct_of_range,
    sharpe_ratio, max_drawdown, momentum_score, reflexivity_gap
)


class TestSMA:
    def test_basic(self):
        assert sma([1, 2, 3, 4, 5], 3) == pytest.approx(4.0)

    def test_insufficient_data(self):
        assert sma([1, 2], 5) is None

    def test_full_series(self):
        assert sma([10, 20, 30], 3) == pytest.approx(20.0)

    def test_empty(self):
        assert sma([], 3) is None


class TestRSI:
    def test_insufficient_data(self):
        assert rsi([1, 2, 3], 14) is None

    def test_all_gains(self):
        # All gains → RSI near 100
        closes = list(range(1, 30))
        r = rsi(closes)
        assert r is not None and r > 90

    def test_all_losses(self):
        # All losses → RSI near 0
        closes = list(range(30, 1, -1))
        r = rsi(closes)
        assert r is not None and r < 10


class TestPctChange:
    def test_positive(self):
        assert pct_change(110, 100) == pytest.approx(10.0)

    def test_negative(self):
        assert pct_change(90, 100) == pytest.approx(-10.0)

    def test_zero_prev(self):
        assert pct_change(100, 0) == 0.0

    def test_no_change(self):
        assert pct_change(100, 100) == pytest.approx(0.0)


class TestReturnN:
    def test_basic(self):
        closes = [100, 102, 104, 106, 110]
        assert return_n(closes, 4) == pytest.approx(10.0)

    def test_insufficient(self):
        assert return_n([100, 110], 5) == 0.0

    def test_negative_return(self):
        closes = [110, 108, 105, 100]
        result = return_n(closes, 3)
        assert result < 0


class TestPercentileRank:
    def test_median(self):
        arr = list(range(1, 101))
        r = percentile_rank(50, arr)
        assert 48 <= r <= 52

    def test_max(self):
        arr = list(range(1, 11))
        assert percentile_rank(11, arr) == 100.0

    def test_min(self):
        arr = list(range(1, 11))
        assert percentile_rank(0, arr) == 0.0

    def test_empty(self):
        assert percentile_rank(5, []) == 50.0


class TestRollingZscore:
    def test_at_mean(self):
        series = [10.0] * 30
        score = rolling_zscore(10.0, series)
        assert 45 <= score <= 55  # near 50 (z=0)

    def test_above_mean(self):
        series = [10.0] * 30
        score = rolling_zscore(15.0, series)
        assert score > 50  # above mean

    def test_insufficient(self):
        assert rolling_zscore(5.0, [1.0], window=60) == 50.0


class TestPctOfRange:
    def test_at_low(self):
        assert pct_of_range(100, 100, 200) == pytest.approx(0.0)

    def test_at_high(self):
        assert pct_of_range(200, 100, 200) == pytest.approx(100.0)

    def test_midpoint(self):
        assert pct_of_range(150, 100, 200) == pytest.approx(50.0)

    def test_equal_range(self):
        assert pct_of_range(100, 100, 100) is None


class TestMaxDrawdown:
    def test_no_drawdown(self):
        assert max_drawdown([100, 110, 120, 130]) == pytest.approx(0.0)

    def test_full_drawdown(self):
        dd = max_drawdown([100, 50])
        assert dd == pytest.approx(50.0)

    def test_recovery(self):
        dd = max_drawdown([100, 80, 120])
        assert dd == pytest.approx(20.0)


class TestReflexivityGap:
    def test_loop_top(self):
        result = reflexivity_gap(30.0, 5.0)
        assert result["stage"] == "LOOP_TOP"
        assert result["gap"] == pytest.approx(25.0)

    def test_neglected(self):
        result = reflexivity_gap(-5.0, 10.0)
        assert result["stage"] == "NEGLECTED"

    def test_early_loop(self):
        result = reflexivity_gap(5.0, 0.0)
        assert result["stage"] == "EARLY_LOOP"

    def test_fundamental_led(self):
        result = reflexivity_gap(2.0, 8.0)
        assert result["stage"] == "FUNDAMENTAL_LED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
