import os
"""
Complete ESG Scoring Pipeline
Integrates all components for end-to-end scoring
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import hashlib
from pathlib import Path
import time

# Import all components
from apps.ingestion.crawler import crawl_sustainabilityreports, ReportRef
from apps.ingestion.parser import parse_pdf, Chunk
from apps.ingestion.validator import validate_chunks, ChunkValidator
from libs.llm.watsonx_client import get_watsonx_client, WatsonXClient
from libs.storage.astradb_vector import get_vector_store, AstraDBVectorStore
from libs.storage.astradb_graph import get_graph_store, AstraDBGraphStore
from libs.retrieval.hybrid_retriever import HybridRetriever
from apps.scoring.scorer import score_company
from apps.scoring.rubric_v3_loader import get_rubric_v3, RubricV3Loader


def get_audit_timestamp():
    """Deterministic timestamp with AUDIT_TIME override"""
    import os
    from datetime import datetime
    audit_time = os.getenv("AUDIT_TIME")
    if audit_time:
        return audit_time
    return get_audit_timestamp()

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for scoring pipeline"""
    # Ingestion
    max_reports_per_company: int = 3
    chunk_size: int = 512
    chunk_overlap: int = 102

    # Retrieval
    retrieval_k: int = 20
    vector_weight: float = 0.7
    expansion_hops: int = 1

    # Scoring
    confidence_threshold: float = 0.6
    min_evidence_per_theme: int = 3

    # Processing
    batch_size: int = 32
    max_workers: int = 4
    cache_results: bool = True

    # Paths
    data_dir: Path = field(default_factory=lambda: Path("data"))
    artifacts_dir: Path = field(default_factory=lambda: Path("artifacts"))
    reports_dir: Path = field(default_factory=lambda: Path("reports"))


@dataclass
class CompanyScore:
    """Complete scoring result for a company"""
    company: str
    year: int
    overall_stage: float
    overall_confidence: float
    theme_scores: Dict[str, Dict[str, Any]]
    evidence_count: int
    processing_time: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ESGScoringPipeline:
    """
    End-to-end pipeline for ESG maturity scoring
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()

        # Initialize components
        self.llm_client = get_watsonx_client()
        self.vector_store = get_vector_store()
        self.graph_store = get_graph_store()
        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            graph_store=self.graph_store,
            llm_client=self.llm_client,
            vector_weight=self.config.vector_weight,
            expansion_hops=self.config.expansion_hops
        )
        self.validator = ChunkValidator()

        # Ensure directories exist
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.config.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.config.reports_dir.mkdir(parents=True, exist_ok=True)

        # ESG themes and rubric v3.0
        self.rubric_loader = get_rubric_v3()
        self.themes = self._load_themes()
        self.rubric = self._load_rubric()

    def _load_themes(self) -> List[str]:
        """Load ESG themes for evaluation from rubric v3.0"""
        # Use the 7 themes from rubric v3.0
        return self.rubric_loader.get_theme_names()

    def _load_rubric(self) -> Dict[str, Dict[int, str]]:
        """Load scoring rubric for each theme from rubric v3.0"""
        rubric = {}

        for theme_code in self.rubric_loader.get_theme_codes():
            theme_rubric = self.rubric_loader.get_rubric_for_llm(theme_code)
            theme_name = self.rubric_loader.get_theme(theme_code).name
            rubric[theme_name] = theme_rubric

        return rubric

    def score_company(
        self,
        company: str,
        year: Optional[int] = None,
        use_cached_data: bool = True
    ) -> CompanyScore:
        """
        Score a single company's ESG maturity
        """
        start_time = time.time()
        logger.info(f"Starting ESG scoring for {company} ({year or 'latest'})")

        # Step 1: Ingest data
        chunks = self._ingest_company_data(company, year, use_cached_data)
        if not chunks:
            logger.warning(f"No data found for {company}")
            return self._create_empty_score(company, year or datetime.fromisoformat(get_audit_timestamp()).year)

        # Step 2: Process and store chunks
        processed_chunks = self._process_chunks(chunks, company, year)

        # Step 3: Score each theme
        theme_scores = {}
        total_evidence = 0

        for theme in self.themes:
            logger.info(f"Scoring {theme} for {company}")
            theme_score = self._score_theme(company, year, theme, processed_chunks)
            theme_scores[theme] = theme_score
            total_evidence += theme_score.get("evidence_count", 0)

        # Step 4: Calculate overall score
        overall_stage, overall_confidence = self._calculate_overall_score(theme_scores)

        # Step 5: Create final score
        processing_time = time.time() - start_time

        score = CompanyScore(
            company=company,
            year=year or datetime.fromisoformat(get_audit_timestamp()).year,
            overall_stage=overall_stage,
            overall_confidence=overall_confidence,
            theme_scores=theme_scores,
            evidence_count=total_evidence,
            processing_time=processing_time,
            timestamp=get_audit_timestamp(),
            metadata={
                "chunks_processed": len(processed_chunks),
                "themes_evaluated": len(self.themes),
                "pipeline_version": "1.0.0"
            }
        )

        # Save results
        self._save_score(score)

        logger.info(f"Completed scoring for {company}: Stage {overall_stage:.1f} (confidence {overall_confidence:.2f})")
        return score

    def _ingest_company_data(
        self,
        company: str,
        year: Optional[int],
        use_cache: bool
    ) -> List[Chunk]:
        """Ingest and parse company ESG reports"""
        all_chunks = []

        # Check cache first
        if use_cache:
            cached_chunks = self._load_cached_chunks(company, year)
            if cached_chunks:
                logger.info(f"Using {len(cached_chunks)} cached chunks for {company}")
                return cached_chunks

        # Crawl for reports
        logger.info(f"Crawling for {company} reports")
        reports = crawl_sustainabilityreports(max_reports=self.config.max_reports_per_company)

        # Filter for company and year
        company_reports = [
            r for r in reports
            if company.lower() in r.company.lower()
            and (year is None or r.year == year)
        ]

        if not company_reports:
            logger.warning(f"No reports found for {company}")
            # Try with static/known URLs
            company_reports = self._get_known_reports(company, year)

        # Parse each report
        for report in company_reports[:self.config.max_reports_per_company]:
            logger.info(f"Parsing {report.company} {report.year} report")
            try:
                chunks = parse_pdf(
                    company=report.company,
                    year=report.year,
                    url=report.url
                )
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Failed to parse {report.url}: {e}")

        # Validate chunks
        if all_chunks:
            valid_chunks, validation_report = validate_chunks(
                all_chunks,
                source_pdf=f"{company}_{year or 'all'}.pdf",
                deduplicate=True,
                track_lineage=True,
                save_results=False
            )
            logger.info(f"Validated {len(valid_chunks)}/{len(all_chunks)} chunks")
            all_chunks = valid_chunks

        # Cache results
        if use_cache and all_chunks:
            self._save_cached_chunks(company, year, all_chunks)

        return all_chunks

    def _get_known_reports(self, company: str, year: Optional[int]) -> List[ReportRef]:
        """Get known report URLs for major companies"""
        known_urls = {
            "Microsoft": [
                ReportRef("Microsoft", "Environmental Sustainability Report", 2023,
                         "https://query.prod.cms.rt.microsoft.com/cms/api/am/binary/RW15mgm")
            ],
            "Apple": [
                ReportRef("Apple", "Environmental Progress Report", 2023,
                         "https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_2023.pdf")
            ],
            "Google": [
                ReportRef("Google", "Environmental Report", 2023,
                         "https://www.gstatic.com/gumdrop/sustainability/google-2023-environmental-report.pdf")
            ]
        }

        reports = []
        for key, urls in known_urls.items():
            if company.lower() in key.lower():
                for report in urls:
                    if year is None or report.year == year:
                        reports.append(report)

        return reports

    def _process_chunks(
        self,
        chunks: List[Chunk],
        company: str,
        year: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Process chunks: generate embeddings and store"""
        processed = []

        # Generate embeddings in batches
        texts = [chunk.text for chunk in chunks]
        embeddings = self.llm_client.generate_embeddings_batch(
            texts,
            batch_size=self.config.batch_size
        )

        # Prepare for storage
        items_to_store = []
        for chunk, embedding in zip(chunks, embeddings):
            metadata = {
                "company": chunk.company,
                "year": chunk.year,
                "section": chunk.section,
                "source_url": chunk.source_url,
                "text": chunk.text,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end
            }

            items_to_store.append((chunk.chunk_id, embedding, metadata))

            # Create graph nodes
            self.graph_store.upsert_node(
                chunk.chunk_id,
                "chunk",
                metadata
            )

            processed.append({
                "chunk": chunk,
                "embedding": embedding,
                "metadata": metadata
            })

        # Batch store in vector database
        if items_to_store:
            success_count = self.vector_store.upsert_batch(items_to_store)
            logger.info(f"Stored {success_count}/{len(items_to_store)} chunks in vector store")

        # Create graph relationships
        self._create_graph_relationships(processed, company, year)

        return processed

    def _create_graph_relationships(
        self,
        processed_chunks: List[Dict[str, Any]],
        company: str,
        year: Optional[int]
    ):
        """Create graph relationships between entities"""
        # Create company node
        company_id = f"company_{company.lower().replace(' ', '_')}"
        self.graph_store.upsert_node(
            company_id,
            "company",
            {"name": company, "year": year}
        )

        # Create theme nodes
        for theme in self.themes:
            theme_id = f"theme_{theme.lower().replace(' ', '_')}"
            self.graph_store.upsert_node(
                theme_id,
                "theme",
                {"name": theme}
            )

        # Link chunks to company and themes
        for item in processed_chunks:
            chunk = item["chunk"]

            # Link to company
            edge_id = f"{chunk.chunk_id}_belongs_to_{company_id}"
            self.graph_store.upsert_edge(
                edge_id=edge_id,
                source_id=chunk.chunk_id,
                target_id=company_id,
                edge_type="belongs_to"
            )

            # Link to relevant themes based on section
            section_lower = chunk.section.lower()
            for theme in self.themes:
                if any(word in section_lower for word in theme.lower().split()):
                    theme_id = f"theme_{theme.lower().replace(' ', '_')}"
                    edge_id = f"{chunk.chunk_id}_references_{theme_id}"
                    self.graph_store.upsert_edge(
                        edge_id=edge_id,
                        source_id=chunk.chunk_id,
                        target_id=theme_id,
                        edge_type="references",
                        properties={"section": chunk.section}
                    )

    def _score_theme(
        self,
        company: str,
        year: Optional[int],
        theme: str,
        processed_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Score a single theme for the company using rubric v3.0"""
        # Retrieve relevant evidence
        query = f"{theme} initiatives targets metrics performance"
        retrieval_results = self.retriever.retrieve(
            query=query,
            company=company,
            year=year,
            theme=theme,
            k=self.config.retrieval_k
        )

        # Check evidence requirements per rubric v3.0
        min_evidence = self.rubric_loader.get_evidence_requirements()
        if len(retrieval_results) < min_evidence:
            logger.warning(f"Insufficient evidence for {theme}: {len(retrieval_results)} chunks (min: {min_evidence})")

        # Extract findings from retrieved chunks
        all_findings = []
        detected_frameworks = []

        for result in retrieval_results[:10]:  # Limit to top 10 for efficiency
            findings = self.llm_client.extract_findings(
                text=result.text,
                query=query,
                theme=theme
            )
            all_findings.extend(findings.get("findings", []))

            # Detect framework signals (SBTi, ISSB, GHG Protocol, CSRD)
            text_lower = result.text.lower()
            if "sbti" in text_lower or "science-based target" in text_lower or "science based target" in text_lower:
                detected_frameworks.append("SBTi")
            if "issb" in text_lower or "tcfd" in text_lower:
                detected_frameworks.append("ISSB_TCFD")
            if "ghg protocol" in text_lower:
                detected_frameworks.append("GHG_Protocol")
            if "csrd" in text_lower or "esrs" in text_lower:
                detected_frameworks.append("CSRD_ESRS")

        detected_frameworks = list(set(detected_frameworks))  # Unique frameworks

        # Classify maturity based on findings
        theme_rubric = self.rubric.get(theme, {})
        classification = self.llm_client.classify_maturity(
            findings=all_findings,
            theme=theme,
            rubric=theme_rubric
        )

        base_stage = classification.get("stage", 0)
        base_confidence = classification.get("confidence", 0.5)

        # Apply framework boosts per rubric v3.0
        theme_code = self._get_theme_code(theme)
        if theme_code and detected_frameworks:
            adjusted_stage = self.rubric_loader.apply_framework_boost(
                theme_code,
                base_stage,
                detected_frameworks
            )
            if adjusted_stage > base_stage:
                logger.info(f"Framework boost applied for {theme}: {base_stage} -> {adjusted_stage} (frameworks: {detected_frameworks})")
        else:
            adjusted_stage = base_stage

        # Apply freshness penalty if evidence is old
        evidence_age_months = self._calculate_evidence_age(year)
        adjusted_confidence = self.rubric_loader.apply_freshness_penalty(
            base_confidence,
            evidence_age_months
        )
        if adjusted_confidence != base_confidence:
            logger.info(f"Freshness penalty applied for {theme}: {base_confidence:.2f} -> {adjusted_confidence:.2f} (age: {evidence_age_months} months)")

        # Get confidence label
        confidence_label = self.rubric_loader.get_confidence_guidance(adjusted_confidence)

        # Build theme score with rubric v3.0 metadata
        theme_score = {
            "stage": adjusted_stage,
            "confidence": adjusted_confidence,
            "confidence_label": confidence_label,
            "evidence_count": len(all_findings),
            "reasoning": classification.get("reasoning", ""),
            "key_findings": all_findings[:5],  # Top 5 findings
            "retrieval_count": len(retrieval_results),
            "detected_frameworks": detected_frameworks,
            "base_stage": base_stage,
            "base_confidence": base_confidence,
            "evidence_age_months": evidence_age_months
        }

        return theme_score

    def _get_theme_code(self, theme_name: str) -> Optional[str]:
        """Get theme code from theme name"""
        theme = self.rubric_loader.get_theme_by_name(theme_name)
        return theme.code if theme else None

    def _calculate_evidence_age(self, year: Optional[int]) -> int:
        """Calculate age of evidence in months"""
        if year is None:
            return 0

        current_year = datetime.fromisoformat(get_audit_timestamp()).year
        years_diff = current_year - year
        return years_diff * 12

    def _calculate_overall_score(
        self,
        theme_scores: Dict[str, Dict[str, Any]]
    ) -> Tuple[float, float]:
        """Calculate overall ESG maturity score"""
        if not theme_scores:
            return 0.0, 0.0

        stages = []
        confidences = []
        weights = []

        for theme, score in theme_scores.items():
            stage = score.get("stage", 0)
            confidence = score.get("confidence", 0.5)
            evidence_count = score.get("evidence_count", 1)

            stages.append(stage)
            confidences.append(confidence)
            # Weight by evidence count
            weights.append(min(evidence_count / self.config.min_evidence_per_theme, 2.0))

        # Weighted average stage
        if sum(weights) > 0:
            overall_stage = sum(s * w for s, w in zip(stages, weights)) / sum(weights)
        else:
            overall_stage = sum(stages) / len(stages)

        # Average confidence weighted by evidence
        if sum(weights) > 0:
            overall_confidence = sum(c * w for c, w in zip(confidences, weights)) / sum(weights)
        else:
            overall_confidence = sum(confidences) / len(confidences)

        return round(overall_stage, 1), round(overall_confidence, 2)

    def _create_empty_score(self, company: str, year: int) -> CompanyScore:
        """Create empty score when no data available"""
        empty_themes = {
            theme: {
                "stage": 0,
                "confidence": 0.0,
                "evidence_count": 0,
                "reasoning": "No data available",
                "key_findings": [],
                "retrieval_count": 0
            }
            for theme in self.themes
        }

        return CompanyScore(
            company=company,
            year=year,
            overall_stage=0.0,
            overall_confidence=0.0,
            theme_scores=empty_themes,
            evidence_count=0,
            processing_time=0.0,
            timestamp=get_audit_timestamp(),
            metadata={"error": "No data available"}
        )

    def _save_score(self, score: CompanyScore):
        """Save scoring results"""
        # Save to JSON
        filename = f"{score.company.lower().replace(' ', '_')}_{score.year}_score.json"
        filepath = self.config.reports_dir / filename

        with open(filepath, 'w') as f:
            json.dump(score.to_dict(), f, indent=2)

        logger.info(f"Saved score to {filepath}")

        # Also save to artifacts
        artifacts_file = self.config.artifacts_dir / "all_scores.jsonl"
        with open(artifacts_file, 'a') as f:
            f.write(json.dumps(score.to_dict()) + '\n')

    def _load_cached_chunks(self, company: str, year: Optional[int]) -> List[Chunk]:
        """Load cached chunks if available"""
        cache_file = self.config.data_dir / f"cache/{company}_{year or 'all'}_chunks.json"

        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    chunks = []
                    for item in data:
                        chunk = Chunk(**item)
                        chunks.append(chunk)
                    return chunks
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")

        return []

    def _save_cached_chunks(self, company: str, year: Optional[int], chunks: List[Chunk]):
        """Save chunks to cache"""
        cache_dir = self.config.data_dir / "cache"
        cache_dir.mkdir(exist_ok=True)

        cache_file = cache_dir / f"{company}_{year or 'all'}_chunks.json"

        try:
            data = [chunk.to_dict() for chunk in chunks]
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Cached {len(chunks)} chunks to {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    def score_multiple_companies(
        self,
        companies: List[str],
        year: Optional[int] = None
    ) -> List[CompanyScore]:
        """Score multiple companies"""
        scores = []

        for company in companies:
            logger.info(f"Processing {company} ({companies.index(company)+1}/{len(companies)})")
            try:
                score = self.score_company(company, year)
                scores.append(score)
            except Exception as e:
                logger.error(f"Failed to score {company}: {e}")
                scores.append(self._create_empty_score(company, year or datetime.fromisoformat(get_audit_timestamp()).year))

        # Generate comparative report
        self._generate_comparative_report(scores)

        return scores

    def _generate_comparative_report(self, scores: List[CompanyScore]):
        """Generate comparative analysis report"""
        report = {
            "timestamp": get_audit_timestamp(),
            "companies_evaluated": len(scores),
            "summary": {},
            "rankings": {},
            "theme_analysis": {}
        }

        # Overall rankings
        scores_sorted = sorted(scores, key=lambda x: x.overall_stage, reverse=True)
        report["rankings"]["overall"] = [
            {
                "rank": i + 1,
                "company": s.company,
                "stage": s.overall_stage,
                "confidence": s.overall_confidence
            }
            for i, s in enumerate(scores_sorted)
        ]

        # Theme-specific rankings
        for theme in self.themes:
            theme_rankings = sorted(
                scores,
                key=lambda x: x.theme_scores.get(theme, {}).get("stage", 0),
                reverse=True
            )
            report["rankings"][theme] = [
                {
                    "company": s.company,
                    "stage": s.theme_scores.get(theme, {}).get("stage", 0)
                }
                for s in theme_rankings[:5]  # Top 5
            ]

        # Save report
        report_file = self.config.reports_dir / f"comparative_report_{datetime.fromisoformat(get_audit_timestamp()).strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Saved comparative report to {report_file}")


def run_pipeline_test():
    """Test the complete pipeline"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize pipeline
    config = PipelineConfig()
    pipeline = ESGScoringPipeline(config)

    # Test with single company
    test_companies = ["Microsoft", "Apple", "Google"]

    scores = []
    for company in test_companies[:1]:  # Start with one
        logger.info(f"\n{'='*60}")
        logger.info(f"Scoring {company}")
        logger.info(f"{'='*60}")

        score = pipeline.score_company(company, year=2023, use_cached_data=True)
        scores.append(score)

        # Print results
        print(f"\n{company} ESG Maturity Score:")
        print(f"  Overall Stage: {score.overall_stage}/4.0")
        print(f"  Confidence: {score.overall_confidence:.0%}")
        print(f"  Evidence Count: {score.evidence_count}")
        print(f"\n  Theme Scores:")
        for theme, theme_score in score.theme_scores.items():
            print(f"    {theme}: Stage {theme_score['stage']} (confidence {theme_score['confidence']:.0%})")

    return scores


if __name__ == "__main__":
    scores = run_pipeline_test()