"""
MCP Server for ESG Maturity Assessment
Critical Path: HTTP server exposing agent tools to watsonx.orchestrate
"""
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mcp_server.models.requests import (
    MaturityQueryRequest,
    ExplainScoreRequest,
    IngestReportRequest,
    ListOrganizationsRequest,
    ToolCallRequest
)
from mcp_server.models.responses import (
    MaturityQueryResponse,
    ExplainScoreResponse,
    IngestReportResponse,
    ListOrganizationsResponse,
    ErrorResponse,
    MCPToolResponse
)

# Import agent handlers
from agents.normalizer.mcp_normalizer import MCPNormalizerAgent
from agents.scoring.mcp_scoring import MCPScoringAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Agent registry
AGENTS: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup: Initialize agents
    logger.info("Initializing MCP Server...")

    AGENTS['normalizer'] = MCPNormalizerAgent()
    AGENTS['scoring'] = MCPScoringAgent()

    logger.info(f"Initialized {len(AGENTS)} agents")

    yield

    # Shutdown
    logger.info("Shutting down MCP Server...")


# Create FastAPI app
app = FastAPI(
    title="ESG Maturity Assessment MCP Server",
    description="Multi-agent MCP server for sustainability maturity scoring with watsonx.orchestrate integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Key authentication
async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key from header"""
    # In production, validate against database/environment
    # For now, accept any key or no key for development
    if x_api_key is None:
        logger.warning("No API key provided - using development mode")
        return "dev-key"
    return x_api_key


def generate_metadata(run_id: Optional[str] = None) -> Dict[str, Any]:
    """Generate metadata for responses"""
    if run_id is None:
        run_id = f"run-{uuid.uuid4().hex[:12]}"

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "run_id": run_id,
        "server_version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agents": list(AGENTS.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/tools/list")
async def list_tools(api_key: str = Depends(verify_api_key)):
    """List all available MCP tools"""
    tools = []

    for agent_name, agent in AGENTS.items():
        agent_tools = agent.list_tools()
        for tool_name in agent_tools:
            tool_def = agent.get_tool(tool_name)
            if tool_def:
                tools.append({
                    "name": tool_name,
                    "agent": agent_name,
                    "description": tool_def.get("description", ""),
                    "schema": tool_def.get("inputSchema", {})
                })

    return {
        "success": True,
        "tools": tools,
        "total_count": len(tools),
        "metadata": generate_metadata()
    }


@app.post("/tools/call", response_model=MCPToolResponse)
async def call_tool(
    request: ToolCallRequest,
    api_key: str = Depends(verify_api_key)
):
    """Generic MCP tool call endpoint"""
    run_id = f"run-{uuid.uuid4().hex[:12]}"

    try:
        # Route to appropriate handler based on tool name
        if request.tool == "esg.query.maturity":
            return await handle_maturity_query_internal(request.params, run_id)
        elif request.tool == "esg.explain.score":
            return await handle_explain_score_internal(request.params, run_id)
        elif request.tool == "esg.ingest.report":
            return await handle_ingest_report_internal(request.params, run_id)
        elif request.tool == "esg.list.organizations":
            return await handle_list_organizations_internal(request.params, run_id)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{request.tool}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calling tool {request.tool}: {e}")
        return MCPToolResponse(
            success=False,
            tool=request.tool,
            result=None,
            errors=[str(e)],
            metadata=generate_metadata(run_id)
        )


async def handle_maturity_query_internal(params: Dict[str, Any], run_id: str) -> MCPToolResponse:
    """Internal handler for maturity query"""
    from mcp_server.handlers.query_handler import handle_maturity_query

    req = MaturityQueryRequest(**params)
    response = await handle_maturity_query(req, run_id)

    return MCPToolResponse(
        success=response.success,
        tool="esg.query.maturity",
        result=response.dict(),
        errors=[],
        metadata=response.metadata
    )


async def handle_explain_score_internal(params: Dict[str, Any], run_id: str) -> MCPToolResponse:
    """Internal handler for score explanation"""
    from mcp_server.handlers.explainability_handler import handle_explain_score

    req = ExplainScoreRequest(**params)
    response = await handle_explain_score(req, run_id)

    return MCPToolResponse(
        success=response.success,
        tool="esg.explain.score",
        result=response.dict(),
        errors=[],
        metadata=response.metadata
    )


async def handle_ingest_report_internal(params: Dict[str, Any], run_id: str) -> MCPToolResponse:
    """Internal handler for report ingestion"""
    # Placeholder - will implement when needed
    return MCPToolResponse(
        success=False,
        tool="esg.ingest.report",
        result=None,
        errors=["Not implemented yet"],
        metadata=generate_metadata(run_id)
    )


async def handle_list_organizations_internal(params: Dict[str, Any], run_id: str) -> MCPToolResponse:
    """Internal handler for listing organizations"""
    # Placeholder - will implement when needed
    return MCPToolResponse(
        success=False,
        tool="esg.list.organizations",
        result=None,
        errors=["Not implemented yet"],
        metadata=generate_metadata(run_id)
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            metadata=generate_metadata()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            details={"message": str(exc)},
            metadata=generate_metadata()
        ).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
