"""
Pipeline Orchestrator for MCP Server
Critical Path: Executes real bronze→silver→gold pipeline with actual agents
NO MOCKS - All computations are authentic
"""
from typing import List, Dict, Any, Optional
import logging
import os
from pathlib import Path

from mcp_server.data_access import DataAccessLayer
from agents.normalizer.mcp_normalizer import MCPNormalizerAgent
from agents.scoring.mcp_scoring import MCPScoringAgent

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the real data pipeline: Bronze → Silver → Gold

    Uses actual agents and watsonx.ai API - no synthetic data
    """

    def __init__(self, data_access: Optional[DataAccessLayer] = None):
        """Initialize orchestrator with real components"""
        # Auto-detect data access layer: use local if Bronze files exist locally
        if data_access is None:
            project_root = Path(__file__).parents[1]
            bronze_path = project_root / "data" / "bronze"

            # Check if local Bronze directory has Parquet files
            if bronze_path.exists() and list(bronze_path.rglob("*.parquet")):
                logger.info("Detected local Bronze files - using LocalDataAccessLayer")
                from mcp_server.data_access_local import LocalDataAccessLayer
                self.data_access = LocalDataAccessLayer()
            else:
                logger.info("No local Bronze files - using MinIO DataAccessLayer")
                self.data_access = DataAccessLayer()
        else:
            self.data_access = data_access

        self.normalizer = MCPNormalizerAgent()
        self.scorer = MCPScoringAgent()

        logger.info("Initialized PipelineOrchestrator with real agents")

    def ensure_gold_data_exists(self, org_id: str, year: int,
                                theme: Optional[str] = None) -> bool:
        """
        Ensure gold layer data exists for org/year/theme

        If missing, execute full pipeline with real agents
        Returns True if data exists or was successfully created
        """
        logger.info(f"Checking gold data for {org_id}/{year}/{theme}")

        # Query actual gold layer
        existing_scores = self.data_access.query_gold_scores(org_id, year, theme)

        if existing_scores:
            logger.info(f"Gold data already exists: {len(existing_scores)} scores")
            return True

        # Gold data missing - execute pipeline
        logger.info(f"Gold data missing - executing full pipeline")

        return self.execute_pipeline(org_id, year)

    def execute_pipeline(self, org_id: str, year: int) -> bool:
        """
        Execute complete pipeline: Bronze → Silver → Gold

        Uses real agents with actual computation
        """
        run_id = f"pipeline-{org_id}-{year}"

        logger.info(f"[{run_id}] Starting pipeline execution")

        try:
            # Step 1: Query real bronze data
            logger.info(f"[{run_id}] Step 1: Querying bronze layer...")
            bronze_docs = self.data_access.query_bronze_documents(org_id, year)

            if not bronze_docs:
                logger.warning(f"[{run_id}] No bronze data found for {org_id}/{year}")
                return False

            logger.info(f"[{run_id}] Found {len(bronze_docs)} bronze documents")

            # Step 2: Normalize with real agent
            logger.info(f"[{run_id}] Step 2: Normalizing with MCPNormalizerAgent...")
            all_findings = []

            for bronze_doc in bronze_docs:
                # Run actual normalizer
                findings = self.normalizer.normalize_document(bronze_doc)
                all_findings.extend(findings)

                logger.info(f"[{run_id}] Normalized document {bronze_doc.get('doc_id', 'unknown')}: {len(findings)} findings")

            if not all_findings:
                logger.warning(f"[{run_id}] No findings extracted")
                return False

            # Step 3: Write to silver layer
            logger.info(f"[{run_id}] Step 3: Writing {len(all_findings)} findings to silver...")

            # Group by theme for partitioning
            findings_by_theme = {}
            for finding in all_findings:
                theme = finding.get('theme', 'Unclassified')
                if theme not in findings_by_theme:
                    findings_by_theme[theme] = []
                findings_by_theme[theme].append(finding)

            for theme, findings in findings_by_theme.items():
                success = self.data_access.write_silver_findings(org_id, year, theme, findings)
                if success:
                    logger.info(f"[{run_id}] Wrote {len(findings)} findings for theme: {theme}")

            # Step 4: Score with real agent
            logger.info(f"[{run_id}] Step 4: Scoring with MCPScoringAgent...")
            all_scores = self.scorer.score_batch(all_findings, rubric_id='v3.0')

            if not all_scores:
                logger.warning(f"[{run_id}] No scores generated")
                return False

            logger.info(f"[{run_id}] Generated {len(all_scores)} scores")

            # Step 5: Write to gold layer
            logger.info(f"[{run_id}] Step 5: Writing {len(all_scores)} scores to gold...")

            # Group by theme for partitioning
            scores_by_theme = {}
            for score in all_scores:
                theme = score.get('theme', 'Unclassified')
                if theme not in scores_by_theme:
                    scores_by_theme[theme] = []
                scores_by_theme[theme].append(score)

            for theme, scores in scores_by_theme.items():
                success = self.data_access.write_gold_scores(org_id, year, theme, scores)
                if success:
                    logger.info(f"[{run_id}] Wrote {len(scores)} scores for theme: {theme}")

            logger.info(f"[{run_id}] Pipeline execution complete!")
            return True

        except Exception as e:
            logger.error(f"[{run_id}] Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_maturity_scores(self, org_id: str, year: int,
                           theme: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get maturity scores, executing pipeline if needed

        Returns actual scores from gold layer
        """
        # Ensure data exists
        self.ensure_gold_data_exists(org_id, year, theme)

        # Query actual gold layer
        scores = self.data_access.query_gold_scores(org_id, year, theme)

        logger.info(f"Retrieved {len(scores)} scores for {org_id}/{year}/{theme}")

        return scores

    def get_findings(self, org_id: str, year: int,
                    theme: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get normalized findings from silver layer

        Returns actual findings, no mocks
        """
        # Check if silver data exists
        findings = self.data_access.query_silver_findings(org_id, year, theme)

        if not findings:
            # Try to execute pipeline to generate data
            logger.info(f"No silver findings - attempting to execute pipeline")
            self.ensure_gold_data_exists(org_id, year, theme)

            # Re-query
            findings = self.data_access.query_silver_findings(org_id, year, theme)

        logger.info(f"Retrieved {len(findings)} findings for {org_id}/{year}/{theme}")

        return findings
