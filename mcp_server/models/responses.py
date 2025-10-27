"""
Response models for MCP Server
Critical Path: Output formatting for watsonx.orchestrate
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class FindingEvidence(BaseModel):
    """Evidence for a single finding"""
    finding_id: str
    finding_text: str
    page_number: int
    framework: str
    confidence: float


class MaturityQueryResponse(BaseModel):
    """Response model for ESG maturity query"""
    success: bool = True
    org_id: str
    year: int
    theme: str
    maturity_level: int = Field(..., ge=0, le=5)
    maturity_label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    findings_count: int
    key_findings: List[FindingEvidence]
    snapshot_id: Optional[int] = None
    metadata: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "org_id": "microsoft",
                "year": 2024,
                "theme": "Climate",
                "maturity_level": 4,
                "maturity_label": "Leading",
                "confidence": 0.87,
                "findings_count": 12,
                "key_findings": [],
                "snapshot_id": 12345,
                "metadata": {
                    "timestamp": "2025-10-22T04:30:00Z",
                    "run_id": "run-123"
                }
            }
        }


class ScoreExplanation(BaseModel):
    """Explanation for why a score was assigned"""
    score_id: str
    maturity_level: int
    maturity_label: str
    reasoning: str
    evidence: List[FindingEvidence]
    framework_mappings: Dict[str, int]
    confidence_breakdown: Dict[str, float]


class ExplainScoreResponse(BaseModel):
    """Response model for score explanation"""
    success: bool = True
    org_id: str
    year: int
    theme: str
    explanation: ScoreExplanation
    metadata: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "org_id": "microsoft",
                "year": 2024,
                "theme": "Climate",
                "explanation": {
                    "score_id": "score-123",
                    "maturity_level": 4,
                    "maturity_label": "Leading",
                    "reasoning": "Organization has SBTi-approved targets...",
                    "evidence": [],
                    "framework_mappings": {"SBTi": 4, "TCFD": 3},
                    "confidence_breakdown": {"evidence_quality": 0.9, "framework_alignment": 0.85}
                },
                "metadata": {
                    "timestamp": "2025-10-22T04:30:00Z"
                }
            }
        }


class IngestReportResponse(BaseModel):
    """Response model for report ingestion"""
    success: bool
    org_id: str
    year: int
    doc_id: Optional[str] = None
    status: str  # "ingested" | "already_exists" | "failed"
    findings_extracted: int = 0
    scores_generated: int = 0
    message: str
    metadata: Dict[str, Any]


class OrganizationInfo(BaseModel):
    """Information about an organization"""
    org_id: str
    years_available: List[int]
    themes_available: List[str]
    latest_update: datetime
    findings_count: int
    scores_count: int


class ListOrganizationsResponse(BaseModel):
    """Response model for listing organizations"""
    success: bool = True
    organizations: List[OrganizationInfo]
    total_count: int
    metadata: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Organization not found",
                "error_code": "ORG_NOT_FOUND",
                "details": {"org_id": "unknown_company"},
                "metadata": {"timestamp": "2025-10-22T04:30:00Z"}
            }
        }


class MCPToolResponse(BaseModel):
    """Generic MCP tool response wrapper"""
    success: bool
    tool: str
    result: Any
    errors: List[str] = []
    metadata: Dict[str, Any]
