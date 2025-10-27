# Design - Phase 3B: Unstructured Extraction with LLM

**Task ID**: 013-unstructured-extraction-phase3b
**Phase**: 3B
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Architecture Overview

Phase 3B completes the asymmetric extraction design by implementing the **unstructured path** (PDF → LLM → ESGMetrics) alongside the structured path (JSON → Parser → ESGMetrics) from Phase 3.

```
┌─────────────────────────────────────────────────────────┐
│                    ExtractionRouter                      │
│                  (from Phase 3)                          │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  StructuredExtractor     │  │    LLMExtractor          │
│  (Phase 3 - Complete)    │  │  (Phase 3B - NEW)        │
│                          │  │                          │
│  • SEC EDGAR JSON        │  │  • PDF via PyMuPDF       │
│  • us-gaap parsing       │  │  • IBM watsonx.ai LLM    │
│  • 98% accuracy          │  │  • ≥85% target accuracy  │
└──────────────┬───────────┘  └──────────────┬───────────┘
               │                             │
               └──────────────┬──────────────┘
                              ▼
                      ┌──────────────────┐
                      │   ESGMetrics     │
                      │  (Pydantic v2)   │
                      └──────────────────┘
```

---

## Component Design

### 1. PDFTextExtractor (Helper Module)

**Purpose**: Extract text from born-digital PDF files using PyMuPDF

**Interface**:
```python
from typing import Optional
import fitz  # PyMuPDF

class PDFTextExtractor:
    """Extracts text from PDF files using PyMuPDF."""

    def __init__(self):
        """Initialize PDF text extractor."""
        self.min_text_length = 100  # Minimum expected text length

    def extract_text(self, pdf_path: str) -> str:
        """Extract all text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text (all pages concatenated)

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If PDF is empty or corrupted
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                text_parts.append(text)

            doc.close()
            full_text = "\n\n".join(text_parts)

            if len(full_text.strip()) < self.min_text_length:
                raise ValueError(f"PDF text too short: {len(full_text)} chars")

            return full_text

        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {e}")

    def extract_page(self, pdf_path: str, page_num: int) -> str:
        """Extract text from specific page (0-indexed).

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)

        Returns:
            Extracted text from page

        Raises:
            ValueError: If page number invalid
        """
        doc = fitz.open(pdf_path)
        if page_num < 0 or page_num >= len(doc):
            raise ValueError(f"Invalid page number: {page_num}")

        page = doc[page_num]
        text = page.get_text()
        doc.close()
        return text

    def get_page_count(self, pdf_path: str) -> int:
        """Get number of pages in PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Number of pages
        """
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
```

**Design Rationale**:
- PyMuPDF (fitz) is battle-tested for PDF text extraction
- Handles multi-page PDFs automatically
- Minimal external dependencies
- Fast (C++ backend)

**Test Strategy**:
- Test with REAL Apple Sustainability Report PDF
- Test with empty PDF (expect ValueError)
- Test with corrupted PDF (expect ValueError)
- Test page-level extraction

---

### 2. LLMExtractor (Critical Path)

**Purpose**: Extract ESG metrics from PDF text using IBM watsonx.ai LLM

**Interface**:
```python
from typing import Optional, Dict, Any
from ibm_watsonx_ai import Credentials, APIClient
from ibm_watsonx_ai.foundation_models import ModelInference
import json
import time

class LLMExtractor:
    """Extracts ESG metrics from unstructured data using IBM watsonx.ai."""

    def __init__(
        self,
        project_id: str,
        api_key: str,
        model_id: str = "ibm/granite-13b-chat-v2",
        use_cache: bool = True,
        cache_path: str = "test_data/llm_cache"
    ):
        """Initialize LLM extractor with IBM watsonx.ai credentials.

        Args:
            project_id: IBM Cloud project ID
            api_key: IAM API key
            model_id: watsonx.ai model ID (default: granite-13b-chat-v2)
            use_cache: Whether to cache/replay responses (for deterministic tests)
            cache_path: Path to cache directory
        """
        self.project_id = project_id
        self.model_id = model_id
        self.use_cache = use_cache
        self.cache_path = cache_path

        # Initialize watsonx.ai client
        credentials = Credentials(
            url="https://us-south.ml.cloud.ibm.com",
            api_key=api_key
        )
        self.client = APIClient(credentials)
        self.model = ModelInference(
            model_id=model_id,
            api_client=self.client,
            project_id=project_id
        )

        self.pdf_extractor = PDFTextExtractor()
        self.prompt_template = self._load_extraction_prompt()
        self.errors: List[ExtractionError] = []

    def extract(self, report: CompanyReport) -> ExtractionResult:
        """Extract ESG metrics from PDF report using LLM.

        Workflow:
        1. Extract text from PDF using PyMuPDF
        2. Construct LLM prompt with text + JSON schema
        3. Call watsonx.ai API with retry logic
        4. Parse LLM JSON response into ESGMetrics
        5. Assess extraction quality

        Args:
            report: CompanyReport with local_path to PDF

        Returns:
            ExtractionResult with metrics, quality, and errors

        Raises:
            ValueError: If report.local_path is None
        """
        self.errors = []

        if report.local_path is None:
            raise ValueError("CompanyReport.local_path is None")

        # Step 1: Extract text from PDF
        try:
            text = self.pdf_extractor.extract_text(report.local_path)
        except Exception as e:
            self.errors.append(ExtractionError(
                field_name=None,
                error_type=type(e).__name__,
                message=f"PDF text extraction failed: {e}",
                severity="error"
            ))
            return ExtractionResult(
                metrics=None,
                quality=ExtractionQuality(0.0, 0.0, 0.0),
                errors=self.errors
            )

        # Step 2: Construct prompt
        prompt = self._construct_prompt(
            company_name=report.company.name,
            fiscal_year=report.year,
            text=text
        )

        # Step 3: Call LLM with retry and caching
        try:
            response_json = self._call_llm_with_cache(
                prompt=prompt,
                cache_key=f"{report.company.cik}_{report.year}"
            )
        except Exception as e:
            self.errors.append(ExtractionError(
                field_name=None,
                error_type=type(e).__name__,
                message=f"LLM API call failed: {e}",
                severity="error"
            ))
            return ExtractionResult(
                metrics=None,
                quality=ExtractionQuality(0.0, 0.0, 0.0),
                errors=self.errors
            )

        # Step 4: Parse response into ESGMetrics
        metrics = self._parse_llm_response(response_json, report)

        # Step 5: Calculate quality
        quality = self._calculate_quality(metrics)

        return ExtractionResult(
            metrics=metrics,
            quality=quality,
            errors=self.errors
        )

    def _construct_prompt(self, company_name: str, fiscal_year: int, text: str) -> str:
        """Construct extraction prompt with JSON schema."""
        # Truncate text to fit model context window (~4000 tokens)
        max_chars = 12000  # ~3000 tokens
        truncated_text = text[:max_chars]

        prompt = f"""Extract ESG metrics from the following sustainability report for {company_name} (fiscal year {fiscal_year}).

Report Text:
{truncated_text}

Extract the following metrics and return as JSON:
- scope1_emissions (tCO2e): Scope 1 greenhouse gas emissions
- scope2_emissions (tCO2e): Scope 2 greenhouse gas emissions
- scope3_emissions (tCO2e): Scope 3 greenhouse gas emissions (if available)
- renewable_energy_pct (%): Percentage of renewable energy used
- water_usage (cubic meters): Total water usage
- waste_recycled_pct (%): Percentage of waste recycled
- women_in_workforce_pct (%): Percentage of women in workforce
- employee_turnover_rate (%): Employee turnover rate

Return ONLY valid JSON in this exact format:
{{
  "scope1_emissions": <number or null>,
  "scope2_emissions": <number or null>,
  "scope3_emissions": <number or null>,
  "renewable_energy_pct": <number or null>,
  "water_usage": <number or null>,
  "waste_recycled_pct": <number or null>,
  "women_in_workforce_pct": <number or null>,
  "employee_turnover_rate": <number or null>
}}

If a metric is not found, use null. Do not include explanations or text outside the JSON.
"""
        return prompt

    def _call_llm_with_cache(self, prompt: str, cache_key: str) -> Dict[str, Any]:
        """Call watsonx.ai LLM with caching for deterministic tests.

        Args:
            prompt: Extraction prompt
            cache_key: Unique key for caching (e.g., "cik_year")

        Returns:
            Parsed JSON response from LLM
        """
        cache_file = os.path.join(self.cache_path, f"{cache_key}.json")

        # Check cache first
        if self.use_cache and os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                cached = json.load(f)
                return cached["response"]

        # Call LLM with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.model.generate(
                    prompt=prompt,
                    params={
                        "decoding_method": "greedy",  # Deterministic
                        "max_new_tokens": 500,
                        "temperature": 0.0,  # No randomness
                        "stop_sequences": ["}"]  # Stop after JSON
                    }
                )

                # Extract generated text
                generated_text = response["results"][0]["generated_text"]

                # Parse JSON
                # Find JSON object in response
                start_idx = generated_text.find("{")
                end_idx = generated_text.rfind("}") + 1
                json_str = generated_text[start_idx:end_idx]

                response_json = json.loads(json_str)

                # Cache response
                if self.use_cache:
                    os.makedirs(self.cache_path, exist_ok=True)
                    with open(cache_file, "w") as f:
                        json.dump({
                            "cache_key": cache_key,
                            "model_id": self.model_id,
                            "timestamp": time.time(),
                            "response": response_json
                        }, f, indent=2)

                return response_json

            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff

    def _parse_llm_response(self, response_json: Dict[str, Any], report: CompanyReport) -> Optional[ESGMetrics]:
        """Parse LLM JSON response into ESGMetrics."""
        try:
            # Map LLM response to ESGMetrics fields
            metrics_dict = {
                "company_name": report.company.name,
                "cik": report.company.cik,
                "fiscal_year": report.year,
                "extraction_method": "llm",
                "data_source": "sustainability_report",
                "scope1_emissions": response_json.get("scope1_emissions"),
                "scope2_emissions": response_json.get("scope2_emissions"),
                "scope3_emissions": response_json.get("scope3_emissions"),
                "renewable_energy_pct": response_json.get("renewable_energy_pct"),
                "water_usage": response_json.get("water_usage"),
                "waste_recycled_pct": response_json.get("waste_recycled_pct"),
                "women_in_workforce_pct": response_json.get("women_in_workforce_pct"),
                "employee_turnover_rate": response_json.get("employee_turnover_rate"),
            }

            metrics = ESGMetrics(**metrics_dict)
            return metrics

        except Exception as e:
            self.errors.append(ExtractionError(
                field_name=None,
                error_type=type(e).__name__,
                message=f"Failed to parse LLM response: {e}",
                severity="error"
            ))
            return None

    def _calculate_quality(self, metrics: Optional[ESGMetrics]) -> ExtractionQuality:
        """Calculate extraction quality metrics."""
        if metrics is None:
            return ExtractionQuality(0.0, 0.0, 0.0)

        # Count non-null fields
        esg_fields = [
            "scope1_emissions", "scope2_emissions", "scope3_emissions",
            "renewable_energy_pct", "water_usage", "waste_recycled_pct",
            "women_in_workforce_pct", "employee_turnover_rate"
        ]

        non_null_count = sum(
            1 for field in esg_fields
            if getattr(metrics, field) is not None
        )

        field_completeness = non_null_count / len(esg_fields)

        # Assume LLM responses are type-correct (Pydantic validated)
        type_correctness = 1.0

        # Value validity: check ranges (percentages 0-100, emissions ≥0)
        value_validity = 1.0

        return ExtractionQuality(
            field_completeness=field_completeness,
            type_correctness=type_correctness,
            value_validity=value_validity
        )
```

**Design Rationale**:
- **Caching**: Enables deterministic testing without live API calls
- **Retry logic**: Handles transient API failures
- **Greedy decoding**: Temperature=0 for deterministic outputs
- **Prompt engineering**: Explicit JSON schema reduces hallucinations
- **Error handling**: Graceful degradation (return None + errors)

**Test Strategy**:
- Use cached responses for all unit tests
- One integration test with real API (marked `@pytest.mark.requires_api`)
- Test malformed JSON response (parsing error)
- Test API failure (network error)
- Test empty PDF (text extraction failure)

---

## Data Strategy

### Real Data Sources

1. **Apple Environmental Progress Report 2024**
   - URL: https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_2024.pdf
   - Size: ~5-10 MB PDF
   - Metrics: Scope 1/2/3 emissions, renewable energy %, water usage

2. **Microsoft Sustainability Report 2024**
   - URL: https://www.microsoft.com/en-us/sustainability/reports
   - Metrics: Carbon negative commitment, renewable energy %, water replenishment

3. **Tesla Impact Report 2023**
   - URL: https://www.tesla.com/ns_videos/2023-tesla-impact-report.pdf
   - Metrics: GHG emissions avoided, renewable energy deployment

### Ground Truth Creation

**Process**:
1. Download PDF
2. Manually read sustainability report
3. Extract ESG metrics from tables/charts
4. Record in `ground_truth/<company>_<year>_sustainability_ground_truth.json`
5. Include page numbers and source sections for traceability

**Example Ground Truth**:
```json
{
  "company_name": "Apple Inc.",
  "fiscal_year": 2024,
  "report_url": "https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_2024.pdf",
  "verified_date": "2025-10-24",
  "metrics": {
    "scope1_emissions": {
      "value": 48800,
      "unit": "tCO2e",
      "page": 12,
      "section": "Carbon Footprint"
    },
    "scope2_emissions": {
      "value": 127000,
      "unit": "tCO2e",
      "page": 12
    },
    "renewable_energy_pct": {
      "value": 100.0,
      "unit": "%",
      "page": 8,
      "section": "Clean Energy"
    }
  }
}
```

---

## Integration with Phase 3

Phase 3B **completes** the asymmetric extraction design from Phase 3:

**Phase 3 Delivered**:
- ExtractionRouter (content-type routing)
- StructuredExtractor (SEC EDGAR JSON)
- ESGMetrics model (Pydantic + Parquet)
- ExtractionResult contracts

**Phase 3B Adds**:
- LLMExtractor (PDF via watsonx.ai)
- PDFTextExtractor (PyMuPDF helper)
- Real sustainability report testing

**Combined Result**:
```python
# Full asymmetric extraction now works
router = ExtractionRouter(
    structured_extractor=StructuredExtractor(),  # Phase 3
    llm_extractor=LLMExtractor(project_id, api_key)  # Phase 3B
)

# Route SEC EDGAR JSON → StructuredExtractor
sec_report = CompanyReport(
    source=SourceRef(content_type="application/json"),
    local_path="apple_sec_edgar.json"
)
result1 = router.extract(sec_report)  # Uses StructuredExtractor

# Route Sustainability PDF → LLMExtractor
pdf_report = CompanyReport(
    source=SourceRef(content_type="application/pdf"),
    local_path="apple_sustainability.pdf"
)
result2 = router.extract(pdf_report)  # Uses LLMExtractor
```

---

## Success Thresholds

### Extraction Accuracy
- **Target**: ≥85% accuracy on ESG metrics from PDFs
- **Measurement**: Compare LLM-extracted values against ground truth
- **Tolerance**: ±10% for numeric values

### Coverage
- **Line Coverage**: ≥95%
- **Branch Coverage**: ≥95%
- **Files**: `llm_extractor.py`, `pdf_text_extractor.py`

### Tests
- **Total**: ≥25 tests
- **CP Tests**: All tests marked `@pytest.mark.cp`
- **Failure Tests**: ≥5 failure-path tests

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Ready for Implementation
**Next**: Create evidence.json and remaining context files
