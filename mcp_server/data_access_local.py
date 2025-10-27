"""
Local File Data Access Layer for MCP Server
Critical Path: Read Bronze/Silver/Gold Parquet files from local filesystem
NO MOCKS - Reads actual Parquet files written by Demo B pipeline
"""
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import duckdb

logger = logging.getLogger(__name__)


class LocalDataAccessLayer:
    """
    Data access layer for local Parquet files

    Reads actual Bronze/Silver/Gold data from filesystem (not MinIO)
    Compatible with Demo B pipeline output
    """

    def __init__(
        self,
        bronze_path: Optional[Path] = None,
        silver_path: Optional[Path] = None,
        gold_path: Optional[Path] = None,
        duckdb_path: Optional[Path] = None
    ):
        """
        Initialize local data access layer

        Args:
            bronze_path: Path to bronze layer (default: data/bronze)
            silver_path: Path to silver layer (default: data/silver)
            gold_path: Path to gold layer (default: data/gold)
            duckdb_path: Path to DuckDB file (default: data/evidence.duckdb)
        """
        # Default paths (project root relative)
        project_root = Path(__file__).parents[1]

        self.bronze_path = bronze_path or (project_root / "data" / "bronze")
        self.silver_path = silver_path or (project_root / "data" / "silver")
        self.gold_path = gold_path or (project_root / "data" / "gold")
        self.duckdb_path = duckdb_path or (project_root / "data" / "evidence.duckdb")

        logger.info(f"Initialized LocalDataAccessLayer")
        logger.info(f"  Bronze: {self.bronze_path}")
        logger.info(f"  Silver: {self.silver_path}")
        logger.info(f"  Gold: {self.gold_path}")
        logger.info(f"  DuckDB: {self.duckdb_path}")

    def query_bronze_documents(self, org_id: str, year: int) -> List[Dict[str, Any]]:
        """
        Query bronze layer for raw evidence

        Reads actual Parquet files from:
          data/bronze/org_id={org_id}/year={year}/theme=*/*.parquet

        Args:
            org_id: Organization identifier (e.g., "MSFT")
            year: Fiscal year

        Returns:
            List of bronze evidence dictionaries (from Evidence dataclass)
        """
        pattern = f"org_id={org_id}/year={year}/theme=*/*.parquet"
        full_pattern = self.bronze_path / pattern

        logger.info(f"Querying bronze layer: {full_pattern}")

        try:
            # Use DuckDB to read Parquet files
            con = duckdb.connect(":memory:")

            # Read all matching Parquet files
            query = f"SELECT * FROM read_parquet('{self.bronze_path}/{pattern}')"
            result = con.execute(query).fetchall()
            columns = [desc[0] for desc in con.description]

            # Convert to list of dicts
            documents = []
            for row in result:
                doc = dict(zip(columns, row))
                documents.append(doc)

            con.close()

            logger.info(f"Found {len(documents)} bronze documents for {org_id}/{year}")

            return documents

        except Exception as e:
            logger.error(f"Error querying bronze layer: {e}")
            return []

    def query_silver_findings(
        self,
        org_id: str,
        year: int,
        theme: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query silver layer for normalized findings

        Reads actual Parquet files from:
          data/silver/org_id={org_id}/year={year}/theme={theme|*}/*.parquet

        Args:
            org_id: Organization identifier
            year: Fiscal year
            theme: Optional theme filter (e.g., "GHG")

        Returns:
            List of silver finding dictionaries
        """
        theme_pattern = f"theme={theme}" if theme else "theme=*"
        pattern = f"org_id={org_id}/year={year}/{theme_pattern}/*.parquet"
        full_pattern = self.silver_path / pattern

        logger.info(f"Querying silver layer: {full_pattern}")

        try:
            # Use DuckDB to read Parquet files
            con = duckdb.connect(":memory:")

            # Read all matching Parquet files
            query = f"SELECT * FROM read_parquet('{self.silver_path}/{pattern}')"
            result = con.execute(query).fetchall()
            columns = [desc[0] for desc in con.description]

            # Convert to list of dicts
            findings = []
            for row in result:
                finding = dict(zip(columns, row))
                findings.append(finding)

            con.close()

            logger.info(f"Found {len(findings)} silver findings for {org_id}/{year}/{theme}")

            return findings

        except Exception as e:
            logger.error(f"Error querying silver layer: {e}")
            return []

    def query_gold_scores(
        self,
        org_id: str,
        year: int,
        theme: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query gold layer for maturity scores

        Reads actual Parquet files from:
          data/gold/org_id={org_id}/year={year}/theme={theme|*}/*.parquet

        Args:
            org_id: Organization identifier
            year: Fiscal year
            theme: Optional theme filter

        Returns:
            List of gold score dictionaries
        """
        theme_pattern = f"theme={theme}" if theme else "theme=*"
        pattern = f"org_id={org_id}/year={year}/{theme_pattern}/*.parquet"
        full_pattern = self.gold_path / pattern

        logger.info(f"Querying gold layer: {full_pattern}")

        # Check if gold path exists
        if not self.gold_path.exists():
            logger.warning(f"Gold path does not exist: {self.gold_path}")
            return []

        try:
            # Use DuckDB to read Parquet files
            con = duckdb.connect(":memory:")

            # Read all matching Parquet files
            query = f"SELECT * FROM read_parquet('{self.gold_path}/{pattern}')"
            result = con.execute(query).fetchall()
            columns = [desc[0] for desc in con.description]

            # Convert to list of dicts
            scores = []
            for row in result:
                score = dict(zip(columns, row))
                scores.append(score)

            con.close()

            logger.info(f"Found {len(scores)} gold scores for {org_id}/{year}/{theme}")

            return scores

        except Exception as e:
            logger.error(f"Error querying gold layer: {e}")
            return []

    def write_silver_findings(
        self,
        org_id: str,
        year: int,
        theme: str,
        findings: List[Dict[str, Any]]
    ) -> bool:
        """
        Write findings to silver layer

        Args:
            org_id: Organization identifier
            year: Fiscal year
            theme: Theme (e.g., "GHG")
            findings: List of finding dictionaries

        Returns:
            True if successful
        """
        import pyarrow as pa
        import pyarrow.parquet as pq
        from datetime import datetime

        if not findings:
            logger.warning("No findings to write")
            return False

        # Create partition path
        partition_path = self.silver_path / f"org_id={org_id}" / f"year={year}" / f"theme={theme}"
        partition_path.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"findings-{timestamp}.parquet"
        file_path = partition_path / filename

        logger.info(f"Writing {len(findings)} findings to {file_path}")

        try:
            # Convert to PyArrow table
            table = pa.Table.from_pylist(findings)

            # Write Parquet file
            pq.write_table(table, file_path)

            logger.info(f"Successfully wrote silver findings: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error writing silver findings: {e}")
            return False

    def write_gold_scores(
        self,
        org_id: str,
        year: int,
        theme: str,
        scores: List[Dict[str, Any]]
    ) -> bool:
        """
        Write scores to gold layer

        Args:
            org_id: Organization identifier
            year: Fiscal year
            theme: Theme (e.g., "GHG")
            scores: List of score dictionaries

        Returns:
            True if successful
        """
        import pyarrow as pa
        import pyarrow.parquet as pq
        from datetime import datetime

        if not scores:
            logger.warning("No scores to write")
            return False

        # Create partition path
        partition_path = self.gold_path / f"org_id={org_id}" / f"year={year}" / f"theme={theme}"
        partition_path.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"scores-{timestamp}.parquet"
        file_path = partition_path / filename

        logger.info(f"Writing {len(scores)} scores to {file_path}")

        try:
            # Convert to PyArrow table
            table = pa.Table.from_pylist(scores)

            # Write Parquet file
            pq.write_table(table, file_path)

            logger.info(f"Successfully wrote gold scores: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error writing gold scores: {e}")
            return False
