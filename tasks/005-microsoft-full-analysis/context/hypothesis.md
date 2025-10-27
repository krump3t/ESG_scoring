# Hypothesis - Task 005: Extraction Pipeline Authenticity Validation & Remediation

**Task ID:** 005-extraction-pipeline-authenticity
**Date:** 2025-10-22
**Protocol:** SCA v13.8-MEA

---

## Primary Hypothesis

**H1:** Implementing semantic segmentation, table extraction, and entity recognition in the PDF extraction pipeline will achieve ≥85% overlap with manual ground truth extraction, enabling authentic embeddings generation and knowledge graph preparation.

**Rationale:** Current naive extraction (0.27 findings/page, 4 themes) violates SCA authenticity invariants. Enhanced extraction with discourse-aware chunking, structured data capture, and NLP will achieve production-grade authenticity.

---

## Success Metrics

### Primary Metrics (Authenticity Gates)

| Metric | Baseline (Naive) | Target (Enhanced) | Measurement Method |
|--------|-----------------|-------------------|-------------------|
| **Coverage** | 0.27 findings/page (31 from 114 pages) | ≥5 findings/page (≥570 findings) | Count findings / page count |
| **Theme Diversity** | 4 themes (Climate, Energy, Materials, Operations) | ≥7 themes | Unique theme count |
| **Table Capture** | 0% (disabled) | 100% of tables | Compare extracted tables vs manual count |
| **Quantitative Metrics** | ~10% (31 findings, few with metrics) | ≥80% of numeric data | Regex scan for metrics, check capture rate |
| **Manual Audit Match** | ~30% estimated | ≥85% overlap | Jaccard similarity of key phrases |

### Quality Metrics

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| **Semantic Fidelity** | ≥90% multi-sentence statements preserved | Check compound statements not fragmented |
| **Entity Extraction** | ≥80% of organizations, dates, quantities | Compare spaCy entities vs manual annotation |
| **Relationship Extraction** | ≥70% of partnerships, policies, commitments | Pattern matching + manual review |
| **Structured Data Integrity** | 100% of tables with row/col preservation | Validate table structure intact |

---

## Critical Path

**CP Files:**
- `agents/crawler/extractors/enhanced_pdf_extractor.py` (NEW - core extraction logic)
- `agents/crawler/extractors/pdf_extractor.py` (MODIFIED - add semantic segmentation hooks)

**Entry Points:**
- `EnhancedPDFExtractor.extract()` - Main extraction method
- `EnhancedPDFExtractor.semantic_segment()` - Discourse-aware chunking
- `EnhancedPDFExtractor.extract_tables_as_findings()` - Table → findings conversion
- `EnhancedPDFExtractor.extract_entities()` - NLP entity extraction

**CP Requirements:**
- Coverage: ≥95% line & branch
- Type safety: 0 mypy --strict errors
- Complexity: CCN ≤10, Cognitive ≤15
- TDD: ≥1 test per method, ≥1 Hypothesis property, ≥1 failure test
- Determinism: 100% (same PDF → same findings every time)

---

## Inputs & Outputs

### Inputs

1. **Apple 2022 Environmental Progress Report** (test corpus)
   - Path: `data/pdf_cache/ed9a89cf9feb626c5bb8429f8dddfba6.pdf`
   - Pages: 114
   - Text: 405K chars
   - Expected findings: 570-1000 (5-9 per page)

2. **Manual Ground Truth** (validation baseline)
   - 10-page sample: pages 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
   - Hand-extracted findings with themes, entities, relationships
   - Used for ≥85% overlap validation

3. **Dependencies**
   - `PyMuPDF` (fitz) - PDF text extraction
   - `pdfplumber` - Table extraction
   - `spacy` (en_core_web_sm) - Entity/relationship extraction
   - `nltk` - Sentence tokenization (optional, fallback to regex)

### Outputs

1. **Enhanced Findings Dataset** (`artifacts/apple_2022_enhanced_findings.json`)
   ```json
   {
     "company": "Apple",
     "year": 2022,
     "extraction_method": "enhanced_semantic",
     "findings_count": 750,
     "findings": [
       {
         "finding_id": "apple_2022_001",
         "finding_text": "Full semantic chunk (multi-sentence preserved)",
         "type": "text" | "table" | "list",
         "theme": "Climate | Energy | Water | ...",
         "framework": "TCFD | GRI | ...",
         "page": 10,
         "section": "Climate Strategy",
         "entities": {
           "organizations": ["Apple", "EPA"],
           "dates": ["2030", "2018"],
           "quantities": ["1,527 Mgal", "90%"]
         },
         "relationships": [
           {"type": "partnership", "subject": "Apple", "object": "Google"}
         ],
         "metrics": [
           {"name": "total_water_use", "value": 1527, "unit": "Mgal"}
         ],
         "structured_data": [[...]] // if table
       }
     ]
   }
   ```

2. **Validation Report** (`reports/EXTRACTION_AUTHENTICITY_REPORT.md`)
   - Coverage metrics (findings/page, theme distribution)
   - Manual audit comparison (Jaccard similarity scores)
   - Entity/relationship extraction accuracy
   - Table capture completeness
   - Authenticity certification (pass/fail per gate)

3. **Extraction Authenticity Guarantee** (`EXTRACTION_AUTHENTICITY.md`)
   - Documented coverage guarantees
   - Theme diversity guarantees
   - Table/metric capture guarantees
   - Validation methodology
   - Embeddings/KG readiness certification

---

## Validation Plan

### Phase 1: TDD Tests (Write BEFORE Implementation)

```python
# tests/test_enhanced_extraction_cp.py

@pytest.mark.cp
def test_extraction_coverage_minimum_5_per_page():
    """Enhanced extraction must yield ≥5 findings/page"""
    extractor = EnhancedPDFExtractor()
    findings = extractor.extract(APPLE_PDF)
    assert len(findings) >= 114 * 5  # 570+ findings

@pytest.mark.cp
def test_extraction_theme_diversity_minimum_7():
    """Enhanced extraction must capture ≥7 distinct themes"""
    extractor = EnhancedPDFExtractor()
    findings = extractor.extract(APPLE_PDF)
    themes = set(f['theme'] for f in findings)
    assert len(themes) >= 7
    assert 'Water' in themes
    assert 'Governance' in themes

@pytest.mark.cp
def test_extraction_captures_all_tables():
    """Enhanced extraction must capture 100% of tables"""
    extractor = EnhancedPDFExtractor()
    findings = extractor.extract(APPLE_PDF)
    table_findings = [f for f in findings if f['type'] == 'table']
    assert len(table_findings) >= 20  # Apple has ~20 tables

@pytest.mark.cp
def test_extraction_preserves_multi_sentence_statements():
    """Semantic chunking must not fragment compound statements"""
    extractor = EnhancedPDFExtractor()
    findings = extractor.extract(APPLE_PDF)
    # Check for known multi-sentence statement from Page 10
    apple_commitment = [f for f in findings if '2030 carbon goal' in f['finding_text']]
    assert len(apple_commitment) > 0
    # Verify compound statement preserved (≥3 sentences in one finding)
    assert len(apple_commitment[0]['finding_text'].split('.')) >= 3

@pytest.mark.cp
@given(pdf_path=st.just(APPLE_PDF))
def test_extraction_determinism(pdf_path):
    """Extraction must be 100% deterministic (same input → same output)"""
    extractor = EnhancedPDFExtractor()
    findings1 = extractor.extract(pdf_path)
    findings2 = extractor.extract(pdf_path)
    findings3 = extractor.extract(pdf_path)
    assert findings1 == findings2 == findings3
```

### Phase 2: Manual Audit Validation

1. **Sample Selection:** Pages 10, 20, 30, 40, 50, 60, 70, 80, 90, 100 (10 pages)
2. **Manual Extraction:** Human extracts all findings from these pages (expected ~50-90 findings)
3. **Automated Extraction:** Run enhanced extractor on same 10 pages
4. **Comparison:** Calculate Jaccard similarity of key phrases
   - **Pass:** ≥85% overlap
   - **Fail:** <85% overlap (identify gaps, iterate)

### Phase 3: MEA Validation Loop

```
┌─────────────────────────────────────────────────────────────┐
│         MEA LOOP (Mandatory Execution Algorithm)            │
└─────────────────────────────────────────────────────────────┘

Step 1: Write/Fix Code
├── Implement EnhancedPDFExtractor
├── Add semantic_segment() method
├── Add extract_tables_as_findings() method
└── Add extract_entities() method

Step 2: Execute Validation
└── Run: sca-protocol-skill\commands\validate-only.ps1

Step 3: Capture & Analyze Output
└── Print full JSON validation_output

Step 4: Route (Decision)
├── IF status == "ok":
│   ├── Execute snapshot-save.ps1
│   └── Report success, proceed to manual audit
├── IF status == "blocked" OR "revise":
│   ├── List failed gates (coverage_cp, types_cp, tdd, etc.)
│   ├── GO BACK TO STEP 1 (autonomous remediation)
│   └── Stop after 3 consecutive failures
```

### Phase 4: Embeddings/KG Readiness Validation

1. **Embeddings Test:** Generate embeddings for 100 random findings
   - Verify semantic diversity (embedding similarity matrix)
   - Check for redundancy (no duplicate embeddings)

2. **KG Test:** Extract entities/relationships from 100 random findings
   - Verify entity coverage (≥3 entities per finding on average)
   - Verify relationship coverage (≥1 relationship per 2 findings)

3. **Downstream Integration Test:**
   - Feed findings to scorer (validate all 7 dimensions represented)
   - Feed findings to KG builder (validate graph structure)

---

## Risk Counters

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **spaCy model not available** | Medium | High | Fallback to regex entity extraction; document limitation |
| **Table extraction errors (malformed tables)** | Medium | Medium | Validate table structure; skip malformed, log warning |
| **Semantic segmentation over-chunks (fragments statements)** | Medium | High | Tune discourse boundary detection; validate multi-sentence preservation test |
| **Performance degradation (<10ms/finding)** | Low | Medium | Profile extraction; optimize NLP batch processing |
| **Determinism failure (non-reproducible results)** | Low | Critical | Root cause analysis; ensure no randomness in chunking/NLP |
| **Manual audit match <85%** | Medium | High | Iterate on extraction logic; adjust thresholds; expand ground truth sample |

---

## Assumptions

See `assumptions.md` for full list.

**Key Assumptions:**
- A1: spaCy `en_core_web_sm` model sufficient for entity extraction (vs larger models)
- A2: Discourse boundaries detectable via heuristics (section headers, topic shifts, list markers)
- A3: 10-page manual audit sample representative of full 114-page report
- A4: Table-to-text conversion preserves semantic fidelity for scoring
- A5: Enhanced extraction maintains determinism (no randomness introduced)

---

## Exclusions

**Out of Scope:**
1. ❌ OCR (assume PDFs have text layer; Apple PDF confirmed extractable)
2. ❌ Image content extraction (charts, graphs - extract metadata only)
3. ❌ Multi-document extraction (focus: single PDF validation)
4. ❌ Non-English reports (Apple report is English; extend later if needed)

**In Scope:**
1. ✅ Semantic segmentation (discourse-aware chunking)
2. ✅ Table extraction + conversion to findings
3. ✅ Entity/relationship extraction (spaCy NLP)
4. ✅ Manual audit validation (10-page sample)
5. ✅ Embeddings/KG readiness certification

---

**Hypothesis Complete**
