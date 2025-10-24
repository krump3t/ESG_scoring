"""
Data Ingestion Contracts (Pydantic Models)

**Phase 2 Enhancement**: Added SourceRef.priority_score field for v3 enhancement #1
(priority-based multi-source download).

**SCA v13.8 Compliance**:
- Type-safe contracts with Pydantic v2
- Immutable models (frozen=True) for SourceRef
- Comprehensive field validation
- JSON serialization/deserialization

**Models**:
- CompanyRef: Company identifier (CIK, name, ticker)
- SourceRef: Data source reference with priority scoring
- CompanyReport: Downloaded report metadata
"""

from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, Literal
from datetime import datetime


class CompanyRef(BaseModel):
    """Reference to a company (identifier for search/download).

    Examples:
        >>> CompanyRef(cik="0000320193", name="Apple Inc.")
        >>> CompanyRef(name="Microsoft Corporation", ticker="MSFT")
    """

    cik: Optional[str] = Field(
        None,
        description="SEC Central Index Key (10-digit zero-padded string)",
        min_length=10,
        max_length=10,
        pattern=r"^\d{10}$"
    )

    name: str = Field(
        ...,
        description="Company name",
        min_length=1
    )

    ticker: Optional[str] = Field(
        None,
        description="Stock ticker symbol (e.g., 'AAPL', 'MSFT')"
    )

    class Config:
        """Pydantic config."""
        frozen = False  # Mutable (may need to add CIK after creation)


class SourceRef(BaseModel):
    """Reference to a data source (URL, API endpoint, etc.).

    **Phase 2 Enhancement**: Added priority_score field for prioritization logic.

    Priority-based download uses (tier, priority_score) tuple:
    - Lower tier = higher quality (1 > 2 > 3)
    - Lower priority_score = higher priority within tier (0 > 50 > 100)

    Examples:
        >>> SourceRef(provider="sec_edgar", tier=1, content_type="application/json", priority_score=5)
        >>> SourceRef(provider="gri", tier=2, content_type="application/pdf", priority_score=30)
    """

    provider: str = Field(
        ...,
        description="Provider name (e.g., 'sec_edgar', 'gri', 'company_ir')",
        min_length=1
    )

    tier: int = Field(
        ...,
        ge=1,
        le=3,
        description="Quality tier: 1=highest (APIs), 2=medium (databases), 3=lowest (web scraping)"
    )

    url: Optional[HttpUrl] = Field(
        None,
        description="Download URL (if applicable)"
    )

    access: Literal["api", "scrape", "file"] = Field(
        "api",
        description="Access method: api=REST API, scrape=web scraping, file=local file"
    )

    content_type: str = Field(
        ...,
        description="MIME type (e.g., 'application/pdf', 'text/html', 'application/json')",
        min_length=1
    )

    priority_score: int = Field(
        100,
        ge=0,
        le=100,
        description="Priority score: 0=highest priority, 100=lowest priority. Lower is better."
    )

    @validator("priority_score")
    def validate_priority_score(cls, v):
        """Ensure priority_score is in valid range [0, 100]."""
        if not (0 <= v <= 100):
            raise ValueError(f"priority_score must be 0-100, got {v}")
        return v

    class Config:
        """Pydantic config."""
        frozen = True  # Immutable (hashable for deduplication)


class CompanyReport(BaseModel):
    """Downloaded company report metadata.

    Represents a successfully downloaded report (PDF, HTML, JSON, etc.)
    with provenance information.

    Examples:
        >>> CompanyReport(
        ...     company=CompanyRef(cik="0000320193", name="Apple Inc."),
        ...     year=2023,
        ...     source=SourceRef(provider="sec_edgar", tier=1, content_type="application/pdf", priority_score=10),
        ...     local_path="/tmp/apple_10k_2023.pdf",
        ...     sha256="abc123..."
        ... )
    """

    company: CompanyRef = Field(
        ...,
        description="Company reference"
    )

    year: int = Field(
        ...,
        ge=2000,
        le=2030,
        description="Fiscal year"
    )

    source: SourceRef = Field(
        ...,
        description="Data source reference (where report was downloaded from)"
    )

    local_path: str = Field(
        ...,
        description="Local file path where report is stored",
        min_length=1
    )

    sha256: str = Field(
        ...,
        description="SHA256 hash of file content (for deduplication)",
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$"
    )

    file_size_bytes: Optional[int] = Field(
        None,
        ge=0,
        description="File size in bytes"
    )

    date_downloaded: Optional[datetime] = Field(
        None,
        description="Timestamp when report was downloaded"
    )

    class Config:
        """Pydantic config."""
        frozen = False  # Mutable (may need to update metadata after creation)


# ============================================================================
# Priority Score Examples (for documentation)
# ============================================================================
"""
Priority Score Guidelines:

**Tier 1 - APIs (Structured Data)**:
- 0-10: XBRL/JSON (fully structured, machine-readable)
  * Example: SEC EDGAR XBRL facts JSON → priority_score=5
- 10-30: PDF from official APIs
  * Example: SEC EDGAR 10-K PDF → priority_score=10
  * Example: CDP Climate Change PDF → priority_score=15
- 30-50: HTML from official APIs
  * Example: SEC EDGAR 10-K HTML → priority_score=20

**Tier 2 - Databases (Semi-Structured)**:
- 30-50: PDF from reputable databases
  * Example: GRI Database PDF → priority_score=30
  * Example: SASB Navigator PDF → priority_score=35
- 50-70: HTML from reputable databases
  * Example: GRI Database HTML → priority_score=40

**Tier 3 - Web Scraping (Unstructured)**:
- 50-80: PDF from company IR sites (high quality, but requires scraping)
  * Example: Company sustainability report PDF → priority_score=50
- 80-100: HTML from company IR sites (low quality, requires complex extraction)
  * Example: Company sustainability page HTML → priority_score=60

**Default**: 100 (lowest priority, fallback for unknown sources)
"""
