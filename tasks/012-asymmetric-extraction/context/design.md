# Phase 3 Design - Asymmetric Extraction Paths

**Task ID**: 012-asymmetric-extraction
**SCA Version**: v13.8-MEA
**Phase**: Context Gate
**Date**: 2025-10-24

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 3: Asymmetric Extraction                │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  ExtractionRouter       │
                    │  • route_by_content()   │
                    │  • extract()            │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Content-Type Check    │
                    │   (SourceRef)           │
                    └─────┬──────────────┬────┘
                          │              │
         ┌────────────────▼────┐    ┌───▼──────────────────┐
         │ StructuredExtractor │    │   LLMExtractor       │
         │ (JSON/XBRL)         │    │   (PDF/HTML)         │
         │                     │    │                      │
         │ • Pydantic parsing  │    │ • PyMuPDF text      │
         │ • Field mapping     │    │ • LLM prompt        │
         │ • Type validation   │    │ • Response parsing  │
         └─────────┬───────────┘    └───────┬──────────────┘
                   │                        │
                   └────────┬───────────────┘
                            │
                  ┌─────────▼──────────┐
                  │   ESGMetrics       │
                  │   (Pydantic Model) │
                  │                    │
                  │ • company_name     │
                  │ • fiscal_year      │
                  │ • scope1_emissions │
                  │ • scope2_emissions │
                  │ • scope3_emissions │
                  │ • governance_score │
                  │ • ...              │
                  └──────────┬─────────┘
                             │
                   ┌─────────▼──────────┐
                   │  Parquet Writer    │
                   │  (PyArrow)         │
                   │                    │
                   │ • Schema mapping   │
                   │ • Type conversion  │
                   │ • File write       │
                   └────────────────────┘
```

---

## Component Specifications

### 1. ExtractionRouter (CP-1)

**Purpose**: Routes CompanyReport to appropriate extractor based on SourceRef.content_type

**Interface**:
```python
class ExtractionRouter:
    """Routes extraction based on content type (asymmetric paths)."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize router with optional LLM client for PDF/HTML extraction."""
        self.structured_extractor = StructuredExtractor()
        self.llm_extractor = LLMExtractor(llm_client) if llm_client else None

    def extract(self, report: CompanyReport) -> ExtractionResult:
        """Extract ESG metrics from report using content-type-specific extractor.

        Args:
            report: CompanyReport from Phase 2 crawler

        Returns:
            ExtractionResult with ESGMetrics and quality metadata

        Raises:
            ValueError: If content_type unsupported or extractor unavailable
        """
        content_type = report.source.content_type

        if content_type in ["application/json", "application/vnd.xbrl"]:
            return self.structured_extractor.extract(report)
        elif content_type in ["application/pdf", "text/html"]:
            if not self.llm_extractor:
                raise ValueError("LLM extractor not configured for PDF/HTML")
            return self.llm_extractor.extract(report)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
```

**Routing Logic**:
- `application/json` → StructuredExtractor (SEC EDGAR JSON facts)
- `application/vnd.xbrl` → StructuredExtractor (XBRL XML parsed as JSON)
- `application/pdf` → LLMExtractor (Sustainability reports)
- `text/html` → LLMExtractor (Company IR pages)

**Complexity**: CCN ≤5 (simple if/elif routing)

---

### 2. StructuredExtractor (CP-2)

**Purpose**: Extract ESG metrics from structured data (JSON/XBRL) using Pydantic parsing

**Interface**:
```python
class StructuredExtractor:
    """Extracts ESG metrics from structured data (JSON/XBRL)."""

    def extract(self, report: CompanyReport) -> ExtractionResult:
        """Parse structured data into ESGMetrics Pydantic model.

        Args:
            report: CompanyReport with local_path to JSON/XBRL file

        Returns:
            ExtractionResult with:
              - metrics: ESGMetrics instance
              - quality: ExtractionQuality with field completeness metrics
              - errors: List of field-level errors (if any)

        Raises:
            ValueError: If file not found or JSON parse error
        """
        # Read JSON from report.local_path
        with open(report.local_path, 'r') as f:
            data = json.load(f)

        # Map JSON fields to ESGMetrics
        try:
            metrics = ESGMetrics(
                company_name=report.company.name,
                fiscal_year=report.year,
                scope1_emissions=data.get("emissions", {}).get("scope1"),
                scope2_emissions=data.get("emissions", {}).get("scope2"),
                scope3_emissions=data.get("emissions", {}).get("scope3"),
                # ... map all fields
            )
            quality = self._assess_quality(metrics)
            return ExtractionResult(metrics=metrics, quality=quality, errors=[])
        except ValidationError as e:
            # Pydantic validation failed - return partial metrics with errors
            return ExtractionResult(
                metrics=None,
                quality=ExtractionQuality(field_completeness=0.0, type_correctness=0.0),
                errors=[str(err) for err in e.errors()]
            )

    def _assess_quality(self, metrics: ESGMetrics) -> ExtractionQuality:
        """Calculate quality metrics for extracted data."""
        total_fields = len(metrics.__fields__)
        populated_fields = sum(1 for f in metrics.__dict__.values() if f is not None)

        return ExtractionQuality(
            field_completeness=populated_fields / total_fields,
            type_correctness=1.0,  # Pydantic guarantees type correctness
            value_validity=self._check_value_ranges(metrics)
        )
```

**Field Mapping Strategy**:
- Use JSON path expressions (e.g., `data["emissions"]["scope1"]`)
- Graceful None handling for missing fields (Optional[float] in ESGMetrics)
- Pydantic validators ensure type correctness

**Error Handling**:
- JSONDecodeError → ExtractionResult with errors list
- ValidationError → Partial metrics + field-level errors
- FileNotFoundError → Raise ValueError (caller handles)

**Complexity**: CCN ≤8

---

### 3. LLMExtractor (CP-3)

**Purpose**: Extract ESG metrics from unstructured data (PDF/HTML) using LLM

**Interface**:
```python
class LLMExtractor:
    """Extracts ESG metrics from unstructured data using IBM watsonx.ai."""

    def __init__(self, watsonx_client: WatsonxClient):
        """Initialize with IBM watsonx.ai client.

        Args:
            watsonx_client: Configured WatsonxClient with project_id and IAM authentication
        """
        self.watsonx_client = watsonx_client
        self.prompt_template = self._load_extraction_prompt()
        self.model_id = "ibm/granite-13b-chat-v2"  # or "meta-llama/llama-2-70b-chat"

    def extract(self, report: CompanyReport) -> ExtractionResult:
        """Extract ESG metrics from PDF/HTML using LLM.

        Workflow:
        1. Extract text from PDF using PyMuPDF (or HTML using BeautifulSoup)
        2. Construct LLM prompt with text + JSON schema
        3. Call LLM API with retry logic
        4. Parse LLM response into ESGMetrics
        5. Assess extraction quality

        Args:
            report: CompanyReport with local_path to PDF/HTML

        Returns:
            ExtractionResult with metrics and quality assessment
        """
        # Step 1: Extract text
        text = self._extract_text(report.local_path, report.source.content_type)

        # Step 2: Construct prompt
        prompt = self.prompt_template.format(
            company_name=report.company.name,
            fiscal_year=report.year,
            document_text=text[:10000]  # Truncate to avoid token limits
        )

        # Step 3: Call watsonx.ai with retry
        try:
            response = self._call_watsonx_with_retry(prompt, max_retries=3)
        except WatsonxAPIError as e:
            return ExtractionResult(
                metrics=None,
                quality=ExtractionQuality(field_completeness=0.0),
                errors=[f"LLM API error: {e}"]
            )

        # Step 4: Parse response
        try:
            metrics_dict = json.loads(response)
            metrics = ESGMetrics(**metrics_dict)
        except (JSONDecodeError, ValidationError) as e:
            return ExtractionResult(
                metrics=None,
                quality=ExtractionQuality(field_completeness=0.0),
                errors=[f"LLM response parse error: {e}"]
            )

        # Step 5: Assess quality
        quality = self._assess_llm_quality(metrics, text)
        return ExtractionResult(metrics=metrics, quality=quality, errors=[])

    def _extract_text(self, file_path: str, content_type: str) -> str:
        """Extract text from PDF or HTML."""
        if content_type == "application/pdf":
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            return "\n".join(page.get_text() for page in doc)
        elif content_type == "text/html":
            from bs4 import BeautifulSoup
            with open(file_path, 'r') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            return soup.get_text()
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    def _call_watsonx_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Call IBM watsonx.ai API with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                response = self.watsonx_client.generate(
                    model_id=self.model_id,
                    prompt=prompt,
                    parameters={
                        "decoding_method": "greedy",  # Deterministic (no sampling)
                        "max_new_tokens": 2000,
                        "min_new_tokens": 1,
                        "temperature": 0.0,  # Deterministic
                        "repetition_penalty": 1.0
                    }
                )
                return response.results[0].generated_text
            except WatsonxAPIError as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
```

**LLM Prompt Template**:
```
You are an ESG data extraction assistant. Extract the following metrics from the sustainability report for {company_name} (fiscal year {fiscal_year}):

Required fields (return JSON):
- scope1_emissions: GHG Scope 1 emissions in metric tons CO2e (float or null)
- scope2_emissions: GHG Scope 2 emissions in metric tons CO2e (float or null)
- scope3_emissions: GHG Scope 3 emissions in metric tons CO2e (float or null)
- governance_score: Board independence score 0-100 (int or null)
- diversity_score: Workforce diversity score 0-100 (int or null)

Document text:
{document_text}

Respond with ONLY valid JSON matching this schema. Use null for missing values.
```

**Complexity**: CCN ≤10 (retry logic, error handling, multi-format support)

---

### 4. ESGMetrics (CP-4)

**Purpose**: Pydantic model for ESG metrics with Parquet schema compatibility

**Schema**:
```python
class ESGMetrics(BaseModel):
    """ESG metrics extracted from company reports (Parquet-compatible)."""

    # Identifiers
    company_name: str = Field(..., description="Company name")
    fiscal_year: int = Field(..., ge=2000, le=2030, description="Fiscal year")
    report_date: Optional[datetime] = Field(None, description="Report publication date")

    # GHG Emissions (Scope 1, 2, 3)
    scope1_emissions: Optional[float] = Field(None, ge=0, description="Scope 1 GHG emissions (metric tons CO2e)")
    scope2_emissions: Optional[float] = Field(None, ge=0, description="Scope 2 GHG emissions (metric tons CO2e)")
    scope3_emissions: Optional[float] = Field(None, ge=0, description="Scope 3 GHG emissions (metric tons CO2e)")

    # Governance Metrics
    governance_score: Optional[int] = Field(None, ge=0, le=100, description="Board independence score")
    diversity_score: Optional[int] = Field(None, ge=0, le=100, description="Workforce diversity score")

    # Social Metrics
    employee_count: Optional[int] = Field(None, ge=0, description="Total employees")
    safety_incidents: Optional[int] = Field(None, ge=0, description="Workplace safety incidents")

    # Environmental Metrics
    water_consumption: Optional[float] = Field(None, ge=0, description="Water consumption (cubic meters)")
    waste_generated: Optional[float] = Field(None, ge=0, description="Waste generated (metric tons)")
    renewable_energy_pct: Optional[float] = Field(None, ge=0, le=100, description="% energy from renewables")

    # Metadata
    extraction_method: str = Field("unknown", description="structured or llm")
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic config for Parquet compatibility."""
        # Frozen for immutability
        frozen = True
        # Allow arbitrary types for datetime
        arbitrary_types_allowed = True

    def to_parquet_dict(self) -> dict:
        """Convert to Parquet-compatible dict (datetimes → strings)."""
        data = self.dict()
        # Convert datetimes to ISO strings for Parquet
        data["report_date"] = data["report_date"].isoformat() if data["report_date"] else None
        data["extraction_timestamp"] = data["extraction_timestamp"].isoformat()
        return data

    @classmethod
    def from_parquet_dict(cls, data: dict) -> "ESGMetrics":
        """Load from Parquet dict (strings → datetimes)."""
        if data.get("report_date"):
            data["report_date"] = datetime.fromisoformat(data["report_date"])
        if data.get("extraction_timestamp"):
            data["extraction_timestamp"] = datetime.fromisoformat(data["extraction_timestamp"])
        return cls(**data)
```

**Parquet Schema Mapping**:
```python
import pyarrow as pa

ESG_METRICS_SCHEMA = pa.schema([
    ("company_name", pa.string()),
    ("fiscal_year", pa.int32()),
    ("report_date", pa.string(), True),  # nullable
    ("scope1_emissions", pa.float64(), True),
    ("scope2_emissions", pa.float64(), True),
    ("scope3_emissions", pa.float64(), True),
    ("governance_score", pa.int32(), True),
    ("diversity_score", pa.int32(), True),
    ("employee_count", pa.int64(), True),
    ("safety_incidents", pa.int64(), True),
    ("water_consumption", pa.float64(), True),
    ("waste_generated", pa.float64(), True),
    ("renewable_energy_pct", pa.float64(), True),
    ("extraction_method", pa.string()),
    ("extraction_timestamp", pa.string()),
])
```

**Schema Parity Strategy**:
- Use `to_parquet_dict()` for serialization (datetime → string)
- Use `from_parquet_dict()` for deserialization (string → datetime)
- Property-based tests verify round-trip integrity

---

## Data Flow

### Structured Extraction (JSON/XBRL)
```
CompanyReport → ExtractionRouter.extract()
              ↓
    StructuredExtractor.extract()
              ↓
    json.load(report.local_path)
              ↓
    ESGMetrics(**mapped_fields)
              ↓
    Pydantic validation
              ↓
    ExtractionResult(metrics, quality)
```

### Unstructured Extraction (PDF/HTML)
```
CompanyReport → ExtractionRouter.extract()
              ↓
    LLMExtractor.extract()
              ↓
    PyMuPDF/BeautifulSoup text extraction
              ↓
    LLM prompt construction
              ↓
    LLM API call (with retry)
              ↓
    JSON response parsing
              ↓
    ESGMetrics(**llm_response)
              ↓
    Pydantic validation
              ↓
    ExtractionResult(metrics, quality)
```

---

## Quality Assessment

### ExtractionQuality Dataclass
```python
@dataclass
class ExtractionQuality:
    """Quality metrics for extraction process."""

    field_completeness: float  # % fields populated (non-None)
    type_correctness: float    # % fields with valid types (Pydantic guarantees 1.0)
    value_validity: float      # % numeric fields within expected ranges

    def overall_score(self) -> float:
        """Weighted average quality score."""
        return (
            0.4 * self.field_completeness +
            0.3 * self.type_correctness +
            0.3 * self.value_validity
        )
```

**Thresholds**:
- Structured extraction: field_completeness ≥0.95, overall_score ≥0.95
- Unstructured extraction: field_completeness ≥0.70, overall_score ≥0.80

---

## Verification Strategy

### Differential Tests
- Extract same SEC EDGAR file using both StructuredExtractor and ground truth annotations
- Compare field values, assert ≥98% match

### Sensitivity Tests
- Perturb content_type to invalid values → assert ValueError
- Perturb JSON structure (missing fields) → assert graceful degradation
- Perturb LLM responses (invalid JSON) → assert error handling

### Property Tests
- Generate 50 random ESGMetrics instances with Hypothesis
- Serialize to Parquet, deserialize, assert equality
- Verify schema compatibility with pyarrow validation

---

## Success Thresholds (From Hypothesis)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Structured extraction accuracy | ≥98% | Field-level precision/recall |
| Unstructured extraction accuracy | ≥85% | Field-level precision/recall |
| Schema parity | 100% | Parquet round-trip tests |
| Coverage (CP files) | ≥95% line, ≥95% branch | pytest-cov |
| Type safety | 0 mypy errors | mypy --strict |
| Complexity (CP files) | CCN ≤10 | lizard |

---

**Document Prepared By**: Scientific Coding Agent v13.8-MEA
**Review Status**: Draft (Context Gate)
**Next Action**: Create evidence.json with primary sources
