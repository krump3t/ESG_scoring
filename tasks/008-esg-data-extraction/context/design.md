# Task 008: ESG Maturity Evidence Extraction - Design
## ESG Prospecting Engine | SCA v13.8-MEA

**Task ID:** 008-esg-data-extraction
**Date:** 2025-10-22
**Protocol:** SCA v13.8-MEA
**Version:** 1.0

---

## System Architecture

### High-Level Flow

```
┌─────────────────┐
│  SEC Filings    │ (25 HTML files from Task 007)
│  (10-K/20-F)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Filing Parser                     │
│   - HTML → Structured Sections      │
│   - Extract text blocks             │
│   - Identify page numbers           │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Evidence Extractor (7 Matchers)  │
│   ┌───────────────────────────┐    │
│   │ TSP Matcher               │    │
│   │ OSP Matcher               │    │
│   │ DM Matcher                │    │
│   │ GHG Matcher               │    │
│   │ RD Matcher                │    │
│   │ EI Matcher                │    │
│   │ RMM Matcher               │    │
│   └───────────────────────────┘    │
│   - Pattern matching (regex + NLP) │
│   - Context window extraction      │
│   - Confidence scoring              │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Stage Classifier                  │
│   - Map evidence → maturity stage   │
│   - Apply stage indicators          │
│   - Aggregate multi-evidence        │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Evidence Database (JSON)          │
│   - evidence_id, theme, stage       │
│   - doc_id, page_no, extract        │
│   - confidence, hash                │
└─────────────────────────────────────┘
```

---

## Component Design

### 1. Filing Parser

**Purpose:** Convert SEC HTML filings into structured, searchable text blocks.

**Input:** HTML file (10-K or 20-F from SEC EDGAR)

**Output:** Structured document object:
```python
{
  "doc_id": "10-K_2025_AAPL",
  "company": "Apple Inc.",
  "cik": "0000320193",
  "year": 2025,
  "filing_type": "10-K",
  "sections": [
    {
      "section_id": "Item_1",
      "title": "Business",
      "text": "...",
      "page_start": 5,
      "page_end": 12
    },
    {
      "section_id": "Item_1A",
      "title": "Risk Factors",
      "text": "...",
      "page_start": 13,
      "page_end": 25
    }
  ],
  "full_text": "concatenated text",
  "total_pages": 156
}
```

**Technical Approach:**
- **HTML Parsing:** BeautifulSoup4
- **Section Detection:** Regex patterns for SEC filing structure (Item 1, Item 1A, Item 7, etc.)
- **Page Number Extraction:** Parse page indicators from HTML metadata or headers
- **Text Cleaning:** Remove HTML tags, normalize whitespace, preserve paragraph structure

**Key Sections to Parse:**
- Item 1: Business (often contains operational structure, energy use)
- Item 1A: Risk Factors (climate risk disclosures)
- Item 7: Management Discussion & Analysis (targets, GHG data)
- Sustainability/ESG section (if present, often non-standard location)

---

### 2. Theme-Specific Matchers (7 Modules)

Each matcher implements a common interface:

```python
class BaseMatcher:
    def __init__(self, theme: str):
        self.theme = theme
        self.patterns = self._load_patterns()

    def match(self, text: str, page_no: int) -> List[Evidence]:
        """
        Returns list of Evidence objects with:
        - matched text span
        - confidence score (0.0-1.0)
        - stage indicator (0-4)
        - evidence type
        """
        pass

    def _load_patterns(self) -> Dict:
        """Load regex patterns and keywords for this theme"""
        pass
```

#### 2.1 TSP Matcher (Target Setting & Planning)

**Stage Indicators:**
- **Stage 0:** No keywords found or only generic CSR
- **Stage 1:** Qualitative targets ("reduce emissions", "improve efficiency")
- **Stage 2:** Quantitative + time-bound ("reduce by 25% by 2030", "baseline year 2020")
- **Stage 3:** SBTi keywords ("science-based target", "SBTi pending", "SBTi submitted")
- **Stage 4:** SBTi validation ("SBTi approved", "SBTi validated") + financial linkage ("CAPEX", "OPEX")

**Patterns:**
```python
TSP_PATTERNS = {
    "sbti_stage_4": r"SBTi (approved|validated|committed)",
    "sbti_stage_3": r"SBTi (pending|submitted|science-based)",
    "quantitative_target": r"reduce.*?(\d+)%.*?by (\d{4})",
    "baseline_year": r"baseline year (\d{4})",
    "net_zero": r"net(-|\s)zero.*?(\d{4})",
    "scope_targets": r"Scope [123] target",
    "financial_integration": r"(CAPEX|OPEX).*?(sustainability|climate|emissions)"
}
```

**Confidence Scoring:**
- High (0.9-1.0): Explicit SBTi validation, quantitative targets with baseline
- Medium (0.7-0.9): Qualitative targets, partial quantification
- Low (0.5-0.7): Generic sustainability mentions

---

#### 2.2 OSP Matcher (Operational Structure & Processes)

**Stage Indicators:**
- **Stage 0:** No governance mentions
- **Stage 1:** Named owner ("Sustainability Manager", "ESG team")
- **Stage 2:** Formalized roles + policies ("Chief Sustainability Officer", "ESG policy")
- **Stage 3:** Cross-functional ("ESG committee", "Board oversight", "quarterly reviews")
- **Stage 4:** Management system + audit ("internal audit", "ESG management system")

**Patterns:**
```python
OSP_PATTERNS = {
    "cso": r"Chief Sustainability Officer",
    "esg_committee": r"(ESG|sustainability) committee",
    "board_oversight": r"Board.*?(oversight|responsible).*?(ESG|sustainability)",
    "internal_audit": r"internal audit.*?(ESG|sustainability)",
    "kpi_tracking": r"(KPI|key performance indicator).*?(ESG|sustainability)",
    "management_system": r"(ESG|sustainability) management system"
}
```

---

#### 2.3 DM Matcher (Data Maturity)

**Stage Indicators:**
- **Stage 0:** No data methodology mentions
- **Stage 1:** Manual collection ("spreadsheet", "manual entry")
- **Stage 2:** Partial automation ("automated collection", "validation protocols")
- **Stage 3:** Centralized database ("centralized platform", "supplier data")
- **Stage 4:** Automated pipelines ("real-time", "ETL", "automated validation")

**Patterns:**
```python
DM_PATTERNS = {
    "automated_pipeline": r"automated.*(data collection|pipeline|ETL)",
    "centralized_platform": r"centralized.*(platform|database|system)",
    "real_time": r"real(-|\s)time.*(monitoring|data|validation)",
    "supplier_data": r"supplier data (exchange|collection|integration)",
    "data_validation": r"data (validation|quality|QA) (protocol|process)"
}
```

---

#### 2.4 GHG Matcher (GHG Accounting)

**Stage Indicators:**
- **Stage 0:** No emissions data
- **Stage 1:** Partial Scope 1/2 ("Scope 1 emissions")
- **Stage 2:** Complete Scope 1/2 + partial Scope 3, with methodology
- **Stage 3:** Comprehensive Scope 1/2/3 + limited assurance
- **Stage 4:** Reasonable assurance + GHG Protocol compliance

**Patterns:**
```python
GHG_PATTERNS = {
    "scope_1": r"Scope 1 (emissions|GHG)",
    "scope_2": r"Scope 2 (emissions|GHG)",
    "scope_3": r"Scope 3 (emissions|GHG)",
    "emissions_value": r"([\d,]+)\s*(mtCO2e|tCO2e|metric tons CO2)",
    "ghg_protocol": r"GHG Protocol",
    "limited_assurance": r"limited assurance.*(emissions|GHG)",
    "reasonable_assurance": r"reasonable assurance.*(emissions|GHG)",
    "assurance_provider": r"(Deloitte|EY|KPMG|PwC).*(assurance|verification).*(emissions|GHG)",
    "base_year": r"base year (\d{4})"
}
```

**Numerical Extraction:**
Extract actual emissions values:
- Regex to find patterns like "12,345 mtCO2e" or "1.2 million metric tons CO2 equivalent"
- Convert to standard units (mtCO2e)
- Link to Scope 1/2/3

---

#### 2.5 RD Matcher (Reporting & Disclosure)

**Stage Indicators:**
- **Stage 0:** No framework alignment
- **Stage 1:** GRI index partial ("GRI", "GRI Content Index")
- **Stage 2:** TCFD/ISSB aligned ("TCFD", "ISSB")
- **Stage 3:** Cross-framework ("GRI and TCFD", "dual materiality")
- **Stage 4:** External assurance + digital tagging ("XBRL", "assured")

**Patterns:**
```python
RD_PATTERNS = {
    "gri": r"GRI( |-)(\d{3}|Standards|Content Index)",
    "tcfd": r"TCFD( |-)?(aligned|alignment|recommendations)",
    "issb": r"ISSB( |-)?(S1|S2|standards)",
    "sasb": r"SASB( |-)?(standards|materiality)",
    "csrd": r"CSRD|Corporate Sustainability Reporting Directive",
    "external_assurance": r"external assurance.*(sustainability|ESG)",
    "xbrl": r"XBRL|eXtensible Business Reporting Language",
    "integrated_report": r"integrated (report|reporting)"
}
```

---

#### 2.6 EI Matcher (Energy Intelligence)

**Stage Indicators:**
- **Stage 0:** No energy tracking
- **Stage 1:** Basic metering ("energy consumption", "kWh")
- **Stage 2:** KPIs + projects ("energy efficiency", "renewable energy")
- **Stage 3:** Automated monitoring ("EMS", "energy management system")
- **Stage 4:** AI/ML forecasting ("predictive", "AI", "optimization")

**Patterns:**
```python
EI_PATTERNS = {
    "energy_consumption": r"([\d,]+)\s*(kWh|MWh|GWh)",
    "renewable_energy": r"renewable energy.*?([\d.]+)%",
    "ems": r"(EMS|energy management system)",
    "energy_efficiency": r"energy efficiency (project|initiative|improvement)",
    "predictive_maintenance": r"predictive maintenance",
    "ai_forecasting": r"(AI|machine learning|ML).*(energy|forecasting|optimization)"
}
```

---

#### 2.7 RMM Matcher (Risk Management & Mitigation)

**Stage Indicators:**
- **Stage 0:** No risk framework
- **Stage 1:** Qualitative risks ("climate risk", "environmental risk")
- **Stage 2:** Risk taxonomy ("physical risk", "transition risk")
- **Stage 3:** Scenario analysis ("1.5°C scenario", "2°C scenario")
- **Stage 4:** Financial integration ("financial impact", "enterprise risk")

**Patterns:**
```python
RMM_PATTERNS = {
    "climate_risk": r"climate risk",
    "physical_risk": r"physical risk.*(flood|wildfire|sea level|drought)",
    "transition_risk": r"transition risk.*(policy|technology|market)",
    "scenario_analysis": r"scenario (analysis|modeling|testing).*(1\.5°C|2°C|climate)",
    "financial_impact": r"financial impact.*(climate|ESG)",
    "tcfd_risk": r"TCFD.*(risk|scenario)",
    "risk_mitigation": r"risk mitigation (strategy|plan)"
}
```

---

### 3. Evidence Extractor (Orchestration)

**Purpose:** Coordinate all 7 matchers and aggregate evidence.

```python
class EvidenceExtractor:
    def __init__(self):
        self.matchers = [
            TSPMatcher(),
            OSPMatcher(),
            DMMatcher(),
            GHGMatcher(),
            RDMatcher(),
            EIMatcher(),
            RMMMatcher()
        ]

    def extract_evidence_from_filing(
        self,
        filing: ParsedFiling
    ) -> List[Evidence]:
        """
        Run all 7 matchers on the filing.
        Returns aggregated evidence list.
        """
        all_evidence = []

        for matcher in self.matchers:
            theme_evidence = matcher.match(
                text=filing.full_text,
                page_no=self._get_page_number(filing)
            )
            all_evidence.extend(theme_evidence)

        # Deduplicate by hash
        all_evidence = self._deduplicate(all_evidence)

        # Sort by confidence (highest first)
        all_evidence.sort(key=lambda e: e.confidence, reverse=True)

        return all_evidence
```

**Context Window Extraction:**
For each match, extract 30-word window:
- 15 words before match
- Match text
- 15 words after match

This provides context for human review and explainability.

**Hash Generation:**
SHA256 hash of extracted text for deduplication:
```python
import hashlib

def generate_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
```

---

### 4. Stage Classifier

**Purpose:** Map evidence to maturity stages (0-4) based on stage indicators.

**Logic:**
```python
class StageClassifier:
    def classify(self, evidence: List[Evidence], theme: str) -> int:
        """
        Determine stage (0-4) for a theme based on evidence.

        Rules:
        - If no evidence: Stage 0
        - If multiple stage indicators: take highest
        - If ambiguous: take lower (conservative scoring)
        """
        if not evidence:
            return 0

        # Get all stage indicators for this theme
        stage_indicators = [e.stage_indicator for e in evidence if e.theme == theme]

        if not stage_indicators:
            return 0

        # Conservative: require multiple pieces of evidence for Stage 4
        if 4 in stage_indicators:
            count_stage_4 = stage_indicators.count(4)
            if count_stage_4 >= 2:  # Require at least 2 Stage 4 evidence items
                return 4
            else:
                return 3  # Downgrade to Stage 3 if only 1 piece

        # Otherwise, take max
        return max(stage_indicators)
```

---

### 5. Confidence Scoring

**Formula:**
```
confidence = pattern_match_strength * context_relevance * specificity_bonus

Where:
- pattern_match_strength: 0.6-1.0 (exact vs. partial match)
- context_relevance: 0.8-1.0 (nearby keywords boost confidence)
- specificity_bonus: +0.1 if numerical values present, +0.1 if named entities present
```

**Example:**
- Match: "SBTi validated science-based targets"
- pattern_match_strength: 1.0 (exact "SBTi validated")
- context_relevance: 1.0 (contains "science-based")
- specificity_bonus: 0.0
- **confidence = 1.0 * 1.0 * 1.0 = 1.0**

**Example 2:**
- Match: "committed to reduce emissions"
- pattern_match_strength: 0.7 (generic reduction)
- context_relevance: 0.8 (no specific target)
- specificity_bonus: 0.0
- **confidence = 0.7 * 0.8 * 1.0 = 0.56**

---

## Data Structures

### Evidence Object

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Evidence:
    evidence_id: str  # UUID
    org_id: str  # CIK
    year: int
    theme: str  # TSP | OSP | DM | GHG | RD | EI | RMM
    stage_indicator: int  # 0-4
    doc_id: str  # e.g., "10-K_2025_AAPL"
    page_no: int
    span_start: int  # Character offset in full_text
    span_end: int
    extract_30w: str  # 30-word context window
    hash_sha256: str
    confidence: float  # 0.0-1.0
    evidence_type: str  # e.g., "SBTi_validation", "emissions_disclosure"
    snapshot_id: str  # Extraction run identifier
```

### Parsed Filing Object

```python
@dataclass
class ParsedFiling:
    doc_id: str
    company: str
    cik: str
    year: int
    filing_type: str  # "10-K" or "20-F"
    sections: List[Section]
    full_text: str
    total_pages: int
```

---

## Processing Pipeline

**Step 1: Batch Load SEC Filings**
```python
filings = []
for file_path in glob("tasks/007-tier2-data-providers/qa/downloads/*.html"):
    filing = FilingParser.parse(file_path)
    filings.append(filing)
```

**Step 2: Extract Evidence (Parallel Processing)**
```python
from multiprocessing import Pool

def extract_filing(filing):
    extractor = EvidenceExtractor()
    return extractor.extract_evidence_from_filing(filing)

with Pool(processes=4) as pool:
    all_evidence = pool.map(extract_filing, filings)
```

**Step 3: Aggregate and Score**
```python
classifier = StageClassifier()

for filing, evidence_list in zip(filings, all_evidence):
    theme_scores = {}
    for theme in ["TSP", "OSP", "DM", "GHG", "RD", "EI", "RMM"]:
        theme_evidence = [e for e in evidence_list if e.theme == theme]
        theme_scores[theme] = classifier.classify(theme_evidence, theme)

    # Store results
    save_results(filing.doc_id, theme_scores, evidence_list)
```

**Step 4: Quality Validation**
```python
# Sample 5 random filings for manual review
sample = random.sample(filings, 5)

for filing in sample:
    evidence = get_evidence(filing.doc_id)
    manual_review_ui(filing, evidence)  # Human validates stage assignments
```

---

## Output Format

### Evidence JSON (per filing)

```json
{
  "doc_id": "10-K_2025_AAPL",
  "company": "Apple Inc.",
  "cik": "0000320193",
  "year": 2025,
  "extraction_date": "2025-10-22",
  "snapshot_id": "run_20251022_143022",
  "evidence_count": 23,
  "theme_coverage": ["TSP", "OSP", "GHG", "RD", "EI", "RMM"],
  "evidence": [
    {
      "evidence_id": "uuid-1",
      "theme": "TSP",
      "stage_indicator": 4,
      "evidence_type": "sbti_validation",
      "page_no": 12,
      "extract_30w": "Apple has committed to science-based targets validated by the Science Based Targets initiative (SBTi) to achieve net-zero emissions across our value chain by 2030.",
      "confidence": 0.95,
      "hash_sha256": "abc123..."
    },
    {
      "evidence_id": "uuid-2",
      "theme": "GHG",
      "stage_indicator": 3,
      "evidence_type": "emissions_disclosure_assured",
      "page_no": 45,
      "extract_30w": "Scope 1 and 2 emissions totaling 12.3 million metric tons CO2 equivalent (mtCO2e) were subject to limited assurance by Deloitte & Touche LLP.",
      "confidence": 0.92,
      "hash_sha256": "def456..."
    }
  ]
}
```

---

## Performance Considerations

**Target:** <45 seconds per filing (P95)

**Optimizations:**
1. **Parallel Processing:** Process 4 filings concurrently
2. **Regex Compilation:** Pre-compile all patterns at matcher initialization
3. **Early Exit:** If no matches in first 10% of text, reduce pattern set
4. **Caching:** Cache parsed filings to avoid re-parsing during development

**Expected Bottlenecks:**
- HTML parsing: ~5-10 seconds per filing
- Pattern matching: ~10-20 seconds per filing (7 matchers × 100-200 pages)
- Evidence aggregation: ~2-5 seconds per filing

**Total:** ~17-35 seconds typical, <45 seconds P95

---

## Testing Strategy

### Unit Tests (Per Matcher)

```python
def test_tsp_matcher_stage_4():
    """Test TSP matcher identifies Stage 4 (SBTi validated)"""
    text = "Our science-based targets were validated by SBTi in 2024"
    matcher = TSPMatcher()
    evidence = matcher.match(text, page_no=1)

    assert len(evidence) == 1
    assert evidence[0].stage_indicator == 4
    assert evidence[0].confidence >= 0.9
```

### Integration Tests

```python
def test_full_extraction_pipeline():
    """Test end-to-end extraction on sample filing"""
    filing = FilingParser.parse("tests/fixtures/sample_10k.html")
    extractor = EvidenceExtractor()
    evidence = extractor.extract_evidence_from_filing(filing)

    # Should find evidence for at least 4 themes
    themes_found = set(e.theme for e in evidence)
    assert len(themes_found) >= 4

    # Should have at least 7 evidence items
    assert len(evidence) >= 7
```

### Quality Validation Tests

```python
def test_manual_validation_precision():
    """Compare automated extraction to human review"""
    # Load pre-validated test set
    ground_truth = load_ground_truth("tests/fixtures/validated_evidence.json")

    # Run extraction
    filing = FilingParser.parse(ground_truth["filing_path"])
    evidence = extract_evidence(filing)

    # Calculate precision
    true_positives = count_matches(evidence, ground_truth["evidence"])
    precision = true_positives / len(evidence)

    assert precision >= 0.75  # Threshold: 75% precision
```

---

## Error Handling

**Graceful Degradation:**
- If HTML parsing fails → log error, skip filing, continue batch
- If matcher fails → log error, continue with other matchers
- If no evidence found → return empty list (valid outcome, Stage 0)

**Logging:**
```python
import logging

logger = logging.getLogger("evidence_extractor")

logger.info(f"Processing filing: {doc_id}")
logger.debug(f"TSP matcher found {len(tsp_evidence)} evidence items")
logger.warning(f"No evidence found for theme: DM")
logger.error(f"Failed to parse filing: {doc_id}, error: {e}")
```

---

## Future Enhancements (Out of Scope for Task 008)

- **ML-based extraction:** Train transformer model for evidence classification
- **Table parsing:** Extract structured data from tables (more accurate than text)
- **PDF parsing:** Support native PDF filings (currently HTML only)
- **Multi-language support:** Extract from non-English filings
- **Real-time processing:** Stream processing for continuous extraction

---

**Version:** 1.0
**Status:** Design complete, ready for implementation
**Next:** Create evidence.json (research sources)
