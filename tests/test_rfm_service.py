"""Tests for RFM service."""
from datetime import date

import pytest

from api.services.rfm_service import (
    _calculate_recency,
    _quantile_bin,
    _quantile_bin_reverse,
    _compute_tertiles,
    _build_segment_label,
    _bin_customers,
    compute_rfm,
)


class TestHelperFunctions:
    """Tests for RFM helper functions."""
    def test_quantile_bin_low(self):
        """Values at or below q33 should be L."""
        assert _quantile_bin(10, 20, 40) == "L"
        assert _quantile_bin(20, 20, 40) == "L"

    def test_quantile_bin_medium(self):
        """Values between q33 and q66 should be M."""
        assert _quantile_bin(30, 20, 40) == "M"
        assert _quantile_bin(40, 20, 40) == "M"

    def test_quantile_bin_high(self):
        """Values above q66 should be H."""
        assert _quantile_bin(50, 20, 40) == "H"

    def test_quantile_bin_reverse_low_value_gets_high(self):
        """In reverse binning, low values get H."""
        assert _quantile_bin_reverse(10, 20, 40) == "H"
        assert _quantile_bin_reverse(20, 20, 40) == "H"

    def test_quantile_bin_reverse_high_value_gets_low(self):
        """In reverse binning, high values get L."""
        assert _quantile_bin_reverse(50, 20, 40) == "L"

    def test_compute_tertiles(self):
        """Tertiles should split values at 33% and 66%."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        q33, q66 = _compute_tertiles(values)
        # int(9*0.33) = 2, so index 2 -> value 3
        # int(9*0.66) = 5, so index 5 -> value 6
        assert q33 == 3
        assert q66 == 6

    def test_build_segment_label(self):
        """Segment label combines R/F/M bins."""
        assert _build_segment_label("H", "M", "L") == "RH_FM_ML"
        assert _build_segment_label("L", "L", "L") == "RL_FL_ML"


class TestBinCustomers:
    """Tests for customer binning logic."""

    def test_bin_customers_empty(self):
        """Empty input returns empty output."""
        assert _bin_customers([], date.today()) == []

    def test_bin_customers_assigns_segments(self):
        """Each customer should get a segment label."""
        customers = [
            {"customer_id": "A", "recency": 1, "frequency": 10, "monetary": 1000},
            {"customer_id": "B", "recency": 30, "frequency": 5, "monetary": 500},
            {"customer_id": "C", "recency": 60, "frequency": 1, "monetary": 100},
        ]
        result = _bin_customers(customers, date.today())
        assert len(result) == 3
        for c in result:
            assert "segment" in c
            assert c["segment"].startswith("R")

    def test_bin_customers_best_customer_high(self):
        """Customer with best metrics should be RH_FH_MH."""
        customers = [
            {"customer_id": "best", "recency": 1, "frequency": 100, "monetary": 10000},
            {"customer_id": "mid", "recency": 30, "frequency": 10, "monetary": 1000},
            {"customer_id": "worst", "recency": 90, "frequency": 1, "monetary": 50},
        ]
        result = _bin_customers(customers, date.today())
        best = next(c for c in result if c["customer_id"] == "best")
        assert best["segment"] == "RH_FH_MH"


@pytest.mark.asyncio
class TestComputeRfm:
    """Integration tests for compute_rfm."""

    async def test_compute_rfm_with_data(self, db_session, sample_transactions):
        """RFM computation returns segmented customers."""
        ref_date = date(2024, 1, 15)
        result = await compute_rfm(db_session, reference_date=ref_date)
        
        assert len(result) == 3
        customer_ids = {c["customer_id"] for c in result}
        assert customer_ids == {"C1", "C2", "C3"}
        
        for c in result:
            assert "segment" in c
            assert "recency" in c
            assert "frequency" in c
            assert "monetary" in c

    async def test_compute_rfm_best_customer_segment(self, db_session, sample_transactions):
        """Best customer (C1) should have high RFM scores."""
        ref_date = date(2024, 1, 15)
        result = await compute_rfm(db_session, reference_date=ref_date)
        
        c1 = next(c for c in result if c["customer_id"] == "C1")
        # C1 has most recent purchase, highest frequency, highest monetary
        assert c1["segment"] == "RH_FH_MH"

    async def test_compute_rfm_empty_db(self, db_session):
        """Empty database returns empty list."""
        result = await compute_rfm(db_session)
        assert result == []
