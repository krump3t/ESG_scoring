"""
Phase 4 TDD Tests for DuckDBReader (Data Lake SQL Query Layer)

Tests written BEFORE implementation per SCA v13.8 TDD Guard.
Uses REAL Phase 3 Apple metrics for authentic SQL query testing.

Critical Path: libs/data_lake/duckdb_reader.py
"""

import os
import pytest
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any
import pyarrow as pa
import pyarrow.parquet as pq
from hypothesis import given, strategies as st

from libs.models.esg_metrics import ESGMetrics, ESG_METRICS_PARQUET_SCHEMA


# ============================================================================
# Fixtures (Real Phase 3 Data + Parquet Files)
# ============================================================================

@pytest.fixture
def parquet_file_with_real_apple(tmp_path: Path) -> Path:
    """Create Parquet file with REAL Apple metrics from Phase 3."""
    metrics = ESGMetrics(
        company_name="Apple Inc.",
        cik="0000320193",
        fiscal_year=2024,
        fiscal_period="FY",
        report_date=datetime(2024, 9, 28, tzinfo=timezone.utc),
        assets=352583000000.0,  # $352.6B
        liabilities=308030000000.0,
        net_income=99803000000.0,  # $99.8B
        scope1_emissions=None,
        scope2_emissions=None,
        renewable_energy_pct=None,
        extraction_method="structured",
        extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
        data_source="SEC EDGAR 10-K FY2024",
        confidence_score=0.98
    )

    # Write to Parquet
    record = metrics.to_parquet_dict()
    table = pa.Table.from_pylist([record], schema=ESG_METRICS_PARQUET_SCHEMA)
    parquet_path = tmp_path / "apple_metrics.parquet"
    pq.write_table(table, parquet_path, compression="snappy")

    return parquet_path


@pytest.fixture
def parquet_file_with_three_companies(tmp_path: Path) -> Path:
    """Create Parquet file with 3 companies (Apple, Microsoft, Tesla)."""
    companies = [
        ESGMetrics(
            company_name="Apple Inc.",
            cik="0000320193",
            fiscal_year=2024,
            fiscal_period="FY",
            report_date=datetime(2024, 9, 28, tzinfo=timezone.utc),
            assets=352583000000.0,
            liabilities=308030000000.0,
            net_income=99803000000.0,
            extraction_method="structured",
            extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
            data_source="SEC EDGAR 10-K FY2024",
            confidence_score=0.98
        ),
        ESGMetrics(
            company_name="Microsoft Corporation",
            cik="0000789019",
            fiscal_year=2024,
            fiscal_period="FY",
            report_date=datetime(2024, 6, 30, tzinfo=timezone.utc),
            assets=512163000000.0,
            liabilities=238515000000.0,
            net_income=88136000000.0,
            renewable_energy_pct=100.0,
            extraction_method="structured",
            extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
            data_source="SEC EDGAR 10-K FY2024",
            confidence_score=0.97
        ),
        ESGMetrics(
            company_name="Tesla, Inc.",
            cik="0001318605",
            fiscal_year=2024,
            fiscal_period="FY",
            report_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
            assets=106618000000.0,
            liabilities=43009000000.0,
            net_income=14974000000.0,
            extraction_method="structured",
            extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
            data_source="SEC EDGAR 10-K FY2024",
            confidence_score=0.96
        )
    ]

    # Write to Parquet
    records = [m.to_parquet_dict() for m in companies]
    table = pa.Table.from_pylist(records, schema=ESG_METRICS_PARQUET_SCHEMA)
    parquet_path = tmp_path / "three_companies.parquet"
    pq.write_table(table, parquet_path, compression="snappy")

    return parquet_path


@pytest.fixture
def parquet_file_multi_year(tmp_path: Path) -> Path:
    """Create Parquet file with Apple metrics for multiple years."""
    years = [2022, 2023, 2024]
    metrics_list = []

    for year in years:
        metrics = ESGMetrics(
            company_name="Apple Inc.",
            cik="0000320193",
            fiscal_year=year,
            fiscal_period="FY",
            report_date=datetime(year, 9, 28, tzinfo=timezone.utc),
            assets=350000000000.0 + (year - 2022) * 10000000000.0,  # Growing assets
            liabilities=300000000000.0,
            net_income=90000000000.0 + (year - 2022) * 5000000000.0,  # Growing income
            extraction_method="structured",
            extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
            data_source=f"SEC EDGAR 10-K FY{year}",
            confidence_score=0.98
        )
        metrics_list.append(metrics)

    # Write to Parquet
    records = [m.to_parquet_dict() for m in metrics_list]
    table = pa.Table.from_pylist(records, schema=ESG_METRICS_PARQUET_SCHEMA)
    parquet_path = tmp_path / "apple_multi_year.parquet"
    pq.write_table(table, parquet_path, compression="snappy")

    return parquet_path


# ============================================================================
# Authentic Data Tests (Real Apple Metrics)
# ============================================================================

@pytest.mark.cp
def test_query_select_all_real_apple(parquet_file_with_real_apple: Path):
    """
    SC3: DuckDB query correctness on REAL Apple metrics.

    SELECT * query returns correct data from Parquet file.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_real_apple.parent))

    sql = f"""
    SELECT company_name, fiscal_year, assets, net_income
    FROM '{parquet_file_with_real_apple}'
    """

    results = reader.query(sql, parquet_file_with_real_apple.name)

    assert len(results) == 1
    row = results[0]

    # Assert REAL Apple metrics
    assert row["company_name"] == "Apple Inc."
    assert row["fiscal_year"] == 2024
    assert row["assets"] == 352583000000.0  # $352.6B
    assert row["net_income"] == 99803000000.0  # $99.8B


@pytest.mark.cp
def test_query_where_filter_assets(parquet_file_with_three_companies: Path):
    """
    SC3: WHERE clause filters companies by assets threshold.

    Tests SQL filter correctness.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_three_companies.parent))

    # Filter companies with assets > $300B (Apple, Microsoft only)
    sql = f"""
    SELECT company_name, assets
    FROM '{parquet_file_with_three_companies}'
    WHERE assets > 300000000000
    ORDER BY assets DESC
    """

    results = reader.query(sql, parquet_file_with_three_companies.name)

    assert len(results) == 2
    assert results[0]["company_name"] == "Microsoft Corporation"  # $512B
    assert results[1]["company_name"] == "Apple Inc."  # $353B


@pytest.mark.cp
def test_query_group_by_aggregate(parquet_file_with_three_companies: Path):
    """
    SC3: GROUP BY with aggregate functions (COUNT, AVG).

    Tests SQL aggregation correctness.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_three_companies.parent))

    # Count companies and average assets
    sql = f"""
    SELECT
        COUNT(*) as company_count,
        AVG(assets) as avg_assets,
        SUM(net_income) as total_income
    FROM '{parquet_file_with_three_companies}'
    """

    results = reader.query(sql, parquet_file_with_three_companies.name)

    assert len(results) == 1
    row = results[0]

    assert row["company_count"] == 3

    # Average assets: (352.6B + 512.2B + 106.6B) / 3 ≈ 323.8B
    expected_avg = (352583000000.0 + 512163000000.0 + 106618000000.0) / 3
    assert abs(row["avg_assets"] - expected_avg) < 1e6  # Within $1M

    # Total income: $99.8B + $88.1B + $15.0B ≈ $202.9B
    expected_total = 99803000000.0 + 88136000000.0 + 14974000000.0
    assert abs(row["total_income"] - expected_total) < 1e6


@pytest.mark.cp
def test_get_latest_metrics_real_apple(parquet_file_multi_year: Path):
    """
    SC3: get_latest_metrics returns most recent fiscal year.

    Tests convenience method with multi-year data.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_multi_year.parent))

    latest = reader.get_latest_metrics(
        "Apple Inc.",
        parquet_file_multi_year.name
    )

    assert latest is not None
    assert latest.fiscal_year == 2024  # Most recent year
    assert latest.company_name == "Apple Inc."
    assert latest.assets == 370000000000.0  # 2024 value


@pytest.mark.cp
def test_get_companies_summary(parquet_file_with_three_companies: Path):
    """
    SC3: get_companies_summary returns aggregate stats per company.

    Tests summary query with GROUP BY.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_three_companies.parent))

    summary = reader.get_companies_summary(parquet_file_with_three_companies.name)

    assert len(summary) == 3

    # Find Apple summary
    apple_summary = [s for s in summary if s["company_name"] == "Apple Inc."][0]

    assert apple_summary["record_count"] == 1
    assert apple_summary["earliest_year"] == 2024
    assert apple_summary["latest_year"] == 2024


@pytest.mark.cp
def test_query_with_null_filtering(parquet_file_with_three_companies: Path):
    """
    SC4: SQL queries handle null values correctly.

    Tests WHERE clause with IS NULL / IS NOT NULL.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_three_companies.parent))

    # Find companies with renewable_energy_pct data
    sql = f"""
    SELECT company_name, renewable_energy_pct
    FROM '{parquet_file_with_three_companies}'
    WHERE renewable_energy_pct IS NOT NULL
    """

    results = reader.query(sql, parquet_file_with_three_companies.name)

    assert len(results) == 1
    assert results[0]["company_name"] == "Microsoft Corporation"
    assert results[0]["renewable_energy_pct"] == 100.0


# ============================================================================
# Failure-Path Tests (Error Handling)
# ============================================================================

@pytest.mark.cp
def test_query_raises_error_for_missing_file(tmp_path: Path):
    """
    Failure path: query on non-existent file raises FileNotFoundError.

    Per TDD Guard: ≥1 failure test required.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(tmp_path))

    with pytest.raises(FileNotFoundError, match="Parquet file not found"):
        reader.query("SELECT * FROM 'missing.parquet'", "missing.parquet")


@pytest.mark.cp
def test_get_latest_metrics_returns_none_for_unknown_company(
    parquet_file_with_real_apple: Path
):
    """
    Failure path: get_latest_metrics returns None for company not in data.

    Tests graceful handling of missing data.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_real_apple.parent))

    result = reader.get_latest_metrics(
        "Unknown Company Inc.",
        parquet_file_with_real_apple.name
    )

    assert result is None


@pytest.mark.cp
def test_query_raises_error_for_invalid_sql(parquet_file_with_real_apple: Path):
    """
    Failure path: invalid SQL syntax raises exception.

    Tests that DuckDB SQL errors are propagated.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_real_apple.parent))

    # Invalid SQL (syntax error)
    sql = "INVALID SQL SYNTAX"

    with pytest.raises(Exception):  # DuckDB will raise some error
        reader.query(sql, parquet_file_with_real_apple.name)


# ============================================================================
# Property-Based Tests (Hypothesis)
# ============================================================================

@pytest.mark.cp
@given(
    threshold=st.floats(min_value=1e9, max_value=1e12, allow_nan=False, allow_infinity=False)
)
def test_query_where_filter_property_based(
    threshold: float,
    parquet_file_with_three_companies: Path
):
    """
    Property test: WHERE clause filtering produces correct result count.

    Per TDD Guard: ≥1 Hypothesis test required.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_three_companies.parent))

    sql = f"""
    SELECT company_name, assets
    FROM '{parquet_file_with_three_companies}'
    WHERE assets > {threshold}
    """

    results = reader.query(sql, parquet_file_with_three_companies.name)

    # All returned rows should have assets > threshold
    for row in results:
        assert row["assets"] > threshold


# ============================================================================
# Integration Tests (End-to-End with ParquetWriter)
# ============================================================================

@pytest.mark.cp
def test_end_to_end_write_query_pipeline(tmp_path: Path):
    """
    SC10: End-to-end pipeline - Phase 3 extract → Phase 4 write → Phase 4 query.

    Full pipeline integration test with REAL Apple metrics.
    """
    from libs.data_lake.parquet_writer import ParquetWriter
    from libs.data_lake.duckdb_reader import DuckDBReader

    # Step 1: Create REAL Phase 3 Apple metrics
    apple_metrics = ESGMetrics(
        company_name="Apple Inc.",
        cik="0000320193",
        fiscal_year=2024,
        fiscal_period="FY",
        report_date=datetime(2024, 9, 28, tzinfo=timezone.utc),
        assets=352583000000.0,
        liabilities=308030000000.0,
        net_income=99803000000.0,
        extraction_method="structured",
        extraction_timestamp=datetime(2025, 10, 24, tzinfo=timezone.utc),
        data_source="SEC EDGAR 10-K FY2024",
        confidence_score=0.98
    )

    # Step 2: Write to Parquet (Phase 4 ParquetWriter)
    writer = ParquetWriter(base_path=str(tmp_path))
    parquet_file = writer.write_metrics(apple_metrics, "pipeline_test.parquet")

    # Step 3: Query with DuckDB (Phase 4 DuckDBReader)
    reader = DuckDBReader(base_path=str(tmp_path))

    sql = """
    SELECT company_name, fiscal_year, assets, net_income
    FROM ${parquet_file}
    WHERE company_name = 'Apple Inc.'
    """

    results = reader.query(sql, "pipeline_test.parquet")

    # Step 4: Validate end-to-end results
    assert len(results) == 1
    row = results[0]

    assert row["company_name"] == "Apple Inc."
    assert row["fiscal_year"] == 2024
    assert row["assets"] == 352583000000.0
    assert row["net_income"] == 99803000000.0


@pytest.mark.cp
def test_connection_reuse(parquet_file_with_real_apple: Path):
    """
    Test that DuckDB connection is reused across multiple queries.

    Validates _connect() caching behavior.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_real_apple.parent))

    # Run multiple queries
    for _ in range(3):
        sql = f"SELECT COUNT(*) as count FROM '{parquet_file_with_real_apple}'"
        results = reader.query(sql, parquet_file_with_real_apple.name)
        assert results[0]["count"] == 1

    # Close connection
    reader.close()


@pytest.mark.cp
def test_query_order_by_sorting(parquet_file_with_three_companies: Path):
    """
    Test ORDER BY clause with DESC sorting.

    Validates SQL sorting correctness.
    """
    from libs.data_lake.duckdb_reader import DuckDBReader

    reader = DuckDBReader(base_path=str(parquet_file_with_three_companies.parent))

    sql = f"""
    SELECT company_name, assets
    FROM '{parquet_file_with_three_companies}'
    ORDER BY assets DESC
    """

    results = reader.query(sql, parquet_file_with_three_companies.name)

    assert len(results) == 3

    # Assert descending order
    assert results[0]["company_name"] == "Microsoft Corporation"  # $512B
    assert results[1]["company_name"] == "Apple Inc."  # $353B
    assert results[2]["company_name"] == "Tesla, Inc."  # $107B
