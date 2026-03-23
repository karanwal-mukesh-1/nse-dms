"""
tests/conftest.py
=================
Shared pytest fixtures available to all test modules.
"""

import sys
import os
import pytest

# Add project root to path so imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def flat_quote():
    from core.models import QuoteData
    closes  = [100.0] * 252
    volumes = [1_000_000.0] * 252
    return QuoteData(
        symbol="FLAT", price=100.0, prev=99.5,
        closes=closes, volumes=volumes,
        h52=105.0, l52=95.0,
    )


@pytest.fixture
def uptrend_quote():
    from core.models import QuoteData
    closes  = [80 + i * 0.2 for i in range(252)]
    volumes = [1_000_000.0] * 252
    return QuoteData(
        symbol="UPTREND", price=closes[-1], prev=closes[-2],
        closes=closes, volumes=volumes,
        h52=max(closes), l52=min(closes),
    )


@pytest.fixture
def downtrend_quote():
    from core.models import QuoteData
    closes  = [130 - i * 0.2 for i in range(252)]
    volumes = [1_000_000.0] * 252
    return QuoteData(
        symbol="DOWNTREND", price=closes[-1], prev=closes[-2],
        closes=closes, volumes=volumes,
        h52=max(closes), l52=min(closes),
    )


@pytest.fixture
def vix_low():
    from core.models import QuoteData
    closes = [13.0] * 252
    return QuoteData(symbol="^INDIAVIX", price=12.0, prev=13.0,
                     closes=closes, volumes=[])


@pytest.fixture
def vix_high():
    from core.models import QuoteData
    closes = [25.0] * 252
    return QuoteData(symbol="^INDIAVIX", price=28.0, prev=25.0,
                     closes=closes, volumes=[])


@pytest.fixture
def sample_sector():
    from core.models import SectorData
    return SectorData(
        sym="^CNXIT", name="Nifty IT", short="IT",
        stocks=["INFY.NS", "TCS.NS"],
        rs_vs_nifty=3.0, return20d=5.0, return5d=1.5,
        chg=0.8, strength=3.0, valid=True,
    )


@pytest.fixture
def sample_bulk_deals():
    from core.models import BulkDeal
    return [
        BulkDeal(date="2025-01-15", symbol="SBIN", name="SBI",
                  client="LIC of India", deal_type="BUY",
                  quantity=5000000, price=820.0, value_cr=410.0,
                  signal_type="DII_BUY", conviction=3),
        BulkDeal(date="2025-01-14", symbol="INFY", name="Infosys",
                  client="Goldman Sachs", deal_type="SELL",
                  quantity=2000000, price=1850.0, value_cr=370.0,
                  signal_type="FII_SELL", conviction=2),
    ]
