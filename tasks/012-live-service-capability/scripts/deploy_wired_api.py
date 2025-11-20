"""
Task 012: Deploy Wired API
Overwrites apps/api/main.py with the fully integrated logic.
"""
from pathlib import Path

API_CONTENT = '''"""
FastAPI ESG Scoring API - SCA v13.8 (Live Wired)
"""
from typing import Any, Dict, List, Optional
import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from libs.utils.clock import get_clock
from apps.api import metrics  # Now works (prometheus_client installed)
from apps.api import health

# Import the components we just built
from apps.pipeline_orchestrator import PipelineOrchestrator
from agents.crawler.ticker_mapper import TickerMapper

clock = get_clock()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ESG Scoring API",
    description="Deterministic ESG maturity assessment via hybrid retrieval + rubric scoring",
    version="2.0.0"
)

app.include_router(metrics.router)
app.include_router(health.create_router())

# --- Data Models ---

class ScoreRequest(BaseModel):
    company: str = Field(..., description="Company name or Ticker", min_length=1)
    year: Optional[int] = Field(None, description="Reporting year (optional)", ge=2000, le=2100)
    query: str = Field(..., description="ESG query/theme to assess", min_length=1)

class ScoreResponse(BaseModel):
    """Unified Response Schema."""
    company: str
    year: int
    status: str
    trace_id: str
    message: str
    mode: str

# --- Endpoints ---

@app.post("/score", response_model=ScoreResponse, status_code=200)
async def score_esg(
    request: ScoreRequest,
    background_tasks: BackgroundTasks,
    semantic: int = Query(default=0, ge=0, le=1),
    k: int = Query(default=10, ge=1, le=100),
    alpha: float = Query(default=0.6, ge=0.0, le=1.0)
) -> ScoreResponse:
    """
    Score ESG maturity. Auto-detects Online/Offline mode.
    """
    start_time = clock.time()
    year = request.year if request.year else 2024

    # Mode Detection
    allow_network = os.getenv("ALLOW_NETWORK", "false").lower() == "true"

    if allow_network:
        # --- ONLINE MODE (Live Ingestion) ---
        logger.info(f"Online Request: {request.company} ({year})")

        # 1. Resolve Ticker -> CIK
        mapper = TickerMapper()
        cik = mapper.get_cik(request.company)

        if not cik:
            # Fallback: Check if input is already a CIK (digits)
            if request.company.isdigit() and len(request.company) <= 10:
                cik = request.company.zfill(10)
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Ticker '{request.company}' not found in SEC database. Please use a valid Ticker (e.g. AAPL) or CIK."
                )

        trace_id = f"live-{cik}-{year}"

        # 2. Configure Orchestrator
        project_config = {
            "paths": {
                "data_lake": "artifacts/data_lake",
                "logs": "artifacts/logs"
            }
        }
        orchestrator = PipelineOrchestrator(project_config)

        # 3. Trigger Background Task (Async Ingestion)
        background_tasks.add_task(
            orchestrator.run_pipeline,
            company_cik=cik,
            fiscal_year=year
        )

        return ScoreResponse(
            company=request.company,
            year=year,
            status="processing",
            trace_id=trace_id,
            message="Ingestion pipeline started in background.",
            mode="online"
        )

    else:
        # --- OFFLINE MODE (Demo / Cache) ---
        logger.info(f"Offline Request: {request.company}")

        # Import legacy demo flow
        from apps.pipeline import demo_flow

        try:
            result = demo_flow.run_score(
                company=request.company,
                year=year,
                query=request.query,
                semantic=bool(semantic),
                alpha=alpha if semantic else 1.0,
                k=k,
                seed=42
            )

            return ScoreResponse(
                company=request.company,
                year=year,
                status="completed",
                trace_id=result.get("trace_id", "cached"),
                message="Retrieved from offline cache.",
                mode="offline"
            )
        except Exception as e:
             raise HTTPException(status_code=500, detail=str(e))

'''

def main():
    dest = Path("apps/api/main.py")
    print(f"Overwriting {dest} with wired V2 API...")
    dest.write_text(API_CONTENT, encoding='utf-8')
    print("Success.")

if __name__ == "__main__":
    main()
