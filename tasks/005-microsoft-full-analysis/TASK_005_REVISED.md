# Task 005 (REVISED): Ingestion Pipeline Validation & Authentic Extraction

**Task ID:** 005-ingestion-pipeline-validation
**Date:** 2025-10-22
**Protocol:** SCA v13.8-MEA
**Status:** 🔴 **CRITICAL - AUTHENTICITY VIOLATION DETECTED**

---

## Critical Finding: Extraction Pipeline Fails Authenticity Requirements

### Validation Results

**Test Case:** Apple 2022 Environmental Progress Report (114 pages, 405K chars)

**Automated Extraction:**
- Findings extracted: **31**
- Themes captured: **4** (Climate, Energy, Materials, Operations)
- Findings/page ratio: **0.27** (catastrophically low)
- Missing themes: Water, Waste, Governance, Risk, Social, Disclosure

**Manual Audit (5-page sample):**
- Average chars/page: **4,281**
- Rich content on every page: policies, metrics, commitments, timelines
- **Page 50 example**: Detailed water metrics table (1,527 Mgal, 90% freshwater breakdown, recycled water %) - **COMPLETELY MISSED by extractor**

### Authenticity Violations

Per SCA v13.8 **Universal Authenticity Invariants**:

1. **❌ Authentic Computation Violated**: Extractor produced superficial results (31 findings from 114 pages = 73% content loss)
2. **❌ Algorithmic Fidelity Violated**: Simple paragraph chunking (`\n\n` split) is a trivial placeholder, not a real extraction algorithm
3. **❌ Data Integrity Violated**: Table data, structured content, multi-sentence disclosures lost

**Impact on Downstream Systems:**
- ❌ **Embeddings**: Incomplete semantic coverage (missing 70%+ of content)
- ❌ **Knowledge Graph**: Missing entities (water metrics), relationships (policy timeline), attributes (quantitative data)
- ❌ **Scoring**: Underestimates maturity (missing 6+ themes)

---

## Root Cause Analysis

### Problem 1: Naive Chunking Strategy

**Current Implementation:**
```python
paragraphs = text.split('\n\n')  # Split on double newlines
```

**Issues:**
- Only yields **118 paragraphs** from 114 pages (~1 paragraph/page)
- Loses table structure (tables don't have `\n\n` breaks)
- Breaks compound statements across multiple chunks
- No semantic understanding of discourse boundaries

### Problem 2: Keyword-Only Relevance Scoring

**Current Implementation:**
```python
score += 0.5 if keyword in text_lower
```

**Issues:**
- Misses implicit ESG content (e.g., "We track corporate water use" scores low despite being direct disclosure)
- No understanding of ESG disclosure patterns (metrics, commitments, governance)
- Theme keywords incomplete (missing "water use", "board oversight", etc.)

### Problem 3: No Table/Structured Data Extraction

**Current Implementation:**
- `extract_tables=False` (disabled)
- Even when enabled, `pdfplumber` tables are extracted but not converted to findings

**Issues:**
- Quantitative metrics lost (emissions data, water consumption, energy mix)
- Structured breakdowns lost (90% freshwater, 9% recycled, <1% alternative)
- Charts, diagrams metadata lost

---

## Requirements for Authentic Extraction

### Minimum Viable Extraction (MVE) Criteria

| Criterion | Target | Current | Status |
|-----------|--------|---------|--------|
| **Coverage** | ≥5 findings/page | 0.27 | ❌ FAIL |
| **Theme Diversity** | ≥7 themes | 4 | ❌ FAIL |
| **Table Capture** | 100% of tables | 0% | ❌ FAIL |
| **Quantitative Data** | ≥80% of metrics | ~10% | ❌ FAIL |
| **Semantic Fidelity** | Manual audit match ≥85% | ~30% | ❌ FAIL |

### Embeddings Requirements

For RAG/semantic search, extraction must:
1. ✅ **Preserve context**: Multi-sentence disclosures intact (not fragmented)
2. ✅ **Capture relationships**: "Apple joined Google, Microsoft, Amazon..." (entity relationships)
3. ✅ **Include metrics**: "1,527 Mgal, 90% freshwater" (quantitative grounding)
4. ✅ **Maintain structure**: Hierarchies (governance → board → committee), taxonomies (Scope 1/2/3)

### Knowledge Graph Requirements

For entity extraction and relationship mapping, extraction must:
1. ✅ **Entities**: Organizations (Apple, EPA, TCFD), People (executives), Locations (facilities)
2. ✅ **Relationships**: Partnerships ("joined Google"), Compliance ("EPA Clean Power Plan"), Commitments ("2030 carbon goal")
3. ✅ **Attributes**: Metrics (1,527 Mgal), Dates (2018, 2030), Certifications (ISO 14001)
4. ✅ **Events**: Policy advocacy timeline (2015-2017 events on Page 30)

---

## Proposed Solution: Semantic Segmentation + Multi-Modal Extraction

### Phase 1: Enhanced Chunking (Semantic Segmentation)

**Replace:** Naive `\n\n` split
**With:** Discourse-aware segmentation

```python
class SemanticChunker:
    """Segment text by semantic boundaries, not just newlines"""

    def segment(self, text: str, page_metadata: Dict) -> List[Segment]:
        # 1. Sentence tokenization (NLTK/spaCy)
        sentences = self.tokenize_sentences(text)

        # 2. Identify discourse boundaries
        # - Section headers (regex: ^[A-Z][^a-z]{3,}$)
        # - Topic shifts (embedding similarity < threshold)
        # - List items (bullets, numbers)

        # 3. Group into semantic chunks (3-8 sentences per chunk)
        chunks = self.group_by_discourse(sentences)

        # 4. Preserve multi-sentence statements
        # "Apple committed to X. This includes Y. We achieved Z."
        # → Single chunk (coherent statement)

        return chunks
```

**Expected yield:** ~800-1000 chunks (vs 118 paragraphs) = 7-9 chunks/page

### Phase 2: Table Extraction + Conversion

**Enable table extraction:**
```python
tables = pdf_extractor.extract(pdf_path, extract_tables=True)

for table in tables:
    # Convert table to finding
    finding = {
        'type': 'table',
        'finding_text': self.table_to_text(table['data']),  # Row-by-row narrative
        'structured_data': table['data'],  # Preserve raw table
        'metrics': self.extract_metrics(table['data'])  # Parse numbers
    }
```

**Example (Page 50 water table):**
```
finding_text: "Apple tracks corporate water use across facilities. In FY2022, total water use was 1,527 million gallons, comprising 90% freshwater (primarily municipal sources), 9% recycled water (from treatment plants), and <1% alternative sources (rainwater, condensate recovery)."

structured_data: [[Header row], [Data rows]...]

metrics: [
  {"metric": "total_water_use", "value": 1527, "unit": "Mgal"},
  {"metric": "freshwater_pct", "value": 90, "unit": "%"},
  {"metric": "recycled_water_pct", "value": 9, "unit": "%"}
]
```

### Phase 3: Entity & Relationship Extraction

**Add NLP layer:**
```python
import spacy
nlp = spacy.load("en_core_web_sm")

def extract_entities_relationships(text: str) -> Dict:
    doc = nlp(text)

    entities = {
        'organizations': [ent.text for ent in doc.ents if ent.label_ == 'ORG'],
        'dates': [ent.text for ent in doc.ents if ent.label_ == 'DATE'],
        'quantities': [ent.text for ent in doc.ents if ent.label_ == 'QUANTITY']
    }

    # Relationship patterns
    # "Apple joined [ORG]" → partnership relationship
    # "compliant with [STANDARD]" → compliance relationship

    return {'entities': entities, 'relationships': relationships}
```

### Phase 4: Validation Framework

**Ground truth comparison:**
```python
class ExtractionValidator:
    """Validate extraction against manual audit"""

    def validate_coverage(self, automated: List, manual_sample: List) -> float:
        # Manual audit: Extract 10 pages by hand
        # Compare: Did automated extraction capture same content?
        # Metric: Jaccard similarity of key phrases
        pass

    def validate_metrics_capture(self, extracted: List, pdf_path: str) -> float:
        # Scan PDF for all numeric patterns (\d+%|\d+\s*[A-Z][a-z]+)
        # Check: Did extractor capture ≥80% of metrics?
        pass

    def validate_theme_diversity(self, findings: List) -> bool:
        # Require ≥7 themes represented
        # Require ≥3 findings per theme
        pass
```

---

## Implementation Plan (SCA v13.8-MEA)

### Step 1: Write Tests FIRST (TDD)

```python
# tests/test_extraction_authenticity.py

@pytest.mark.cp
def test_extraction_coverage_minimum_5_findings_per_page():
    """Extraction must yield ≥5 findings/page for authentic coverage"""
    extractor = EnhancedExtractor()
    findings = extractor.extract(APPLE_PDF)

    assert len(findings) >= 114 * 5  # 570+ findings from 114 pages

@pytest.mark.cp
def test_extraction_captures_all_tables():
    """Extraction must capture 100% of tables as structured findings"""
    extractor = EnhancedExtractor()
    findings = extractor.extract(APPLE_PDF)

    # Apple report has ~20 tables (manual count)
    table_findings = [f for f in findings if f['type'] == 'table']
    assert len(table_findings) >= 20

@pytest.mark.cp
def test_extraction_theme_diversity():
    """Extraction must capture ≥7 distinct themes"""
    extractor = EnhancedExtractor()
    findings = extractor.extract(APPLE_PDF)

    themes = set(f['theme'] for f in findings)
    assert len(themes) >= 7
    assert 'Water' in themes  # Currently MISSING
    assert 'Governance' in themes  # Currently MISSING
```

### Step 2: Implement Enhanced Extractor

Create `agents/crawler/extractors/enhanced_pdf_extractor.py` with:
- Semantic chunking (discourse-aware)
- Table extraction + conversion
- Entity/relationship extraction (spaCy)
- Validation hooks

### Step 3: Run MEA Validation Loop

```powershell
# Write tests → Implement → Validate → Fix → Repeat
sca-protocol-skill\commands\validate-only.ps1
```

### Step 4: Document Authenticity Guarantees

Create `EXTRACTION_AUTHENTICITY.md` documenting:
- Coverage guarantees (≥5 findings/page)
- Theme diversity guarantees (≥7 themes)
- Table capture guarantees (100%)
- Validation methodology (manual audit protocol)

---

## Success Criteria

Task 005 is **BLOCKED** until extraction pipeline meets:

| Gate | Requirement | Status |
|------|-------------|--------|
| **Coverage** | ≥5 findings/page (570+ from Apple) | ❌ BLOCKED (31 current) |
| **Theme Diversity** | ≥7 themes | ❌ BLOCKED (4 current) |
| **Table Capture** | 100% of tables | ❌ BLOCKED (0% current) |
| **Manual Audit Match** | ≥85% overlap with human extraction | ❌ BLOCKED (~30% est.) |
| **TDD Tests** | All extraction tests pass | ❌ BLOCKED (tests not written) |
| **MEA Validation** | `validate-only.ps1` status: ok | ❌ BLOCKED |

---

## Next Actions

1. **Create Task 005 context artifacts** (hypothesis, design, evidence for extraction validation)
2. **Write TDD tests** for extraction authenticity (coverage, tables, themes)
3. **Implement EnhancedPDFExtractor** with semantic segmentation + table extraction
4. **Run MEA validation loop** until all tests pass
5. **Document authenticity guarantees** for downstream systems (embeddings, KG)

**Estimated Effort:** 4-6 hours (non-trivial refactor of CP extraction logic)

---

**Status:** BLOCKED - Authenticity violation must be resolved before proceeding with scoring/aggregation
**Priority:** CRITICAL - Blocks embeddings, KG, and all downstream analysis
