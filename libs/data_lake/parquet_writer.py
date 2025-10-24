"""
ParquetWriter - Phase 4 Data Lake Integration

Writes ESGMetrics to Parquet files with schema validation.
Critical Path implementation per SCA v13.8.

Design: libs/data_lake/parquet_writer.py:100 lines
Tests: tests/data_lake/test_parquet_writer_phase4.py:16 tests
"""

from typing import List, Union
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

from libs.models.esg_metrics import ESGMetrics, ESG_METRICS_PARQUET_SCHEMA


class ParquetWriter:
    """Writes ESGMetrics to Parquet files for data lake storage."""

    def __init__(self, base_path: str = "data_lake"):
        """Initialize Parquet writer.

        Args:
            base_path: Base directory for Parquet files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_metrics(
        self,
        metrics: Union[ESGMetrics, List[ESGMetrics]],
        filename: str = "esg_metrics.parquet"
    ) -> Path:
        """Write metrics to Parquet file (overwrites existing).

        Args:
            metrics: Single ESGMetrics or list of metrics
            filename: Output filename (within base_path)

        Returns:
            Path to written Parquet file

        Raises:
            ValueError: If metrics list is empty
        """
        if not isinstance(metrics, list):
            metrics = [metrics]

        if not metrics:
            raise ValueError("Cannot write empty metrics list")

        # Convert to Parquet dicts using Phase 3 serialization
        records = [m.to_parquet_dict() for m in metrics]

        # Create PyArrow Table with Phase 3 schema
        table = pa.Table.from_pylist(records, schema=ESG_METRICS_PARQUET_SCHEMA)

        # Write to Parquet with Snappy compression
        output_path = self.base_path / filename
        pq.write_table(table, output_path, compression="snappy")

        return output_path

    def append_metrics(
        self,
        metrics: Union[ESGMetrics, List[ESGMetrics]],
        filename: str = "esg_metrics.parquet"
    ) -> Path:
        """Append metrics to existing Parquet file.

        If file doesn't exist, creates new file.

        Args:
            metrics: Single ESGMetrics or list of metrics
            filename: Target filename (within base_path)

        Returns:
            Path to updated Parquet file

        Raises:
            ValueError: If metrics list is empty
        """
        if not isinstance(metrics, list):
            metrics = [metrics]

        if not metrics:
            raise ValueError("Cannot append empty metrics list")

        file_path = self.base_path / filename

        # If file doesn't exist, write new
        if not file_path.exists():
            return self.write_metrics(metrics, filename)

        # Read existing data
        existing_table = pq.read_table(file_path)
        existing_records = existing_table.to_pylist()

        # Append new metrics
        new_records = [m.to_parquet_dict() for m in metrics]
        all_records = existing_records + new_records

        # Write combined data with schema validation
        combined_table = pa.Table.from_pylist(
            all_records,
            schema=ESG_METRICS_PARQUET_SCHEMA
        )
        pq.write_table(combined_table, file_path, compression="snappy")

        return file_path

    def get_row_count(self, filename: str = "esg_metrics.parquet") -> int:
        """Get number of rows in Parquet file.

        Args:
            filename: Parquet filename

        Returns:
            Number of rows

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.base_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {file_path}")

        table = pq.read_table(file_path)
        return table.num_rows
