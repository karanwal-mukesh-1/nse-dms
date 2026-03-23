"""
core/math_utils.py
==================
Pure mathematical functions.
No I/O, no state, no side effects.
Every function is independently unit-testable.
"""

from typing import List, Optional
import numpy as np


def sma(arr: List[float], n: int) -> Optional[float]:
    if not arr or len(arr) < n:
        return None
    return float(np.mean(arr[-n:]))


def ema(arr: List[float], n: int) -> Optional[float]:
    """Exponential moving average — more responsive than SMA."""
    if not arr or len(arr) < n:
        return None
    k = 2 / (n + 1)
    result = arr[0]
    for price in arr[1:]:
        result = price * k + result * (1 - k)
    return float(result)


def rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if not closes or len(closes) < period + 1:
        return None
    changes = [closes[i] - closes[i-1] for i in range(-period, 0)]
    gains   = sum(c for c in changes if c > 0) / period
    losses  = sum(abs(c) for c in changes if c < 0) / period
    if losses == 0:
        return 100.0
    return 100 - 100 / (1 + gains / losses)


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """Average True Range — measures volatility."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(-period, 0):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i]  - closes[i-1])
        trs.append(max(hl, hc, lc))
    return float(np.mean(trs))


def pct_change(current: float, prev: float) -> float:
    if not prev or not current:
        return 0.0
    return ((current - prev) / prev) * 100


def return_n(closes: List[float], n: int) -> float:
    if not closes or len(closes) < n + 1:
        return 0.0
    return ((closes[-1] - closes[-1 - n]) / closes[-1 - n]) * 100


def slope_nd(arr: List[float], n: int = 5) -> float:
    """Slope of last n values as % change from first to last."""
    if not arr or len(arr) < n:
        return 0.0
    s = arr[-n:]
    if s[0] == 0:
        return 0.0
    return ((s[-1] - s[0]) / s[0]) * 100


def percentile_rank(value: float, arr: List[float]) -> float:
    """What percentile is value in arr. Self-calibrating score."""
    if not arr or len(arr) < 5:
        return 50.0
    clean = [x for x in arr if x is not None]
    if not clean:
        return 50.0
    return round(len([x for x in clean if x < value]) / len(clean) * 100, 1)


def rolling_zscore(value: float, series: List[float], window: int = 60) -> float:
    """
    Z-score of value vs rolling window, scaled to 0-100.
    More statistically grounded than fixed thresholds.
    """
    if value is None or not series or len(series) < max(window // 2, 5):
        return 50.0
    window_data = series[-window:]
    mu  = float(np.mean(window_data))
    std = float(np.std(window_data))
    if std == 0:
        return 50.0
    z = (value - mu) / std
    z = max(-3.0, min(3.0, z))
    return round((z + 3) / 6 * 100, 1)


def pct_of_range(price: float, l52: Optional[float], h52: Optional[float]) -> Optional[float]:
    """Where is price in its 52-week range. 0%=at low, 100%=at high."""
    if h52 is None or l52 is None or h52 == l52:
        return None
    return round((price - l52) / (h52 - l52) * 100, 1)


def sharpe_ratio(returns: List[float], risk_free: float = 0.065) -> Optional[float]:
    """
    Annualised Sharpe ratio from daily return series.
    risk_free default = 6.5% (approximate India 10Y yield).
    """
    if not returns or len(returns) < 20:
        return None
    daily_rf  = risk_free / 252
    excess     = [r - daily_rf for r in returns]
    mean_ex    = np.mean(excess)
    std_ex     = np.std(excess)
    if std_ex == 0:
        return None
    return round(float(mean_ex / std_ex * np.sqrt(252)), 2)


def max_drawdown(closes: List[float]) -> float:
    """Maximum peak-to-trough drawdown as a percentage."""
    if not closes or len(closes) < 2:
        return 0.0
    peak = closes[0]
    mdd  = 0.0
    for c in closes:
        if c > peak:
            peak = c
        dd = (peak - c) / peak
        if dd > mdd:
            mdd = dd
    return round(mdd * 100, 2)


def rolling_correlation(a: List[float], b: List[float], window: int = 20) -> Optional[float]:
    """Rolling correlation between two series over last `window` periods."""
    if len(a) < window or len(b) < window:
        return None
    return round(float(np.corrcoef(a[-window:], b[-window:])[0, 1]), 3)


def momentum_score(closes: List[float]) -> float:
    """
    Composite momentum: weighted average of multiple return windows.
    12-1 month momentum is the classic academic factor.
    Weights: 1M=20%, 3M=30%, 6M=30%, 12M=20%
    """
    if len(closes) < 60:
        return 0.0
    r1m  = return_n(closes, 20)
    r3m  = return_n(closes, 60)
    r6m  = return_n(closes, 120) if len(closes) >= 120 else r3m
    r12m = return_n(closes, 240) if len(closes) >= 240 else r6m
    return round(r1m*0.2 + r3m*0.3 + r6m*0.3 + r12m*0.2, 2)


def reflexivity_gap(price_momentum_60d: float, fundamental_score: float) -> Dict:
    """
    Soros reflexivity: gap between price and fundamental improvement.
    price_momentum_60d: 60-day price return %
    fundamental_score: 0-100 fundamental improvement (earnings, revenue trend)
    Returns stage and gap.
    """
    gap = price_momentum_60d - fundamental_score
    if gap > 20:
        stage = "LOOP_TOP"       # price far ahead of fundamentals — bust risk
    elif gap > 10:
        stage = "MATURING_LOOP"  # loop is mature
    elif gap > 0:
        stage = "EARLY_LOOP"     # reasonable — price slightly ahead
    elif gap > -10:
        stage = "FUNDAMENTAL_LED" # fundamentals improving, price lagging — BUY
    else:
        stage = "NEGLECTED"      # fundamentals improving strongly, price ignored
    return {"gap": round(gap, 1), "stage": stage}


from typing import Dict   # needed for reflexivity_gap return type hint
