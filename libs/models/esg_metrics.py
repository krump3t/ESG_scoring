"""
ESG Metrics Pydantic Model - Phase 3 (v3 Enhancement #2)

**IMPORTANT**: This model is designed for Parquet schema parity.
All fields must be serializable to PyArrow types.

**Data Sources**:
- Financial metrics: SEC EDGAR companyfacts JSON (us-gaap taxonomy)
- ESG metrics: Sustainability reports via watsonx.ai extraction (future)

Author: Scientific Coding Agent v13.8-MEA
Date: 2025-10-24
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ESGMetrics(BaseModel):
    """ESG and financial metrics extracted from company reports.

    This model combines:
    1. Financial/Governance metrics from SEC EDGAR (structured)
    2. Environmental/Social metrics from sustainability reports (LLM-extracted)

    All fields are Optional to handle incomplete data gracefully.
    Parquet-compatible via to_parquet_dict() and from_parquet_dict() methods.
    """

    # ========================================================================
    # IDENTIFIERS
    # ========================================================================

    company_name: str = Field(..., description="Company name", min_length=1)
    cik: Optional[str] = Field(None, description="SEC Central Index Key (10 digits)")
    fiscal_year: int = Field(..., ge=2000, le=2030, description="Fiscal year")
    fiscal_period: Optional[str] = Field(None, description="Fiscal period (e.g., FY, Q1, Q2)")
    report_date: Optional[datetime] = Field(None, description="Report publication date")

    # ========================================================================
    # FINANCIAL METRICS (from SEC EDGAR us-gaap)
    # ========================================================================

    # Balance Sheet
    assets: Optional[float] = Field(None, ge=0, description="Total assets (USD)")
    liabilities: Optional[float] = Field(None, ge=0, description="Total liabilities (USD)")
    stockholders_equity: Optional[float] = Field(None, description="Stockholders equity (USD)")

    # Income Statement
    revenues: Optional[float] = Field(None, ge=0, description="Total revenues (USD)")
    net_income: Optional[float] = Field(None, description="Net income/loss (USD)")
    operating_income: Optional[float] = Field(None, description="Operating income (USD)")

    # Shares
    shares_outstanding: Optional[float] = Field(None, ge=0, description="Common stock shares outstanding")

    # ========================================================================
    # GOVERNANCE METRICS (from SEC EDGAR + Proxy Statements)
    # ========================================================================

    board_size: Optional[int] = Field(None, ge=0, le=50, description="Number of board members")
    independent_directors_pct: Optional[float] = Field(None, ge=0, le=100, description="% independent directors")
    board_diversity_pct: Optional[float] = Field(None, ge=0, le=100, description="% diverse board members")

    # ========================================================================
    # ENVIRONMENTAL METRICS (from Sustainability Reports via watsonx.ai)
    # ========================================================================

    # GHG Emissions
    scope1_emissions: Optional[float] = Field(None, ge=0, description="Scope 1 GHG emissions (metric tons CO2e)")
    scope2_emissions: Optional[float] = Field(None, ge=0, description="Scope 2 GHG emissions (metric tons CO2e)")
    scope3_emissions: Optional[float] = Field(None, ge=0, description="Scope 3 GHG emissions (metric tons CO2e)")

    # Energy & Resources
    energy_consumption: Optional[float] = Field(None, ge=0, description="Total energy consumption (GJ)")
    renewable_energy_pct: Optional[float] = Field(None, ge=0, le=100, description="% energy from renewables")
    water_withdrawal: Optional[float] = Field(None, ge=0, description="Water withdrawal (cubic meters)")

    # Waste
    waste_generated: Optional[float] = Field(None, ge=0, description="Total waste generated (metric tons)")
    waste_recycled_pct: Optional[float] = Field(None, ge=0, le=100, description="% waste recycled")

    # ========================================================================
    # SOCIAL METRICS (from Sustainability Reports via watsonx.ai)
    # ========================================================================

    employee_count: Optional[int] = Field(None, ge=0, description="Total employees")
    employee_turnover_pct: Optional[float] = Field(None, ge=0, le=100, description="Employee turnover rate %")
    women_in_workforce_pct: Optional[float] = Field(None, ge=0, le=100, description="% women in workforce")
    safety_incident_rate: Optional[float] = Field(None, ge=0, description="Total recordable incident rate (TRIR)")

    # ========================================================================
    # METADATA
    # ========================================================================

    extraction_method: str = Field(
        default="unknown",
        description="Extraction method: 'structured' (JSON) or 'llm' (PDF/HTML)"
    )
    extraction_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of extraction"
    )
    data_source: Optional[str] = Field(
        None,
        description="Data source: 'sec_edgar', 'sustainability_report', etc."
    )

    class Config:
        """Pydantic configuration for immutability and type safety."""
        frozen = True  # Immutable (hashable for deduplication)
        arbitrary_types_allowed = False  # Strict type checking

    # ========================================================================
    # PARQUET SERIALIZATION
    # ========================================================================

    def to_parquet_dict(self) -> dict:
        """Convert to Parquet-compatible dictionary.

        Converts datetime objects to ISO 8601 strings since Parquet
        doesn't natively support Python datetime objects without timezone info.

        Returns:
            Dictionary with all datetime fields as ISO strings
        """
        data = self.dict()

        # Convert datetimes to ISO strings
        if data.get("report_date"):
            data["report_date"] = data["report_date"].isoformat()
        if data.get("extraction_timestamp"):
            data["extraction_timestamp"] = data["extraction_timestamp"].isoformat()

        return data

    @classmethod
    def from_parquet_dict(cls, data: dict) -> "ESGMetrics":
        """Load ESGMetrics from Parquet dictionary.

        Converts ISO string datetimes back to Python datetime objects.

        Args:
            data: Dictionary loaded from Parquet (with ISO datetime strings)

        Returns:
            ESGMetrics instance with proper datetime objects
        """
        # Convert ISO strings back to datetimes
        if data.get("report_date") and isinstance(data["report_date"], str):
            data["report_date"] = datetime.fromisoformat(data["report_date"])
        if data.get("extraction_timestamp") and isinstance(data["extraction_timestamp"], str):
            data["extraction_timestamp"] = datetime.fromisoformat(data["extraction_timestamp"])

        return cls(**data)


# ============================================================================
# PARQUET SCHEMA DEFINITION (for PyArrow)
# ============================================================================

import pyarrow as pa

ESG_METRICS_PARQUET_SCHEMA = pa.schema([
    # Identifiers
    ("company_name", pa.string()),
    ("cik", pa.string(), True),  # nullable
    ("fiscal_year", pa.int32()),
    ("fiscal_period", pa.string(), True),
    ("report_date", pa.string(), True),  # ISO string

    # Financial metrics
    ("assets", pa.float64(), True),
    ("liabilities", pa.float64(), True),
    ("stockholders_equity", pa.float64(), True),
    ("revenues", pa.float64(), True),
    ("net_income", pa.float64(), True),
    ("operating_income", pa.float64(), True),
    ("shares_outstanding", pa.float64(), True),

    # Governance metrics
    ("board_size", pa.int32(), True),
    ("independent_directors_pct", pa.float64(), True),
    ("board_diversity_pct", pa.float64(), True),

    # Environmental metrics
    ("scope1_emissions", pa.float64(), True),
    ("scope2_emissions", pa.float64(), True),
    ("scope3_emissions", pa.float64(), True),
    ("energy_consumption", pa.float64(), True),
    ("renewable_energy_pct", pa.float64(), True),
    ("water_withdrawal", pa.float64(), True),
    ("waste_generated", pa.float64(), True),
    ("waste_recycled_pct", pa.float64(), True),

    # Social metrics
    ("employee_count", pa.int64(), True),
    ("employee_turnover_pct", pa.float64(), True),
    ("women_in_workforce_pct", pa.float64(), True),
    ("safety_incident_rate", pa.float64(), True),

    # Metadata
    ("extraction_method", pa.string()),
    ("extraction_timestamp", pa.string()),  # ISO string
    ("data_source", pa.string(), True),
])
