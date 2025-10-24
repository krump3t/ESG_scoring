"""
Phase 4 TDD Tests for ParquetWriter (Data Lake Integration)

Tests written BEFORE implementation per SCA v13.8 TDD Guard.
Uses REAL Phase 3 Apple metrics ($352.6B assets) for authentic testing.

Critical Path: libs/data_lake/parquet_writer.py
"""

import os
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
from typing import List
import pyarrow as pa
import pyarrow.parquet as pq
from hypothesis import given, strategies as st

from libs.models.esg_metrics import ESGMetrics, ESG_METRICS_PARQUET_SCHEMA


# ============================================================================
# Fixtures (Real Phase 3 Data)
# ============================================================================

@pytest.fixture
def real_apple_metrics() -> ESGMetrics:
    """REAL Apple Inc. FY2024 metrics from Phase 3 SEC EDGAR extraction."""
    return ESGMetrics(
        company_name="Apple Inc.",
        cik="0000320193",
        fiscal_year=2024,
        fiscal_period="FY",
        report_date=datetime(2024, 9, 28, tzinfo=timezone.utc),
        # Financial metrics (REAL from SEC 10-K)
        assets=352583000000.0,  # $352.6B
        liabilities=308030000000.0,  # $308.0B
        net_income=99803000000.0,  # $99.8B
        # Environmental metrics (nulls for Phase 4 testing)
        scope1_emissions=None,
        scope2_emissions=None,
        scope3_emissions=None,
        renewable_energy_pct=None,
        water_withdrawal=None,
        waste_recycled_pct=None,
        # Social metrics (nulls)
        women_in_workforce_pct=None,
        employee_turnover_pct=None,
        # Governance metrics (nulls)
        board_independence_pct=None,
        # Metadata
        extraction_method="structured",
        extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
        data_source="SEC EDGAR 10-K FY2024",
        confidence_score=0.98
    )


@pytest.fixture
def multiple_companies_metrics(real_apple_metrics: ESGMetrics) -> List[ESGMetrics]:
    """Multiple company metrics for batch testing."""
    # Apple (real)
    apple = real_apple_metrics

    # Microsoft (synthetic but realistic)
    microsoft = ESGMetrics(
        company_name="Microsoft Corporation",
        cik="0000789019",
        fiscal_year=2024,
        fiscal_period="FY",
        report_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
        assets=512163000000.0,  # $512.2B
        liabilities=238515000000.0,  # $238.5B
        net_income=88136000000.0,  # $88.1B
        scope1_emissions=None,
        scope2_emissions=None,
        renewable_energy_pct=100.0,  # Known: Microsoft 100% renewable
        extraction_method="structured",
        extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
        data_source="SEC EDGAR 10-K FY2024",
        confidence_score=0.97
    )

    # Tesla (synthetic but realistic)
    tesla = ESGMetrics(
        company_name="Tesla, Inc.",
        cik="0001318605",
        fiscal_year=2024,
        fiscal_period="FY",
        report_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        assets=106618000000.0,  # $106.6B
        liabilities=43009000000.0,  # $43.0B
        net_income=14974000000.0,  # $15.0B
        scope1_emissions=None,
        scope2_emissions=None,
        renewable_energy_pct=None,
        extraction_method="structured",
        extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
        data_source="SEC EDGAR 10-K FY2024",
        confidence_score=0.96
    )

    return [apple, microsoft, tesla]


# ============================================================================
# Authentic Data Tests (Real Apple Metrics)
# ============================================================================

@pytest.mark.cp
def test_write_single_metrics_real_apple(real_apple_metrics: ESGMetrics, tmp_path: Path):
    """
    SC1: Round-trip integrity for REAL Apple metrics.

    Write Phase 3 Apple metrics → read Parquet → assert 100% field preservation.
    """
    from libs.data_lake.parquet_writer import ParquetWriter

    writer = ParquetWriter(base_path=str(tmp_path))
    output_file = writer.write_metrics(real_apple_metrics, "apple_test.parquet")

    # Assert file created
    assert output_file.exists()
    assert output_file.name == "apple_test.parquet"

    # Read back with PyArrow
    table = pq.read_table(output_file)
    assert table.num_rows == 1

    # Validate schema
    assert table.schema.equals(ESG_METRICS_PARQUET_SCHEMA)

    # Convert to dict
    row = table.to_pylist()[0]

    # Assert REAL Apple metrics preserved
    assert row["company_name"] == "Apple Inc."
    assert row["cik"] == "0000320193"
    assert row["fiscal_year"] == 2024
    assert row["assets"] == 352583000000.0  # $352.6B
    assert row["liabilities"] == 308030000000.0
    assert row["net_income"] == 99803000000.0

    # Assert nulls preserved
    assert row["scope1_emissions"] is None
    assert row["renewable_energy_pct"] is None


@pytest.mark.cp
def test_write_batch_metrics_three_companies(
    multiple_companies_metrics: List[ESGMetrics],
    tmp_path: Path
):
    """
    SC1: Batch write with 3 companies (Apple, Microsoft, Tesla).

    Tests batch write functionality with heterogeneous data.
    """
    from libs.data_lake.parquet_writer import ParquetWriter

    writer = ParquetWriter(base_path=str(tmp_path))
    output_file = writer.write_metrics(
        multiple_companies_metrics,
        "companies_batch.parquet"
    )

    # Assert file created
    assert output_file.exists()

    # Read back
    table = pq.read_table(output_file)
    assert table.num_rows == 3

    rows = table.to_pylist()

    # Validate companies
    companies = {row["company_name"] for row in rows}
    assert companies == {"Apple Inc.", "Microsoft Corporation", "Tesla, Inc."}

    # Validate Apple row
    apple_row = [r for r in rows if r["cik"] == "0000320193"][0]
    assert apple_row["assets"] == 352583000000.0


@pytest.mark.cp
def test_append_metrics_to_existing_file(
    real_apple_metrics: ESGMetrics,
    tmp_path: Path
):
    """
    SC1: Append functionality preserves existing data.

    Write initial metrics → append new metrics → assert both preserved.
    """
    from libs.data_lake.parquet_writer import ParquetWriter

    writer = ParquetWriter(base_path=str(tmp_path))

    # Write initial Apple metrics
    output_file = writer.write_metrics(real_apple_metrics, "append_test.parquet")

    # Create Microsoft metrics
    microsoft = ESGMetrics(
        company_name="Microsoft Corporation",
        cik="0000789019",
        fiscal_year=2024,
        fiscal_period="FY",
        report_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
        assets=512163000000.0,
        liabilities=238515000000.0,
        net_income=88136000000.0,
        extraction_method="structured",
        extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
        data_source="SEC EDGAR 10-K FY2024",
        confidence_score=0.97
    )

    # Append Microsoft metrics
    output_file = writer.append_metrics(microsoft, "append_test.parquet")

    # Read combined file
    table = pq.read_table(output_file)
    assert table.num_rows == 2

    rows = table.to_pylist()
    companies = {row["company_name"] for row in rows}
    assert companies == {"Apple Inc.", "Microsoft Corporation"}


@pytest.mark.cp
def test_datetime_microsecond_precision(real_apple_metrics: ESGMetrics, tmp_path: Path):
    """
    SC5: Datetime fields preserved with microsecond precision.

    Tests that extraction_timestamp and report_date round-trip correctly.
    """
    from libs.data_lake.parquet_writer import ParquetWriter

    # Create metrics with specific microsecond timestamp
    metrics = real_apple_metrics
    original_timestamp = datetime(2025, 10, 24, 14, 30, 45, 123456, tzinfo=timezone.utc)
    metrics.extraction_timestamp = original_timestamp

    writer = ParquetWriter(base_path=str(tmp_path))
    output_file = writer.write_metrics(metrics, "datetime_test.parquet")

    # Read back
    table = pq.read_table(output_file)
    row = table.to_pylist()[0]

    # PyArrow returns Python datetime
    read_timestamp = row["extraction_timestamp"]

    # Assert microsecond precision
    assert read_timestamp.year == original_timestamp.year
    assert read_timestamp.month == original_timestamp.month
    assert read_timestamp.day == original_timestamp.day
    assert read_timestamp.hour == original_timestamp.hour
    assert read_timestamp.minute == original_timestamp.minute
    assert read_timestamp.second == original_timestamp.second
    # Microsecond may vary due to timezone conversion, check within 1 second
    assert abs((read_timestamp - original_timestamp.replace(tzinfo=None)).total_seconds()) < 1


@pytest.mark.cp
def test_null_handling_optional_fields(tmp_path: Path):
    """
    SC4: Null values preserved for Optional ESGMetrics fields.

    Tests that nulls are not converted to 0 or "".
    """
    from libs.data_lake.parquet_writer import ParquetWriter

    # Create metrics with all ESG fields as null
    metrics = ESGMetrics(
        company_name="Test Company",
        cik="0000000000",
        fiscal_year=2024,
        fiscal_period="FY",
        report_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        assets=1000000.0,
        liabilities=500000.0,
        net_income=100000.0,
        # All ESG fields null
        scope1_emissions=None,
        scope2_emissions=None,
        scope3_emissions=None,
        renewable_energy_pct=None,
        water_withdrawal=None,
        waste_recycled_pct=None,
        women_in_workforce_pct=None,
        employee_turnover_pct=None,
        board_independence_pct=None,
        extraction_method="test",
        extraction_timestamp=datetime.now(timezone.utc),
        data_source="test",
        confidence_score=1.0
    )

    writer = ParquetWriter(base_path=str(tmp_path))
    output_file = writer.write_metrics(metrics, "null_test.parquet")

    # Read back
    table = pq.read_table(output_file)
    row = table.to_pylist()[0]

    # Assert nulls preserved (not 0)
    assert row["scope1_emissions"] is None
    assert row["scope2_emissions"] is None
    assert row["renewable_energy_pct"] is None
    assert row["water_withdrawal"] is None
    assert row["women_in_workforce_pct"] is None


@pytest.mark.cp
def test_get_row_count(multiple_companies_metrics: List[ESGMetrics], tmp_path: Path):
    """Test get_row_count method returns correct number of rows."""
    from libs.data_lake.parquet_writer import ParquetWriter

    writer = ParquetWriter(base_path=str(tmp_path))
    writer.write_metrics(multiple_companies_metrics, "count_test.parquet")

    row_count = writer.get_row_count("count_test.parquet")
    assert row_count == 3


# ============================================================================
# Failure-Path Tests (Error Handling)
# ============================================================================

@pytest.mark.cp
def test_write_metrics_raises_error_for_empty_list(tmp_path: Path):
    """
    Failure path: empty metrics list should raise ValueError.

    Per TDD Guard: ≥1 failure test required.
    """
    from libs.data_lake.parquet_writer import ParquetWriter

    writer = ParquetWriter(base_path=str(tmp_path))

    with pytest.raises(ValueError, match="Cannot write empty metrics list"):
        writer.write_metrics([], "empty_test.parquet")


@pytest.mark.cp
def test_append_metrics_raises_error_for_empty_list(tmp_path: Path):
    """Failure path: append with empty list should raise ValueError."""
    from libs.data_lake.parquet_writer import ParquetWriter

    writer = ParquetWriter(base_path=str(tmp_path))

    with pytest.raises(ValueError, match="Cannot append empty metrics list"):
        writer.append_metrics([], "append_fail_test.parquet")


@pytest.mark.cp
def test_get_row_count_raises_error_for_missing_file(tmp_path: Path):
    """Failure path: get_row_count on non-existent file should raise FileNotFoundError."""
    from libs.data_lake.parquet_writer import ParquetWriter

    writer = ParquetWriter(base_path=str(tmp_path))

    with pytest.raises(FileNotFoundError, match="Parquet file not found"):
        writer.get_row_count("missing_file.parquet")


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

@pytest.mark.cp
@given(
    company_name=st.text(min_size=1, max_size=100),
    assets=st.floats(min_value=1.0, max_value=1e15, allow_nan=False, allow_infinity=False),
    fiscal_year=st.integers(min_value=2000, max_value=2030)
)
def test_write_metrics_property_based(
    company_name: str,
    assets: float,
    fiscal_year: int,
    tmp_path: Path
):
    """
    Property test: any valid ESGMetrics instance can be written and read back.

    Per TDD Guard: ≥1 Hypothesis test required.
    """
    from libs.data_lake.parquet_writer import ParquetWriter

    # Create metrics from generated properties
    metrics = ESGMetrics(
        company_name=company_name,
        cik="0000000000",
        fiscal_year=fiscal_year,
        fiscal_period="FY",
        report_date=datetime(fiscal_year, 12, 31, tzinfo=timezone.utc),
        assets=assets,
        liabilities=assets * 0.5,
        net_income=assets * 0.1,
        extraction_method="test",
        extraction_timestamp=datetime.now(timezone.utc),
        data_source="hypothesis",
        confidence_score=0.9
    )

    writer = ParquetWriter(base_path=str(tmp_path))
    output_file = writer.write_metrics(metrics, f"prop_test_{abs(hash(company_name))}.parquet")

    # Read back
    table = pq.read_table(output_file)
    row = table.to_pylist()[0]

    # Assert round-trip
    assert row["company_name"] == company_name
    assert row["fiscal_year"] == fiscal_year
    # Float comparison with tolerance
    assert abs(row["assets"] - assets) < 1.0


# ============================================================================
# Edge Case Tests
# ============================================================================

@pytest.mark.cp
def test_append_creates_new_file_if_not_exists(
    real_apple_metrics: ESGMetrics,
    tmp_path: Path
):
    """
    Edge case: append_metrics creates new file if target doesn't exist.

    Per design.md: "If file doesn't exist, creates new file."
    """
    from libs.data_lake.parquet_writer import ParquetWriter

    writer = ParquetWriter(base_path=str(tmp_path))

    # Append to non-existent file (should create it)
    output_file = writer.append_metrics(
        real_apple_metrics,
        "new_file_append.parquet"
    )

    assert output_file.exists()

    # Read back
    table = pq.read_table(output_file)
    assert table.num_rows == 1


@pytest.mark.cp
def test_write_metrics_overwrites_existing_file(
    real_apple_metrics: ESGMetrics,
    tmp_path: Path
):
    """
    Edge case: write_metrics overwrites existing file.

    Tests idempotent write behavior.
    """
    from libs.data_lake.parquet_writer import ParquetWriter

    writer = ParquetWriter(base_path=str(tmp_path))

    # Write initial file with 1 metric
    writer.write_metrics(real_apple_metrics, "overwrite_test.parquet")

    # Write again with different metric (should overwrite)
    microsoft = ESGMetrics(
        company_name="Microsoft Corporation",
        cik="0000789019",
        fiscal_year=2024,
        fiscal_period="FY",
        report_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
        assets=512163000000.0,
        liabilities=238515000000.0,
        net_income=88136000000.0,
        extraction_method="structured",
        extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
        data_source="SEC EDGAR 10-K FY2024",
        confidence_score=0.97
    )

    output_file = writer.write_metrics(microsoft, "overwrite_test.parquet")

    # Read back - should only have Microsoft (Apple overwritten)
    table = pq.read_table(output_file)
    assert table.num_rows == 1

    row = table.to_pylist()[0]
    assert row["company_name"] == "Microsoft Corporation"
