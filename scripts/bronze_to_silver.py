#!/usr/bin/env python3
"""
Bronze-to-Silver Transformer - Phase D Implementation

Consolidates theme-partitioned bronze parquet files into a single silver parquet per org/year.
Implements full SCA v13.8 determinism and authenticity requirements.

Usage:
    python scripts/bronze_to_silver.py --org_id MSFT --year 2023
    python scripts/bronze_to_silver.py --all  # Process all bronze data
"""

import argparse
import glob
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Determinism guards
SEED = int(os.getenv("SEED", "42"))
os.environ["PYTHONHASHSEED"] = str(SEED)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "qa" / "run_log.txt", mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def discover_bronze_orgs() -> List[Dict[str, Any]]:
    """
    Discover all org_id/year combinations in bronze layer.

    Returns:
        List of dicts with 'org_id' and 'year' keys
    """
    bronze_root = PROJECT_ROOT / "data" / "bronze"
    if not bronze_root.exists():
        logger.warning(f"Bronze directory not found: {bronze_root}")
        return []

    orgs = []
    for org_dir in bronze_root.glob("org_id=*"):
        org_id = org_dir.name.split("=")[1]
        for year_dir in org_dir.glob("year=*"):
            year = int(year_dir.name.split("=")[1])
            orgs.append({"org_id": org_id, "year": year})

    logger.info(f"Discovered {len(orgs)} org/year combinations in bronze layer")
    return orgs


def load_bronze_partitions(org_id: str, year: int) -> Optional[pd.DataFrame]:
    """
    Load all theme-partitioned bronze parquet files for an org/year.

    Args:
        org_id: Organization identifier (e.g., 'MSFT')
        year: Year (e.g., 2023)

    Returns:
        Consolidated DataFrame with all themes, or None if no data found
    """
    pattern = str(
        PROJECT_ROOT / "data" / "bronze" / f"org_id={org_id}" / f"year={year}" / "theme=*" / "*.parquet"
    )
    files = glob.glob(pattern)

    if not files:
        logger.warning(f"No bronze files found for {org_id}/{year}: {pattern}")
        return None

    logger.info(f"Loading {len(files)} bronze partition files for {org_id}/{year}")

    dfs = []
    for file_path in sorted(files):  # Deterministic ordering
        try:
            df = pd.read_parquet(file_path)
            dfs.append(df)
            logger.debug(f"Loaded {len(df)} records from {Path(file_path).name}")
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            continue

    if not dfs:
        logger.error(f"No valid bronze data loaded for {org_id}/{year}")
        return None

    # Consolidate all themes
    consolidated = pd.concat(dfs, ignore_index=True)

    # Deterministic sorting for reproducibility
    if "evidence_id" in consolidated.columns:
        consolidated = consolidated.sort_values("evidence_id").reset_index(drop=True)

    logger.info(
        f"Consolidated {len(consolidated)} records across {len(dfs)} theme partitions"
    )

    return consolidated


def compute_hash(df: pd.DataFrame) -> str:
    """
    Compute deterministic SHA256 hash of DataFrame contents.

    Args:
        df: DataFrame to hash

    Returns:
        Hex string of SHA256 hash
    """
    # Convert to JSON with sorted keys for determinism
    records = df.to_dict(orient="records")
    json_str = json.dumps(records, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


def write_silver_consolidated(
    df: pd.DataFrame, org_id: str, year: int, overwrite: bool = False
) -> Path:
    """
    Write consolidated DataFrame to silver layer.

    Args:
        df: Consolidated DataFrame
        org_id: Organization identifier
        year: Year
        overwrite: Whether to overwrite existing files

    Returns:
        Path to written parquet file
    """
    silver_dir = (
        PROJECT_ROOT / "data" / "silver" / f"org_id={org_id}" / f"year={year}"
    )
    silver_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = silver_dir / f"{org_id}_{year}_chunks.parquet"
    jsonl_path = silver_dir / f"{org_id}_{year}_chunks.jsonl"
    manifest_path = silver_dir / "ingestion_manifest.json"

    # Check if silver already exists
    if parquet_path.exists() and not overwrite:
        logger.warning(f"Silver file exists (use --overwrite to replace): {parquet_path}")
        return parquet_path

    # Write parquet
    df.to_parquet(parquet_path, index=False, engine="pyarrow")
    logger.info(f"Wrote {len(df)} records to {parquet_path}")

    # Write JSONL for manual inspection
    df.to_json(jsonl_path, orient="records", lines=True, force_ascii=False)
    logger.info(f"Wrote JSONL to {jsonl_path}")

    # Generate manifest
    manifest = {
        "org_id": org_id,
        "year": year,
        "record_count": len(df),
        "schema_version": int(df["schema_version"].iloc[0]) if "schema_version" in df.columns else 1,
        "themes": sorted(df["theme"].unique().tolist()) if "theme" in df.columns else [],
        "data_hash": compute_hash(df),
        "parquet_file": parquet_path.name,
        "jsonl_file": jsonl_path.name,
        "source_layer": "bronze",
        "transformation": "bronze_to_silver_consolidation",
        "created_at": pd.Timestamp.now().isoformat(),
    }

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote manifest to {manifest_path}")
    logger.info(f"Data hash: {manifest['data_hash']}")

    return parquet_path


def transform_bronze_to_silver(
    org_id: Optional[str] = None,
    year: Optional[int] = None,
    overwrite: bool = False,
) -> int:
    """
    Main transformation function: bronze to silver.

    Args:
        org_id: Specific org to process, or None for all
        year: Specific year to process, or None for all
        overwrite: Whether to overwrite existing silver files

    Returns:
        Number of successful transformations
    """
    logger.info("=" * 80)
    logger.info("Bronze->Silver Transformation (Phase D)")
    logger.info(f"SEED={SEED}, PYTHONHASHSEED={os.environ.get('PYTHONHASHSEED')}")
    logger.info("=" * 80)

    # Determine which orgs to process
    if org_id and year:
        targets = [{"org_id": org_id, "year": year}]
    else:
        targets = discover_bronze_orgs()
        if org_id:
            targets = [t for t in targets if t["org_id"] == org_id]
        if year:
            targets = [t for t in targets if t["year"] == year]

    if not targets:
        logger.error("No bronze data found to transform")
        return 0

    logger.info(f"Processing {len(targets)} org/year combinations")

    success_count = 0
    for target in targets:
        org = target["org_id"]
        yr = target["year"]

        logger.info(f"\nProcessing {org}/{yr}...")

        # Load bronze partitions
        df = load_bronze_partitions(org, yr)
        if df is None:
            logger.error(f"Skipping {org}/{yr} - no bronze data loaded")
            continue

        # Write silver consolidated
        try:
            silver_path = write_silver_consolidated(df, org, yr, overwrite=overwrite)
            logger.info(f"[OK] Successfully transformed {org}/{yr} -> {silver_path}")
            success_count += 1
        except Exception as e:
            logger.error(f"[FAIL] Failed to write silver for {org}/{yr}: {e}")
            continue

    logger.info("=" * 80)
    logger.info(f"Transformation complete: {success_count}/{len(targets)} succeeded")
    logger.info("=" * 80)

    return success_count


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Bronze-to-Silver transformer for ESG evidence data"
    )
    parser.add_argument("--org_id", type=str, help="Organization ID (e.g., MSFT)")
    parser.add_argument("--year", type=int, help="Year (e.g., 2023)")
    parser.add_argument(
        "--all", action="store_true", help="Process all discovered bronze data"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing silver files"
    )

    args = parser.parse_args()

    if not args.all and not (args.org_id and args.year):
        parser.error("Must specify either --all or both --org_id and --year")

    # Run transformation
    success_count = transform_bronze_to_silver(
        org_id=args.org_id, year=args.year, overwrite=args.overwrite
    )

    # Exit code: 0 if at least one succeeded, 1 otherwise
    sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    main()
