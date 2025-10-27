"""
Ingestion Ledger: Crawl Authenticity Tracking

Records URL, headers, SHA256, and retrieval metadata for every crawled source.
Writes to artifacts/ingestion/manifest.json.

SCA v13.8 Authenticity Refactor - CP Module
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import hashlib
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IngestLedger:
    """Tracks all crawled sources with deterministic content hashes."""

    def __init__(self, manifest_path: str = "artifacts/ingestion/manifest.json"):
        """
        Initialize ledger.

        Args:
            manifest_path: Path to write manifest.json
        """
        self.manifest_path = Path(manifest_path)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: List[Dict[str, Any]] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing manifest if present."""
        if self.manifest_path.exists():
            try:
                data = json.loads(self.manifest_path.read_text())
                if isinstance(data, dict) and "sources" in data:
                    self.entries = data["sources"]
                else:
                    self.entries = []
            except Exception as e:
                logger.warning(f"Failed to load existing manifest: {e}")
                self.entries = []

    def add_crawl(
        self,
        url: str,
        source_hash: str,
        retrieval_date: str,
        status_code: int,
        response_headers: Optional[Dict[str, str]] = None,
        content_bytes: Optional[bytes] = None
    ) -> str:
        """
        Record a crawl event.

        Args:
            url: Source URL
            source_hash: Pre-computed source hash (SHA256 hex)
            retrieval_date: ISO 8601 timestamp
            status_code: HTTP status code
            response_headers: Response headers dict
            content_bytes: Optional raw content for verification

        Returns:
            Entry hash for deduplication
        """
        # If content_bytes provided, verify hash
        if content_bytes:
            computed_hash = hashlib.sha256(content_bytes).hexdigest()
            if source_hash != computed_hash:
                logger.warning(
                    f"Hash mismatch for {url}: "
                    f"provided={source_hash}, computed={computed_hash}"
                )

        entry = {
            "url": url,
            "content_hash_sha256": source_hash,
            "retrieval_date": retrieval_date,
            "status_code": status_code,
            "response_headers": response_headers or {}
        }

        self.entries.append(entry)
        self._save()

        return source_hash

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all ledger entries."""
        return self.entries.copy()

    def get_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Lookup entry by URL."""
        for entry in self.entries:
            if entry["url"] == url:
                return entry
        return None

    def _save(self) -> None:
        """Save ledger to manifest.json."""
        manifest = {
            "ingestion_run_id": self._generate_run_id(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sources": self.entries
        }

        try:
            self.manifest_path.write_text(json.dumps(manifest, indent=2))
            logger.info(f"Saved ledger to {self.manifest_path}")
        except Exception as e:
            logger.error(f"Failed to save ledger: {e}")
            raise

    def _generate_run_id(self) -> str:
        """Generate deterministic run ID."""
        import os
        # Use timestamp for determinism within a run
        ts = datetime.utcnow().isoformat()[:10]  # YYYY-MM-DD
        run_hash = hashlib.sha256(ts.encode()).hexdigest()[:8]
        return f"ingest_{ts}_{run_hash}"
