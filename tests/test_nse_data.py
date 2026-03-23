"""
tests/test_nse_data.py
======================
Unit tests for data/nse_data.py
Tests classification logic (no network calls).
"""

import pytest
from data.nse_data import (
    _classify_bulk_deal, _classify_insider,
    _map_to_sector, detect_insider_clusters
)
from core.models import InsiderActivity


class TestClassifyBulkDeal:
    def test_fii_buy_large(self):
        signal, conv = _classify_bulk_deal("Goldman Sachs", "BUY", 200.0)
        assert signal == "FII_BUY"
        assert conv == 3

    def test_fii_buy_small(self):
        signal, conv = _classify_bulk_deal("Morgan Stanley", "BUY", 50.0)
        assert signal == "FII_BUY"
        assert conv == 2

    def test_dii_buy(self):
        signal, conv = _classify_bulk_deal("LIC of India", "BUY", 100.0)
        assert signal == "DII_BUY"
        assert conv == 2

    def test_promoter_buy(self):
        signal, conv = _classify_bulk_deal("Promoter Family Trust", "BUY", 30.0)
        assert signal == "PROMOTER_BUY"
        assert conv == 3

    def test_promoter_sell_large(self):
        signal, conv = _classify_bulk_deal("Promoter Holdings", "SELL", 80.0)
        assert signal == "PROMOTER_SELL"
        assert conv == 3

    def test_promoter_sell_small(self):
        signal, conv = _classify_bulk_deal("Promoter Holdings", "SELL", 10.0)
        assert signal == "PROMOTER_SELL"
        assert conv == 1

    def test_fii_sell(self):
        signal, conv = _classify_bulk_deal("HSBC Securities", "SELL", 100.0)
        assert signal == "FII_SELL"
        assert conv == 2

    def test_unknown_buyer(self):
        signal, conv = _classify_bulk_deal("Some Random Entity", "BUY", 100.0)
        assert signal == "INSTITUTIONAL_BUY"
        assert conv == 1

    def test_case_insensitive(self):
        signal, _ = _classify_bulk_deal("lic of india", "BUY", 100.0)
        assert signal == "DII_BUY"


class TestClassifyInsider:
    def test_pledge_revoke(self):
        signal = _classify_insider("Revoke", "John", "Promoter", False)
        assert signal == "PLEDGE_REVOKED"

    def test_pledge_invoke(self):
        signal = _classify_insider("Invoke", "John", "Promoter", False)
        assert signal == "PLEDGE_INVOKED"

    def test_promoter_buy_near_low(self):
        signal = _classify_insider("BUY", "John", "Promoter Chairman", near_52w_low=True)
        assert signal == "PROMOTER_BUY_NEAR_LOW"

    def test_promoter_buy_not_near_low(self):
        signal = _classify_insider("BUY", "John", "MD Director", near_52w_low=False)
        assert signal == "PROMOTER_BUY"

    def test_insider_buy(self):
        signal = _classify_insider("ACQUISITION", "John", "CFO Employee", False)
        assert signal == "INSIDER_BUY"

    def test_promoter_sell(self):
        signal = _classify_insider("SELL", "John", "Promoter Chairman", False)
        assert signal == "PROMOTER_SELL"

    def test_insider_sell(self):
        signal = _classify_insider("DISPOSAL", "John", "CFO Employee", False)
        assert signal == "INSIDER_SELL"

    def test_neutral_unknown(self):
        signal = _classify_insider("TRANSFER", "John", "Employee", False)
        assert signal == "NEUTRAL"


class TestMapToSector:
    def test_known_stock(self):
        sector = _map_to_sector("INFY.NS")
        assert sector == "IT"

    def test_known_stock_without_suffix(self):
        sector = _map_to_sector("INFY")
        assert sector == "IT"

    def test_bank_stock(self):
        sector = _map_to_sector("HDFCBANK.NS")
        assert sector == "BANK"

    def test_unknown_stock(self):
        sector = _map_to_sector("UNKNOWNSTOCK.NS")
        assert sector is None

    def test_case_insensitive(self):
        sector = _map_to_sector("infy.ns")
        assert sector == "IT"


class TestDetectInsiderClusters:
    def make_activity(self, symbol: str, signal_type: str, person: str) -> InsiderActivity:
        return InsiderActivity(
            date="2025-01-15", symbol=symbol, name=symbol,
            person=person, designation="Director",
            transaction="BUY", quantity=1000,
            signal_type=signal_type,
        )

    def test_cluster_detected(self):
        acts = [
            self.make_activity("SBIN", "PROMOTER_BUY", "Person A"),
            self.make_activity("SBIN", "PROMOTER_BUY", "Person B"),
            self.make_activity("SBIN", "INSIDER_BUY",  "Person C"),
        ]
        clusters = detect_insider_clusters(acts)
        assert len(clusters) == 1
        assert clusters[0]["symbol"] == "SBIN"
        assert clusters[0]["signal"] == "CLUSTER_BUY"
        assert clusters[0]["conviction"] == 3

    def test_multi_buy_two_persons(self):
        acts = [
            self.make_activity("HDFC", "PROMOTER_BUY", "Person A"),
            self.make_activity("HDFC", "INSIDER_BUY",  "Person B"),
        ]
        clusters = detect_insider_clusters(acts)
        assert len(clusters) == 1
        assert clusters[0]["signal"] == "MULTI_BUY"
        assert clusters[0]["conviction"] == 2

    def test_single_buyer_no_cluster(self):
        acts = [self.make_activity("RELIANCE", "PROMOTER_BUY", "Person A")]
        clusters = detect_insider_clusters(acts)
        assert len(clusters) == 0

    def test_empty_input(self):
        clusters = detect_insider_clusters([])
        assert clusters == []

    def test_multiple_symbols(self):
        acts = [
            self.make_activity("SBIN", "PROMOTER_BUY", "A"),
            self.make_activity("SBIN", "PROMOTER_BUY", "B"),
            self.make_activity("SBIN", "PROMOTER_BUY", "C"),
            self.make_activity("HDFC", "PROMOTER_BUY", "X"),
            self.make_activity("HDFC", "INSIDER_BUY",  "Y"),
        ]
        clusters = detect_insider_clusters(acts)
        assert len(clusters) == 2
        # Sorted by conviction — SBIN should be first
        assert clusters[0]["symbol"] == "SBIN"

    def test_sells_not_counted(self):
        acts = [
            self.make_activity("SBIN", "PROMOTER_SELL", "A"),
            self.make_activity("SBIN", "PROMOTER_SELL", "B"),
            self.make_activity("SBIN", "PROMOTER_SELL", "C"),
        ]
        clusters = detect_insider_clusters(acts)
        assert len(clusters) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
