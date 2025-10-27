# ESG Scoring Application — Comprehensive Naming Conventions & Class Mapping

**Generated**: 2025-10-27  
**Repository**: https://github.com/krump3t/ESG_scoring  
**Protocol**: SCA v13.8-MEA

---

## Table of Contents

1. [Repository Structure Overview](#repository-structure-overview)
2. [Naming Convention Patterns](#naming-convention-patterns)
3. [Core Domain Models](#core-domain-models)
4. [Data Provider Classes](#data-provider-classes)
5. [Extraction Classes](#extraction-classes)
6. [Storage & Data Lake Classes](#storage--data-lake-classes)
7. [Retrieval Classes](#retrieval-classes)
8. [Scoring & Rubric Classes](#scoring--rubric-classes)
9. [API & Service Classes](#api--service-classes)
10. [Contract & Model Classes](#contract--model-classes)
11. [Utility & Infrastructure Classes](#utility--infrastructure-classes)
12. [Configuration & Constants](#configuration--constants)
13. [Test Classes](#test-classes)

---

## Repository Structure Overview

### High-Level Directory Pattern
```
{category}/
  ├── {domain}/
  │   ├── {feature}.py          # Implementation
  │   ├── {feature}_models.py   # Data models
  │   ├── {feature}_contracts.py # Pydantic contracts
  │   └── __init__.py           # Module exports
```

### Directory Categories
- **agents/** - Core agent modules (business logic)
- **apps/** - Application layer (API, pipeline orchestration)
- **libs/** - Shared libraries (storage, retrieval, models)
- **tests/** - Test suite (TDD with @pytest.mark.cp)
- **scripts/** - Operational scripts (QA, ingestion, embeddings)
- **rubrics/** - ESG scoring rubrics (canonical JSON)
- **pipelines/** - Airflow DAGs (optional orchestration)
- **tasks/** - SCA v13.8 task management
  
Key subpackages present:
- `agents/crawler/` (providers, extractors, orchestration)
- `agents/extraction/` (structured/LLM extractors)
- `agents/parser/` (pattern matchers, evidence models)
- `agents/storage/` (bronze/silver writers, DuckDB views)
- `agents/scoring/` (rubric loader/scorer, matchers)
- `apps/api/` (FastAPI app and telemetry)
- `apps/index/` (graph and vector index wiring)
- `apps/ingestion/` (crawler+parser integration and validators)

---

## Naming Convention Patterns

### File Naming
```
Pattern: {domain}_{purpose}.py
Examples:
  - sec_edgar_provider.py         # SEC EDGAR data provider
  - structured_extractor.py       # Structured data extraction
  - bronze_writer.py              # Bronze layer writer
  - rubric_v3_scorer.py          # Rubric v3 scorer
  - watsonx_embedder.py          # Watsonx embedding service
```

### Class Naming
```
Pattern: {Domain}{Purpose}[Suffix]
Suffixes:
  - Provider       # Data source providers
  - Extractor      # Data extraction
  - Writer/Manager # Storage operations
  - Retriever      # Data retrieval
  - Scorer/Matcher # Scoring logic
  - Client         # External service clients
  - Agent          # MCP/orchestration agents

Examples:
  - CDPClimateProvider
  - StructuredExtractor
  - BronzeEvidenceWriter
  - SemanticRetriever
  - RubricScorer
  - WatsonxEmbedder
```

### Contract/Model Naming
```
Pattern: {Entity}[Suffix]
Suffixes:
  - Request/Response  # API contracts
  - Result/Error      # Operation results
  - Quality/Metrics   # Quality assessment
  - Ref/Record        # Data references
  - Config            # Configuration

Examples:
  - ScoreRequest, ScoreResponse
  - ExtractionResult, ExtractionError
  - ExtractionQuality
  - CompanyRef, SourceRef
  - PipelineConfig
```

### Method Naming
```
Pattern: {verb}_{noun}[_qualifier]
Common Verbs:
  - load/save        # I/O operations
  - extract/parse    # Data extraction
  - score/classify   # Scoring/classification
  - search/query     # Retrieval operations
  - validate/verify  # Validation
  - normalize/clean  # Data transformation

Examples:
  - load_rubric()
  - extract_metrics()
  - score_theme()
  - search_company()
  - validate_chunks()
  - normalize_name()
```

### Variable Naming
```
Patterns:
  - snake_case for variables
  - SCREAMING_SNAKE_CASE for constants
  - _private for private methods/attributes
  
Examples:
  - company_name
  - fiscal_year
  - MIN_QUOTES_PER_THEME
  - _calculate_quality()
```

---

## Core Domain Models

### Location: `libs/models/`

#### ESGMetrics (esg_metrics.py)
**Purpose**: Core ESG and financial metrics model  
**Type**: Pydantic BaseModel  
**Parquet-compatible**: Yes

```python
class ESGMetrics(BaseModel):
    # Identifiers
    company_name: str
    cik: Optional[str]
    fiscal_year: int
    fiscal_period: Optional[str]
    report_date: Optional[datetime]
    
    # Financial Metrics (SEC EDGAR)
    assets: Optional[float]
    liabilities: Optional[float]
    stockholders_equity: Optional[float]
    revenues: Optional[float]
    net_income: Optional[float]
    operating_income: Optional[float]
    shares_outstanding: Optional[float]
    
    # Environmental Metrics (Sustainability Reports)
    scope1_emissions: Optional[float]
    scope2_emissions: Optional[float]
    scope3_emissions: Optional[float]
    renewable_energy_pct: Optional[float]
    water_withdrawal: Optional[float]
    waste_recycled_pct: Optional[float]
    
    # Social Metrics
    women_in_workforce_pct: Optional[float]
    employee_turnover_pct: Optional[float]
    
    # Metadata
    extraction_method: Optional[str]
    data_source: Optional[str]
```

**Key Methods**:
- `to_parquet_dict()` - Serialize to Parquet-compatible dict
- `from_parquet_dict()` - Deserialize from Parquet dict

---

## Data Provider Classes

### Location: `agents/crawler/data_providers/`

### Base Provider

#### BaseDataProvider (base_provider.py)
**Purpose**: Abstract base for all data providers  
**Pattern**: ABC with abstract methods

```python
class BaseDataProvider(ABC):
    def __init__(self, source_id: str, rate_limit: float = 1.0)
    
    @abstractmethod
    def search_company(
        self,
        company_name: Optional[str] = None,
        company_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[CompanyReport]
    
    @abstractmethod
    def download_report(
        self,
        report: CompanyReport,
        output_dir: Path
    ) -> Path
    
    @abstractmethod
    def list_available_companies(self) -> List[Dict[str, Any]]
```

#### CompanyReport (base_provider.py)
**Purpose**: Standardized report metadata  
**Type**: @dataclass

```python
@dataclass
class CompanyReport:
    company_name: str
    company_id: Optional[str]
    year: int
    report_type: str  # "sustainability", "climate", "10-k", "esg"
    report_title: str
    download_url: Optional[str]
    file_format: str  # "PDF", "JSON", "HTML", "XML"
    file_size_bytes: Optional[int]
    source: str
    source_metadata: Dict[str, Any]
    date_published: Optional[str]
    date_retrieved: str
```

### Provider Implementations

#### CDPClimateProvider (cdp_provider.py)
**Purpose**: CDP Climate Change API integration  
**Tier**: 1 (highest quality)  
**Coverage**: 13,000+ companies

```python
class CDPClimateProvider(BaseDataProvider):
    BASE_URL = "https://data.cdp.net/api"
    
    def __init__(self):
        super().__init__(source_id="cdp_climate_change", rate_limit=0.1)
```

#### SECEdgarProvider (sec_edgar_provider.py)
**Purpose**: SEC EDGAR API integration  
**Tier**: 1 (highest quality)  
**Coverage**: 10,000+ US companies

```python
class SECEdgarProvider(BaseDataProvider):
    BASE_URL = "https://data.sec.gov"
    USER_AGENT = "ESGScoring/1.0 (email@example.com)"
    
    def __init__(self):
        super().__init__(source_id="sec_edgar", rate_limit=0.1)
    
    def fetch_10k(self, cik: str, year: int) -> Optional[CompanyReport]
    def _normalize_cik(self, cik: str) -> str
```

#### GRIDatabaseProvider (gri_provider.py)
**Purpose**: GRI Sustainability Disclosure Database search (Tier 2)

```python
class GRIDatabaseProvider(BaseDataProvider):
    def search_company(self, company_name: Optional[str], company_id: Optional[str], year: Optional[int]) -> List[CompanyReport]
    def download_report(self, report: CompanyReport, output_path: str) -> bool
    def list_available_companies(self, limit: int = 100) -> List[Dict[str, str]]
```

#### SASBNavigatorProvider (sasb_provider.py)
**Purpose**: SASB industry/issue metadata (Tier 2 guidance)

```python
class SASBNavigatorProvider(BaseDataProvider):
    def search_company(self, company_name: Optional[str], company_id: Optional[str], year: Optional[int]) -> List[CompanyReport]
```

#### TickerLookupProvider (ticker_lookup.py)
**Purpose**: Company name → Ticker/CIK resolution (Tier 2 utility)

```python
class TickerLookupProvider(BaseDataProvider):
    def search_company(self, company_name: Optional[str], company_id: Optional[str], year: Optional[int]) -> List[CompanyReport]
```

#### SECEdgarProviderLegacy (sec_edgar_provider_legacy.py)
**Purpose**: Backwards-compatible legacy SEC provider wrapper

```python
class SECEdgarProviderLegacy(SECEdgarProvider):
    ...
```

#### Exceptions (exceptions.py)
```python
class SECEdgarError(Exception)
class DocumentNotFoundError(SECEdgarError)
class RateLimitExceededError(SECEdgarError)
class InvalidCIKError(SECEdgarError)
class MaxRetriesExceededError(SECEdgarError)
class InvalidResponseError(SECEdgarError)
class RequestTimeoutError(SECEdgarError)
```

#### MultiSourceCrawler (multi_source_crawler.py)
**Purpose**: Multi-provider orchestrator with fallback  
**Tier**: Intelligent 4-tier cascading

```python
class MultiSourceCrawler:
    def __init__(self):
        self.providers: Dict[str, BaseDataProvider] = {}
        self._load_providers()
    
    def search_company_reports(
        self,
        company_name: str,
        year: int,
        us_company: bool = False
    ) -> List[CompanyReport]
    
    def download_best_report(
        self,
        company_name: str,
        year: int,
        us_company: bool = False
    ) -> Optional[Path]
```

##### Crawler Utilities
- `agents/crawler/ledger.py`: IngestLedger
- `agents/crawler/mcp_crawler.py`: MCPTool, MCPCrawlerAgent
- `agents/crawler/multi_source_crawler_v2.py`: MultiSourceCrawler (v2 impl)
- `agents/crawler/sustainability_reports_crawler.py`: CrawlTarget, DownloadedReport, SustainabilityReportsCrawler

---

## Extraction Classes

### Locations
- `agents/extraction/` — structured and LLM extractors, PDF text
- `agents/crawler/extractors/` — PDF-oriented extractors used by crawling flows

#### ExtractionRouter (extraction_router.py)
**Purpose**: Content-type aware routing  
**Coverage**: 100% line, 100% branch

```python
class ExtractionRouter:
    def __init__(self):
        self.structured_extractor = StructuredExtractor()
        self.pdf_extractor = PDFTextExtractor()
    
    def route(self, report: CompanyReport) -> ExtractionResult
    
    def _is_structured(self, report: CompanyReport) -> bool
```

#### StructuredExtractor (structured_extractor.py)
**Purpose**: Extract from structured data (JSON/XBRL)  
**Coverage**: 92.9% line, 90.0% branch  
**Taxonomy**: us-gaap (SEC EDGAR)

```python
class StructuredExtractor:
    US_GAAP_FIELD_MAPPING = {
        "Assets": "assets",
        "Liabilities": "liabilities",
        "StockholdersEquity": "stockholders_equity",
        # ... etc
    }
    
    def __init__(self)
    
    def extract(self, report: CompanyReport) -> ExtractionResult
    
    def _extract_companyfacts(
        self,
        facts_data: Dict[str, Any],
        company: CompanyRef,
        year: int
    ) -> ESGMetrics
    
    def _extract_concept_value(
        self,
        facts: Dict[str, Any],
        concept: str,
        target_year: int
    ) -> Optional[float]
    
    def _calculate_quality(
        self,
        metrics: Optional[ESGMetrics]
    ) -> ExtractionQuality
```

#### LLMExtractor (llm_extractor.py)
**Purpose**: LLM-based extraction for unstructured data  
**Model**: IBM watsonx.ai llama-3-3-70b-instruct

```python
class LLMExtractor:
    def __init__(
        self,
        project_id: str,
        api_key: str,
        model_id: str = "meta-llama/llama-3-3-70b-instruct",
        use_cache: bool = True,
        cache_path: str = "test_data/llm_cache"
    )
    
    def extract(self, report: CompanyReport) -> ExtractionResult
    
    def _construct_prompt(self, text: str) -> str
    
    def _parse_llm_response(
        self,
        response_json: Dict[str, Any],
        report: CompanyReport
    ) -> Optional[ESGMetrics]
    
    def _calculate_quality(
        self,
        metrics: Optional[ESGMetrics]
    ) -> ExtractionQuality
```

#### EnhancedPDFExtractor (agents/crawler/extractors/enhanced_pdf_extractor.py)
**Purpose**: Semantic PDF extraction with segmentation, tables, entities  
**Notes**: Used by crawl/evidence pipelines; deterministic outputs

```python
class EnhancedPDFExtractor:
    def __init__(self) -> None
    def extract(self, pdf_path: str) -> Dict[str, Any]
    def semantic_segment(self, text: str, page_boundaries: List[Tuple[int,int,int]]) -> List[Dict]
    # Additional helpers: extract_tables_as_findings, extract_entities, extract_relationships
```

#### PDFExtractor (agents/crawler/extractors/pdf_extractor.py)
```python
class PDFExtractor:
    def extract_text(self, pdf_path: str) -> str
```

#### PDFTextExtractor (agents/extraction/pdf_text_extractor.py)
```python
class PDFTextExtractor:
    def extract_text(self, pdf_path: str) -> str
```

---

## Storage & Data Lake Classes

### Location: `agents/storage/`, `libs/storage/`

#### BronzeWriter / BronzeEvidenceWriter (bronze_writer.py)
**Purpose**: Immutable append-only bronze layer  
**Format**: Parquet with Hive partitioning  
**Coverage**: 89% line

```python
class BronzeEvidenceWriter:
    def __init__(self, base_path: Path)
    
    def write_evidence_batch(
        self,
        evidence_list: List[Dict[str, Any]],
        org_id: str,
        year: int,
        theme: str
    ) -> Path
    
    def _partition_path(
        self,
        org_id: str,
        year: int,
        theme: str
    ) -> Path
    
    def _generate_manifest(
        self,
        evidence_list: List[Dict[str, Any]],
        output_path: Path
    ) -> Dict[str, Any]
```

#### SilverNormalizer (silver_normalizer.py)
**Purpose**: Deduplication + freshness penalties  
**Coverage**: 78% line

```python
class SilverNormalizer:
    FRESHNESS_PENALTIES = {
        (0, 24): 0.0,    # 0-24 months: no penalty
        (25, 36): -0.1,  # 25-36 months: -0.1
        (37, 48): -0.2,  # 37-48 months: -0.2
        (49, float('inf')): -0.3  # >48 months: -0.3
    }
    
    def __init__(self, bronze_path: Path, silver_path: Path)
    
    def normalize(
        self,
        org_id: str,
        year: int,
        theme: str
    ) -> Path
    
    def _deduplicate_by_hash(
        self,
        evidence_df: pd.DataFrame
    ) -> pd.DataFrame
    
    def _apply_freshness_penalty(
        self,
        evidence_df: pd.DataFrame,
        current_year: int
    ) -> pd.DataFrame
```

#### DuckDBManager (duckdb_manager.py)
**Purpose**: SQL query layer over Parquet  
**Coverage**: 78% line  
**Performance**: <1s query, 60-90% partition pruning

```python
class DuckDBManager:
    def __init__(self, db_path: Path, bronze_path: Path, silver_path: Path)
    
    def create_views(self) -> None
    
    def query_evidence(
        self,
        org_id: str,
        year: int,
        theme: Optional[str] = None
    ) -> pd.DataFrame
    
    def get_evidence_count(
        self,
        org_id: str,
        year: int
    ) -> int
```

#### AstraDBVector (astradb_vector.py)
**Purpose**: AstraDB vector store client  
**Dimensions**: 768 (Slate 125M)  
**Performance**: 150-200ms query latency

```python
class AstraDBVectorStore:
    def __init__(
        self,
        api_endpoint: str,
        token: str,
        keyspace: str,
        collection: str
    )
    
    def upsert(
        self,
        id: str,
        vector: List[float],
        metadata: Dict[str, Any]
    ) -> bool
    
    def knn(
        self,
        query_vector: List[float],
        k: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]
    
    def delete_collection(self) -> None
```

---

## Retrieval Classes

### Location: `libs/retrieval/`

#### SemanticRetriever (semantic_retriever.py)
**Purpose**: Vector similarity search  
**Backend**: AstraDB  
**Coverage**: mypy --strict: 0 errors

```python
class SemanticRetriever:
    def __init__(
        self,
        vector_store: AstraDBVectorStore,
        embedder: WatsonxEmbedder
    )
    
    def retrieve(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]
    
    def _embed_query(self, query: str) -> List[float]
    
    def _rank_by_similarity(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]
```

#### ParquetRetriever (parquet_retriever.py)
**Purpose**: Lexical retrieval from Parquet  
**Coverage**: 83% line  
**Methods**: BM25, TF-IDF

```python
class ParquetRetriever:
    def __init__(self, parquet_path: Path)
    
    def retrieve(
        self,
        query: str,
        k: int = 10,
        method: str = "bm25"  # "bm25" or "tfidf"
    ) -> List[Dict[str, Any]]
    
    def _bm25_score(
        self,
        query_tokens: List[str],
        doc_tokens: List[str],
        corpus_stats: Dict[str, Any]
    ) -> float
    
    def _tfidf_score(
        self,
        query_tokens: List[str],
        doc_tokens: List[str],
        corpus_stats: Dict[str, Any]
    ) -> float
```

#### HybridRetriever (hybrid_retriever.py)
**Purpose**: Fusion of lexical + semantic retrieval  
**Alpha**: Configurable weight (default 0.6)

```python
class HybridRetriever:
    def __init__(
        self,
        semantic_retriever: SemanticRetriever,
        lexical_retriever: ParquetRetriever,
        alpha: float = 0.6  # Weight for semantic scores
    )
    
    def retrieve(
        self,
        query: str,
        k: int = 10
    ) -> List[Dict[str, Any]]
    
    def _fuse_results(
        self,
        semantic_results: List[Dict[str, Any]],
        lexical_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]
    
    def _reciprocal_rank_fusion(
        self,
        semantic_results: List[Dict[str, Any]],
        lexical_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]
```

---

## Scoring & Rubric Classes

### Location: `agents/scoring/`

#### RubricScorer (rubric_scorer.py)
**Purpose**: Evidence-first ESG maturity scoring  
**Version**: Rubric v3.0  
**Coverage**: 95.7% spec compliance

```python
class RubricScorer:
    MIN_QUOTES_PER_THEME = 2
    
    def __init__(self, rubric_path: str = "rubrics/maturity_v3.json")
    
    def score(
        self,
        theme: str,
        evidence: List[Dict[str, Any]],
        org_id: str,
        year: Optional[int] = None,
        snapshot_id: Optional[str] = None
    ) -> Dict[str, Any]
    
    def _load_rubric(self) -> Dict[str, Any]
    
    def _enforce_evidence_gate(
        self,
        theme: str,
        evidence: List[Dict[str, Any]]
    ) -> None
    
    def _calculate_stage(
        self,
        theme: str,
        evidence: List[Dict[str, Any]]
    ) -> int
    
    def _calculate_confidence(
        self,
        theme: str,
        evidence: List[Dict[str, Any]],
        stage: int
    ) -> float
```

#### RubricLoader (rubric_loader.py)
**Purpose**: Load rubric from markdown/JSON

```python
class RubricLoader:
    def __init__(self)
    
    def load_from_markdown(self, rubric_path: Path) -> MaturityRubric
    
    def load_from_cache(self, cache_path: Path) -> MaturityRubric
    
    def cache_rubric(
        self,
        rubric: MaturityRubric,
        cache_path: Path
    ) -> None
    
    def _parse_theme_name(self, line: str) -> Optional[str]
    
    def _parse_stage_number(self, line: str) -> Optional[int]
    
    def _extract_keywords(self, description: str) -> List[str]
```

#### CharacteristicMatcher (characteristic_matcher.py)
**Purpose**: Evidence-theme matching

```python
class CharacteristicMatcher:
    def __init__(self, rubric: MaturityRubric)
    
    def match_evidence_to_theme(
        self,
        evidence: str,
        theme: str
    ) -> float
    
    def _extract_keywords_from_evidence(
        self,
        evidence: str
    ) -> List[str]
    
    def _calculate_match_score(
        self,
        evidence_keywords: List[str],
        theme_keywords: List[str]
    ) -> float
```

#### EvidenceTableGenerator (evidence_table_generator.py)
**Purpose**: Evidence aggregation for reporting

```python
class EvidenceTableGenerator:
    def generate(
        self,
        scores: List[Dict[str, Any]]
    ) -> pd.DataFrame
    
    def export_to_csv(
        self,
        evidence_table: pd.DataFrame,
        output_path: Path
    ) -> None
```

### Rubric Data Models

#### StageCharacteristic (rubric_models.py)
```python
@dataclass(frozen=True)
class StageCharacteristic:
    theme: str
    stage: int
    description: str
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageCharacteristic"
```

#### ThemeRubric (rubric_models.py)
```python
@dataclass
class ThemeRubric:
    theme_name: str
    theme_id: str
    stages: Dict[int, List[StageCharacteristic]]
```

#### MaturityRubric (rubric_models.py)
```python
@dataclass
class MaturityRubric:
    version: str
    themes: List[ThemeRubric]
    metadata: Dict[str, Any]
    
    def to_parquet(self, path: Path) -> None
    
    @classmethod
    def from_parquet(cls, path: Path) -> "MaturityRubric"
```

---

## Retrieval & Indexing Classes

### Locations
- `libs/retrieval/` — retrieval strategies and vector index
- `apps/index/` — higher-level index abstractions for apps

#### Retrieval (libs/retrieval)
```python
class HybridRetriever            # libs/retrieval/hybrid_retriever.py
class ParquetRetriever           # libs/retrieval/parquet_retriever.py
class SemanticRetriever          # libs/retrieval/semantic_retriever.py
class VectorIndex                # libs/retrieval/vector_index.py
class ParityChecker              # libs/retrieval/parity_checker.py

# Embeddings
class DeterministicEmbedder      # libs/retrieval/embeddings/deterministic_embedder.py
class WatsonxEmbedder            # libs/retrieval/embeddings/watsonx_embedder.py

# Vector backends
class AstraDBStore               # libs/retrieval/vector_backends/astradb_store.py
```

#### Index (apps/index)
```python
class GraphStore                 # apps/index/graph_store.py
class HybridRetriever            # apps/index/retriever.py (app-level wrapper)
class VectorStore                # apps/index/vector_store.py

# Ontology
class NodeType(Enum)
class EdgeType(Enum)
class Node
class Edge
```

---

## API & Service Classes

### Location: `apps/api/`

#### FastAPI Application (main.py)
**Purpose**: REST API for ESG scoring  
**Version**: 1.0.0

```python
app = FastAPI(
    title="ESG Scoring API",
    description="Deterministic ESG maturity assessment",
    version="1.0.0"
)

@app.post("/score")
async def score_endpoint(request: ScoreRequest) -> ScoreResponse

@app.get("/health")
async def health_check() -> Dict[str, Any]

@app.get("/ready")
async def readiness_probe() -> Dict[str, bool]

@app.get("/live")
async def liveness_probe() -> Dict[str, bool]

@app.get("/metrics")
async def prometheus_metrics() -> str
```

#### Health Router (health.py)
```python
def create_router() -> APIRouter:
    router = APIRouter(prefix="", tags=["health"])
    
    @router.get("/health")
    async def health() -> HealthResponse
    
    @router.get("/ready")
    async def ready() -> ReadinessResponse
    
    @router.get("/live")
    async def live() -> LivenessResponse
    
    return router
```

#### Metrics (metrics.py)
**Purpose**: Prometheus metrics exposition

```python
# Counters
esg_api_requests_total = Counter(
    "esg_api_requests_total",
    "Total API requests",
    ["route", "method", "status"]
)

# Histograms
score_latency_seconds = Histogram(
    "esg_score_latency_seconds",
    "Scoring latency in seconds"
)

# Gauges
active_connections = Gauge(
    "esg_active_connections",
    "Active API connections"
)
```

### Pipeline Orchestration

#### ESGScoringPipeline (pipeline.py)
```python
class ESGScoringPipeline:
    def __init__(self, config: Optional[PipelineConfig] = None)
    
    def score_company(
        self,
        company: str,
        year: int
    ) -> CompanyScore
    
    def _ingest_reports(
        self,
        company: str,
        year: int
    ) -> List[ReportRef]
    
    def _parse_reports(
        self,
        reports: List[ReportRef]
    ) -> List[Chunk]
    
    def _retrieve_evidence(
        self,
        query: str,
        chunks: List[Chunk]
    ) -> List[Dict[str, Any]]
    
    def _score_themes(
        self,
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]
```

#### PipelineConfig (pipeline.py)
```python
@dataclass
class PipelineConfig:
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
```

---

## Contract & Model Classes

### Location: `libs/contracts/`

#### Extraction Contracts (extraction_contracts.py)

```python
@dataclass(frozen=True)
class ExtractionQuality:
    field_completeness: float  # [0.0, 1.0]
    type_correctness: float    # [0.0, 1.0]
    value_validity: float      # [0.0, 1.0]
    
    def overall_score(self) -> float

@dataclass(frozen=True)
class ExtractionError:
    field_name: Optional[str]
    error_type: str
    message: str
    severity: str  # "warning" or "error"

@dataclass(frozen=True)
class ExtractionResult:
    metrics: Optional[ESGMetrics]
    quality: ExtractionQuality
    errors: List[ExtractionError]
    
    def is_success(self) -> bool
```

#### Ingestion Contracts (ingestion_contracts.py)

```python
class CompanyRef(BaseModel):
    cik: Optional[str] = Field(
        None,
        pattern=r"^\d{10}$",
        description="SEC Central Index Key"
    )
    name: str = Field(..., min_length=1)
    ticker: Optional[str] = None

class SourceRef(BaseModel):
    provider: str
    tier: int = Field(..., ge=1, le=3)
    url: Optional[HttpUrl] = None
    access: Literal["api", "scrape", "file"] = "api"
    content_type: str
    priority_score: int = Field(100, ge=0, le=100)

class CompanyReport(BaseModel):
    company: CompanyRef
    year: int
    report_type: str
    local_path: Optional[Path] = None
    download_url: Optional[str] = None
    sha256: Optional[str] = None
    file_size_bytes: Optional[int] = None
    source_ref: SourceRef
    retrieved_at: datetime
```

#### Naming Collision: ExtractionResult

Two distinct types named `ExtractionResult` exist and serve different purposes:
- `libs/contracts/extraction_contracts.py:72` — Pydantic/dataclass hybrid contract holding `metrics: ESGMetrics`, `quality: ExtractionQuality`, and `errors` for metric extraction flows.
- `agents/parser/models.py:126` — Dataclass for evidence extraction results with `evidence_by_theme`, `snapshot_id`, and summary helpers.

Canonicalization guidance:
- Prefer `MetricsExtractionResult` for the contracts type during future refactors.
- Prefer `EvidenceExtractionResult` for the parser type during future refactors.
- Until refactor, always import with explicit module path to avoid ambiguity:
  - `from libs.contracts.extraction_contracts import ExtractionResult as MetricsExtractionResult`
  - `from agents.parser.models import ExtractionResult as EvidenceExtractionResult`

### API Request/Response Models

```python
class ScoreRequest(BaseModel):
    company: str = Field(..., min_length=1)
    year: Optional[int] = Field(None, ge=2000, le=2100)
    query: str = Field(..., min_length=1)

class Evidence(BaseModel):
    quote: str
    page: Optional[int] = None

class DimensionScore(BaseModel):
    theme: str
    stage: int = Field(..., ge=0, le=4)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[Evidence] = Field(default_factory=list)

class ScoreResponse(BaseModel):
    trace_id: str
    company: str
    year: int
    query: str
    scores: List[DimensionScore]
    overall_stage: float
    overall_confidence: float
    processing_time_ms: float
    model_version: str
    rubric_version: str
```

---

## Utility & Infrastructure Classes

### Location: `libs/embedding/`, `libs/llm/`, `libs/utils/`

#### WatsonxEmbedder (watsonx_embedder.py)
**Purpose**: IBM watsonx.ai Slate embedder  
**Model**: slate-125m-english-rtrvr  
**Dimensions**: 768

```python
class WatsonxEmbedder:
    MODEL_ID = "ibm/slate-125m-english-rtrvr"
    DIMENSIONS = 768
    
    def __init__(
        self,
        api_key: str,
        project_id: str,
        url: str = "https://us-south.ml.cloud.ibm.com"
    )
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 5
    ) -> List[List[float]]
    
    def embed_single(self, text: str) -> List[float]
```

#### WatsonxClient (watsonx_client.py)
**Purpose**: IBM watsonx.ai LLM client  
**Model**: Granite 13B

```python
class WatsonXClient:
    def __init__(
        self,
        api_key: str,
        project_id: str,
        model_id: str = "granite-13b-instruct"
    )
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.0
    ) -> str
    
    def generate_json(
        self,
        prompt: str,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]
```

#### Trace Utilities (trace.py)
```python
def generate_trace_id(
    company: str,
    year: int,
    query: str,
    seed: int = 42
) -> str:
    """Generate deterministic SHA256 trace ID."""
    payload = f"{company}:{year}:{query}:{seed}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]

def generate_snapshot_id() -> str:
    """Generate UUID snapshot ID."""
    return str(uuid.uuid4())
```

### Batch Processing

#### BatchProcessor (batch_processor.py)
```python
class BatchProcessor:
    def __init__(
        self,
        bronze_path: Path,
        silver_path: Path,
        db_path: Path,
        cache_path: Path
    )
    
    def process_companies(
        self,
        companies: List[Tuple[str, int]]
    ) -> BatchProcessingResult
    
    def process_single_company(
        self,
        ticker: str,
        year: int
    ) -> CompanyProcessingResult

@dataclass
class CompanyProcessingResult:
    ticker: str
    year: int
    success: bool
    evidence_count: int
    processing_time_seconds: float
    error_message: Optional[str] = None

@dataclass
class BatchProcessingResult:
    batch_id: str
    total_companies: int
    successful_companies: int
    failed_companies: int
    total_evidence_extracted: int
    processing_time_seconds: float
    company_results: List[CompanyProcessingResult]
```

---

## Configuration & Constants

### Environment Variables
```
# IBM watsonx.ai
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
WATSONX_REGION=us-south
WATSONX_MODEL_ID=granite-13b-instruct

# AstraDB
ASTRA_DB_API_ENDPOINT=
ASTRA_DB_TOKEN=
ASTRA_DB_KEYSPACE=esg

# Determinism
SEED=42
PYTHONHASHSEED=0
AUDIT_TIME=2025-01-01T00:00:00Z  # Optional: override timestamps
```

### Data Source Registry (configs/data_source_registry.json)
```json
{
  "registry_version": "1.0.0",
  "last_updated": "YYYY-MM-DD",
  "description": "Verified public data sources for ESG/sustainability reports with API access",
  "data_sources": [
    {
      "source_id": "cdp_climate_change",
      "name": "CDP Climate Change Responses",
      "type": "api",
      "priority": 1,
      "api_endpoint": "https://data.cdp.net/api/odata/v4",
      "base_url": "https://data.cdp.net"
    },
    {
      "source_id": "sec_edgar",
      "name": "SEC EDGAR - 10-K Risk Factors",
      "type": "api",
      "priority": 2,
      "api_endpoint": "https://data.sec.gov/submissions",
      "base_url": "https://www.sec.gov"
    }
  ]
}
```

### Rubric Schema (esg_rubric_schema_v3.json)
```json
{
  "version": "3.0",
  "themes": [
    {
      "code": "TSP",
      "name": "Target Setting & Planning",
      "intent": "...",
      "stages": {
        "0": {"label": "...", "descriptor": "..."},
        "1": {"label": "...", "descriptor": "..."},
        "2": {"label": "...", "descriptor": "..."},
        "3": {"label": "...", "descriptor": "..."},
        "4": {"label": "...", "descriptor": "..."}
      }
    }
  ],
  "scoring_rules": {
    "evidence_min_per_stage_claim": 2,
    "freshness_months_penalty": {...},
    "negative_overrides": [...]
  }
}
```

---

## Test Classes

### Location: `tests/`

### Test File Naming
```
Pattern: test_{module}_[qualifier]_cp.py
Examples:
  - test_structured_extractor_cp.py
  - test_bronze_writer_cp.py
  - test_semantic_retriever_cp.py
  - test_score_api_cp.py
```

### Test Class Naming
```
Pattern: Test{Feature}[Qualifier]
Examples:
  - TestStructuredExtractor
  - TestBronzeWriter
  - TestSemanticRetriever
  - TestScoreAPISemanticToggle
```

### Common Test Fixtures (conftest.py)
```python
@pytest.fixture
def sample_company_report() -> CompanyReport:
    """Sample company report for testing."""
    return CompanyReport(...)

@pytest.fixture
def mock_vector_store() -> AstraDBVectorStore:
    """Mock AstraDB vector store."""
    return Mock(spec=AstraDBVectorStore)

@pytest.fixture
def temp_bronze_path(tmp_path: Path) -> Path:
    """Temporary bronze layer path."""
    bronze = tmp_path / "bronze"
    bronze.mkdir(parents=True)
    return bronze

@pytest.fixture(scope="session")
def integration_flags() -> Dict[str, bool]:
    """Integration flags for testing."""
    return {
        "semantic_enabled": False,
        "watsonx_enabled": False,
        "astradb_enabled": False
    }
```

### Test Markers
```python
# Critical Path tests (must pass for SCA compliance)
@pytest.mark.cp

# Integration tests
@pytest.mark.integration

# End-to-end tests
@pytest.mark.e2e

# Slow tests
@pytest.mark.slow

# Requires external API
@pytest.mark.requires_api

# Property-based tests
@pytest.mark.hypothesis
@pytest.mark.property

# Cloud tests
@pytest.mark.cloud

# Phase-specific tests
@pytest.mark.phase3
@pytest.mark.phase5
@pytest.mark.phase6b
```

---

## Authenticity & Quality Assurance

### Authenticity Audit (scripts/qa/authenticity_audit.py)

#### AuthenticityAuditor
```python
class AuthenticityAuditor:
    def __init__(
        self,
        root_path: Path,
        exempt_paths: List[str] = None
    )
    
    def audit(self) -> AuditReport
    
    def _detect_unseeded_random(self, file_path: Path) -> List[Violation]
    
    def _detect_nondeterministic_time(self, file_path: Path) -> List[Violation]
    
    def _detect_network_imports(self, file_path: Path) -> List[Violation]
    
    def _detect_eval_exec(self, file_path: Path) -> List[Violation]
    
    def _detect_workspace_escape(self, file_path: Path) -> List[Violation]
    
    def _detect_silent_exceptions(self, file_path: Path) -> List[Violation]
    
    def _detect_json_as_parquet(self, file_path: Path) -> List[Violation]
    
    def _detect_nondeterministic_ordering(self, file_path: Path) -> List[Violation]

@dataclass
class Violation:
    file_path: str
    line_number: int
    detector: str
    severity: str  # "FATAL" or "WARN"
    message: str
    code_snippet: str

@dataclass
class AuditReport:
    violations: List[Violation]
    fatal_count: int
    warning_count: int
    determinism_status: str
    timestamp: str
```

### Test Coverage Gates
- **Critical Path**: ≥95% line & branch coverage
- **Type Safety**: mypy --strict = 0 errors
- **Complexity**: Lizard CCN ≤10, Cognitive ≤15
- **Documentation**: ≥95% docstring coverage
- **Security**: detect-secrets clean, bandit no findings

---

## Key Design Patterns

### 1. Provider Pattern (Data Sources)
```
BaseDataProvider (ABC)
├── CDPClimateProvider
├── SECEdgarProvider
├── GRIProvider
└── SASBProvider
```

### 2. Strategy Pattern (Extraction)
```
ExtractionRouter
├── StructuredExtractor (JSON/XBRL)
├── LLMExtractor (Unstructured via LLM)
└── EnhancedPDFExtractor (PDF with NLP)
```

### 3. Repository Pattern (Storage)
```
Storage Layer
├── BronzeWriter (append-only)
├── SilverNormalizer (deduplication)
└── DuckDBManager (query)
```

### 4. Facade Pattern (Retrieval)
```
HybridRetriever
├── SemanticRetriever (vector search)
└── ParquetRetriever (lexical search)
```

### 5. Data Transfer Objects
- Request/Response models (API)
- Contract models (Pydantic)
- Result/Error models (operations)

---

## Module Import Patterns

### Absolute Imports (Preferred)
```python
from agents.extraction.structured_extractor import StructuredExtractor
from libs.models.esg_metrics import ESGMetrics
from libs.contracts.extraction_contracts import ExtractionResult
from apps.api.main import app
```

### Relative Imports (Within Package)
```python
from .base_provider import BaseDataProvider, CompanyReport
from .rubric_models import ThemeRubric, StageCharacteristic
```

### Optional Imports (Graceful Degradation)
```python
try:
    from .cdp_provider import CDPClimateProvider
    __all__.append('CDPClimateProvider')
except ImportError as e:
    logger.warning(f"CDPClimateProvider not available: {e}")
```

---

## Parquet Schema Patterns

### Evidence Schema
```python
evidence_schema = pa.schema([
    ("evidence_id", pa.string()),
    ("org_id", pa.string()),
    ("year", pa.int32()),
    ("theme", pa.string()),
    ("doc_id", pa.string()),
    ("page_no", pa.int32()),
    ("quote", pa.string()),
    ("confidence", pa.float64()),
    ("hash_sha256", pa.string()),
    ("snapshot_id", pa.string()),
    ("retrieved_at", pa.timestamp("us", tz="UTC"))
])
```

### Hive Partitioning
```
data/bronze/
  org_id=AAPL/
    year=2024/
      theme=GHG/
        evidence_20241027_123456.parquet
```

---

## Logging & Observability

### Structured Logging
```python
import structlog

logger = structlog.get_logger(__name__)

logger.info(
    "evidence_extraction_complete",
    org_id="AAPL",
    year=2024,
    theme="GHG",
    evidence_count=42,
    processing_time_ms=123.45
)
```

### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Counters
requests_total = Counter(
    "esg_requests_total",
    "Total requests",
    ["endpoint", "status"]
)

# Histograms
latency_seconds = Histogram(
    "esg_latency_seconds",
    "Request latency"
)

# Gauges
active_jobs = Gauge(
    "esg_active_jobs",
    "Active processing jobs"
)
```

---

## Rename & Import Mapping Guidance

- Duplicate names
  - `ExtractionResult` appears in two modules. Prefer explicit, canonical names and assignment aliases at the module boundary.
    - Canonical names: `MetricsExtractionResult` (contracts), `EvidenceExtractionResult` (parser)
    - Import usage in code:
      - `from libs.contracts.extraction_contracts import MetricsExtractionResult`
      - `from agents.parser.models import EvidenceExtractionResult`
    - Module‑level legacy aliasing (TypeAlias) with import‑time deprecation warning is preferred over subclassing.
      - Example (contracts):
        - `from typing import TypeAlias`
        - `import warnings as _w; _w.warn("...ExtractionResult is deprecated...", DeprecationWarning, stacklevel=2)`
        - `ExtractionResult: TypeAlias = MetricsExtractionResult`
- Canonical imports (golden paths)
  - Providers: `from agents.crawler.data_providers.sec_edgar_provider import SECEdgarProvider`
  - Extractors: `from agents.extraction.structured_extractor import StructuredExtractor`
  - Storage: `from agents.storage.bronze_writer import BronzeEvidenceWriter`
  - Retrieval (library): `from libs.retrieval.hybrid_retriever import HybridRetriever`
  - Retrieval (app layer): prefer namespacing by module path `from apps.index.retriever import HybridRetriever`; if two variants are required, use a capability suffix, e.g., `IndexedHybridRetriever` for the app layer.
  - Models: `from libs.models.esg_metrics import ESGMetrics`
- Suggested future renames (non-breaking plan)
  - `agents/parser/models.ExtractionResult` → `EvidenceExtractionResult`
  - `libs/contracts/extraction_contracts.ExtractionResult` → `MetricsExtractionResult`
  - `apps/scoring/rubric_v3_loader.ThemeRubric` → `ThemeRubricV3`
  - For app retriever variant, prefer `IndexedHybridRetriever` rather than prefixing with `App`.

Regeneration script (developer tooling)
- To refresh the symbol index locally, run this snippet and paste results:
```
python3 - << 'PY'
import os, ast
from pathlib import Path
IGNORE={'.venv','.git','.benchmarks','.mypy_cache','.pytest_cache','.hypothesis','tests'}
out=[]
for dp,_,fns in os.walk('.'):
  if any(p in IGNORE for p in Path(dp).parts):
    continue
  for fn in fns:
    if not fn.endswith('.py'): continue
    p=Path(dp)/fn
    try:
      tree=ast.parse(p.read_text(encoding='utf-8',errors='ignore'))
    except Exception: continue
    classes=[n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    if classes:
      out.append((str(p).replace('\\','/'), classes))
for mod, cls in sorted(out):
  print(f"- {mod}: {', '.join(cls)}")
PY
```

---

## Golden Import Paths

- Public modules should re‑export canonical symbols to support stable imports. Prefer these in docs and internal code:
  - `libs.contracts`: MetricsExtractionResult
  - `agents.parser`: EvidenceExtractionResult
  - `libs.retrieval`: HybridRetriever (library)
  - `apps.index`: HybridRetriever or IndexedHybridRetriever (app layer)
  - `agents.storage`: BronzeEvidenceWriter, SilverNormalizer, DuckDBManager
  - `agents.scoring`: RubricLoader, RubricV3Scorer

Add a small test to import all public symbols only via these golden paths to prevent accidental deep imports.

---

## Deprecation Policy

- Legacy names are supported for one minor release or 4 weeks, whichever is longer.
- Deprecation warnings are emitted at import time, once per process, for legacy names.
- Internal code paths should not import deprecated names; CI treats DeprecationWarning as error internally.
- After the compatibility window, remove the aliases and update this document.
 - After Phase 3 lands, importing legacy names raises ImportError to remove ambiguity.

### Legacy → Canonical Map (for integrators)

- libs.contracts.extraction_contracts
  - Legacy: `ExtractionResult` → Canonical: `MetricsExtractionResult`
- agents.parser.models
  - Legacy: `ExtractionResult` → Canonical: `EvidenceExtractionResult`
- apps.scoring.rubric_v3_loader
  - Legacy: `ThemeRubric` → Canonical: `ThemeRubricV3`
- apps.index.retriever
  - Prefer module‑scoped `HybridRetriever` (golden path). If a distinct app variant exists during transition: Legacy `HybridRetriever` → Canonical `IndexedHybridRetriever` (capability suffix)

All docs and examples should use canonical names from Day 1 (P1).

## Symbol Index (By Module)

- agents/crawler/data_providers
  - Classes: CompanyReport, BaseDataProvider, CDPClimateProvider, GRIDatabaseProvider, SASBNavigatorProvider, SECEdgarProvider, SECEdgarProviderLegacy, TickerLookupProvider
  - Exceptions: SECEdgarError, DocumentNotFoundError, RateLimitExceededError, InvalidCIKError, MaxRetriesExceededError, InvalidResponseError, RequestTimeoutError
- agents/crawler
  - Classes: IngestLedger, MCPTool, MCPCrawlerAgent, MultiSourceCrawler, MultiSourceCrawler (v2), CrawlTarget, DownloadedReport, SustainabilityReportsCrawler
- agents/crawler/extractors
  - Classes: EnhancedPDFExtractor, PDFExtractor
- agents/extraction
  - Classes: ExtractionRouter, LLMExtractor, PDFTextExtractor, StructuredExtractor
- agents/storage
  - Classes: BronzeEvidenceWriter, DuckDBManager, SilverNormalizer
- agents/scoring
  - Classes: MatchResult, CharacteristicMatcher, EvidenceRow, EvidenceTableGenerator, MCPScoringAgent, RubricLoader, StageCharacteristic, ThemeRubric, MaturityRubric, RubricScorer, DimensionScore, RubricV3Scorer
- apps/api
  - Classes: CustomJsonFormatter, ScoreRequest, Evidence, DimensionScore, ScoreResponse, TraceRequest, QuoteRecord, TraceResponse
- apps/scoring
  - Classes: PipelineConfig, CompanyScore, ESGScoringPipeline, StageDescriptor, ThemeRubric, RubricV3Loader, ScoringResult
- apps/index
  - Classes: GraphStore, NodeType, EdgeType, Node, Edge, HybridRetriever, VectorStore
- apps/ingestion
  - Classes: ReportRef, SustainabilityReportsCrawler, Chunk, PDFParser, SustainabilityReportFetcher, ValidationResult, LineageRecord, ChunkValidator, DataLineageTracker
- libs/contracts
  - Classes: ExtractionQuality, ExtractionError, ExtractionResult, CompanyRef, SourceRef, CompanyReport
- libs/models
  - Classes: ESGMetrics
- libs/retrieval
  - Classes: RetrievalResult, HybridRetriever, ParquetRetriever, SemanticRetriever, VectorIndex, ParityChecker
  - Embeddings: DeterministicEmbedder, WatsonxEmbedder
  - Vector backends: AstraDBStore
- libs/ranking
  - Classes: CrossEncoderRanker, RankedDocument, CrossEncoderRanker (real), TFIDFScorer, BM25Scorer, RealCrossEncoderRanker
- libs/storage
  - Classes: GraphNode, GraphEdge, AstraDBGraphStore, AstraDBConfig, AstraDBVectorStore
- libs/llm
  - Classes: WatsonXConfig, WatsonXClient, ImprovedWatsonXClient
- libs/embedding
  - Classes: EmbeddingConfig, DeterministicEmbedder, WatsonXEmbedder
- libs/utils
  - Classes: Clock, HTTPResponse, HTTPClient, RealHTTPClient, MockHTTPClient, Tee
- libs/query
  - Classes: CompanyQuery, MultiCompanyQuery, QuerySynthesizer
- libs/analytics
  - Modules: duck.py, prefilter.py (functional utilities)

Notes:
- This index lists symbol names present in the working tree, excluding tests and virtual environment files.
- For renames, use the Canonicalization guidance in this document and update imports consistently.

---

## Summary

This comprehensive mapping covers:

✅ **100+ Classes** across all modules  
✅ **File & Class Naming Patterns**  
✅ **Method Naming Conventions**  
✅ **Data Models & Contracts**  
✅ **API Endpoints & Routes**  
✅ **Storage & Retrieval Patterns**  
✅ **Test Structures & Fixtures**  
✅ **Configuration & Constants**  
✅ **Design Patterns & Best Practices**

**Key Takeaways**:
1. **Consistent Naming**: {Domain}{Purpose}{Suffix} pattern throughout
2. **Type Safety**: 100% Pydantic models, mypy --strict compliance
3. **Modularity**: Clear separation of concerns (agents/apps/libs)
4. **Testability**: TDD with @pytest.mark.cp, ≥95% coverage
5. **Determinism**: SEED=42, SHA256 hashing, fixed ordering
6. **Authenticity**: No mocks in production, REAL data validation

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-27  
**Maintainer**: ESG Scoring Team  
**Repository**: https://github.com/krump3t/ESG_scoring
