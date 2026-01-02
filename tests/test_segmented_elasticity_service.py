"""Tests for segmented elasticity service."""
from datetime import date

import pytest

from api.services.segmented_elasticity_service import (
    _filter_customers_by_segment,
    _group_by_product,
    elasticity_by_segment,
)


class TestHelperFunctions:
    """Tests for segmented elasticity helper functions."""

    def test_filter_customers_by_segment(self):
        """Should return only matching customer IDs."""
        rfm_data = [
            {"customer_id": "C1", "segment": "RH_FH_MH"},
            {"customer_id": "C2", "segment": "RM_FM_MM"},
            {"customer_id": "C3", "segment": "RH_FH_MH"},
        ]
        result = _filter_customers_by_segment(rfm_data, "RH_FH_MH")
        assert result == {"C1", "C3"}

    def test_filter_customers_by_segment_no_match(self):
        """Should return empty set when no match."""
        rfm_data = [
            {"customer_id": "C1", "segment": "RH_FH_MH"},
        ]
        result = _filter_customers_by_segment(rfm_data, "RL_FL_ML")
        assert result == set()

    def test_group_by_product(self):
        """Should group rows by stock_code."""
        # Create mock row objects with named attributes
        class Row:
            def __init__(self, stock_code, description, avg_price, total_quantity):
                self.stock_code = stock_code
                self.description = description
                self.avg_price = avg_price
                self.total_quantity = total_quantity

        rows = [
            Row("PROD_A", "Product A", 10.0, 5),
            Row("PROD_A", "Product A", 12.0, 8),
            Row("PROD_B", "Product B", 20.0, 3),
        ]
        result = _group_by_product(rows)
        
        assert "PROD_A" in result
        assert "PROD_B" in result
        assert result["PROD_A"]["prices"] == [10.0, 12.0]
        assert result["PROD_A"]["quantities"] == [5, 8]
        assert result["PROD_B"]["prices"] == [20.0]


@pytest.mark.asyncio
class TestElasticityBySegment:
    """Integration tests for elasticity_by_segment."""

    async def test_elasticity_by_segment_filters_customers(
        self, db_session, sample_transactions
    ):
        """Should compute elasticity only for segment customers."""
        ref_date = date(2024, 1, 15)
        
        # C1 is in RH_FH_MH segment and buys PROD_A
        result = await elasticity_by_segment(
            db_session,
            segment="RH_FH_MH",
            reference_date=ref_date,
        )
        
        # Should have results for PROD_A (C1's product)
        stock_codes = {r.stock_code for r in result}
        assert "PROD_A" in stock_codes
        # Should NOT have PROD_C (C3's product, different segment)
        assert "PROD_C" not in stock_codes

    async def test_elasticity_by_segment_no_customers(self, db_session, sample_transactions):
        """Should return empty when no customers in segment."""
        ref_date = date(2024, 1, 15)
        result = await elasticity_by_segment(
            db_session,
            segment="NONEXISTENT_SEGMENT",
            reference_date=ref_date,
        )
        assert result == []

    async def test_elasticity_by_segment_returns_elasticity_result(
        self, db_session, sample_transactions
    ):
        """Results should be ElasticityResult objects with required fields."""
        ref_date = date(2024, 1, 15)
        result = await elasticity_by_segment(
            db_session,
            segment="RH_FH_MH",
            reference_date=ref_date,
        )
        
        for r in result:
            assert hasattr(r, "stock_code")
            assert hasattr(r, "elasticity")
            assert hasattr(r, "sample_size")
            assert hasattr(r, "r_squared")

    async def test_elasticity_by_segment_empty_db(self, db_session):
        """Empty database returns empty list."""
        result = await elasticity_by_segment(db_session, segment="RH_FH_MH")
        assert result == []
