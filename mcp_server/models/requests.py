"""
Request models for MCP Server
Critical Path: Input validation for watsonx.orchestrate queries
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class MaturityQueryRequest(BaseModel):
    """Request model for ESG maturity query"""
    org_id: str = Field(..., description="Organization identifier (lowercase)")
    year: int = Field(..., ge=2020, le=2030, description="Reporting year")
    theme: Optional[str] = Field(None, description="ESG theme filter (Climate/Social/Governance)")

    class Config:
        json_schema_extra = {
            "example": {
                "org_id": "microsoft",
                "year": 2024,
                "theme": "Climate"
            }
        }


class ExplainScoreRequest(BaseModel):
    """Request model for score explanation query"""
    org_id: str = Field(..., description="Organization identifier")
    year: int = Field(..., ge=2020, le=2030, description="Reporting year")
    theme: str = Field(..., description="ESG theme")
    score_id: Optional[str] = Field(None, description="Specific score ID to explain")

    class Config:
        json_schema_extra = {
            "example": {
                "org_id": "microsoft",
                "year": 2024,
                "theme": "Climate"
            }
        }


class IngestReportRequest(BaseModel):
    """Request model for report ingestion"""
    org_id: str = Field(..., description="Organization identifier")
    year: int = Field(..., ge=2020, le=2030, description="Reporting year")
    report_url: str = Field(..., description="URL to sustainability report PDF")
    force_refresh: bool = Field(False, description="Force re-ingestion if already exists")

    class Config:
        json_schema_extra = {
            "example": {
                "org_id": "microsoft",
                "year": 2024,
                "report_url": "https://example.com/microsoft-2024-esg.pdf",
                "force_refresh": False
            }
        }


class ListOrganizationsRequest(BaseModel):
    """Request model for listing available organizations"""
    year: Optional[int] = Field(None, ge=2020, le=2030, description="Filter by year")
    has_scores: bool = Field(True, description="Only return orgs with scores")

    class Config:
        json_schema_extra = {
            "example": {
                "year": 2024,
                "has_scores": True
            }
        }


class ToolCallRequest(BaseModel):
    """Generic MCP tool call request"""
    tool: str = Field(..., description="Tool name to invoke")
    params: dict = Field(..., description="Tool parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "tool": "esg.query.maturity",
                "params": {
                    "org_id": "microsoft",
                    "year": 2024,
                    "theme": "Climate"
                }
            }
        }
