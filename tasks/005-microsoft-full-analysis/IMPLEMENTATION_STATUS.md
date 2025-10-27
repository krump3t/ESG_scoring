# Task 005: Extraction Pipeline Remediation - Implementation Status

**Task ID:** 005-extraction-pipeline-authenticity
**Date:** 2025-10-22
**Protocol:** SCA v13.8-MEA
**Status:** 🟡 **IN PROGRESS - TDD Tests Written, Ready for Implementation**

---

## Progress Summary

### ✅ Completed

1. **Critical Gap Analysis**
   - Identified authenticity violation: 0.27 findings/page (need ≥5)
   - Validated against manual audit (5 pages)
   - Documented root causes: naive chunking, no tables, no entities

2. **Context Artifacts** (7/7 complete)
   - ✅ `context/hypothesis.md` - Success metrics, validation plan
   - ✅ `context/cp_paths.json` - Critical path definition
   - ✅ `context/evidence.json` (from earlier)
   - ✅ `context/design.md` (from earlier - needs minor update)
   - ✅ `context/data_sources.json` (from earlier)
   - ✅ `context/adr.md` (from earlier)
   - ✅ `context/assumptions.md` (from earlier)

3. **TDD Tests** (15 tests, all marked @pytest.mark.cp)
   - ✅ `tests/test_enhanced_extraction_cp.py` - 15 comprehensive tests
   - Coverage tests (5/15): findings/page, theme diversity, tables, metrics, preservation
   - Entity tests (2/15): entity extraction, relationship extraction
   - Determinism tests (2/15): exact match, Hypothesis property
   - Failure tests (3/15): missing PDF, corrupted PDF, spaCy unavailable
   - Performance test (1/15): <2 min target
   - **Expected:** All 15 tests FAIL on current baseline (naive extractor)

### 🟡 In Progress

4. **EnhancedPDFExtractor Implementation**
   - File: `agents/crawler/extractors/enhanced_pdf_extractor.py`
   - **Status:** READY TO IMPLEMENT
   - Components needed:
     1. **Semantic Segmentation** (discourse-aware chunking)
     2. **Table Extraction** (pdfplumber → findings conversion)
     3. **Entity Extraction** (spaCy NLP with regex fallback)
     4. **Relationship Extraction** (pattern matching)

### ⏳ Pending

5. **MEA Validation Loop**
   - Step 2: Run `validate-only.ps1` after implementation
   - Step 3: Analyze validation output (expect failures initially)
   - Step 4: Autonomous remediation (fix → validate → repeat)

6. **Manual Audit Validation**
   - 10-page sample comparison (pages 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
   - Jaccard similarity calculation
   - Target: ≥85% overlap

7. **Production Certification**
   - Document extraction authenticity guarantees
   - Validate embeddings/KG readiness
   - Create EXTRACTION_AUTHENTICITY.md

---

## Next Steps (MEA Loop - Step 1: Implement)

### Implementation Plan for Enhanced PDF Extractor

The enhanced extractor must implement 4 core capabilities:

#### 1. Semantic Segmentation (Replaces Naive `\n\n` Split)

**Current Problem:** Only 118 paragraphs from 114 pages
**Solution:** Discourse-aware chunking

```python
class EnhancedPDFExtractor:
    def semantic_segment(self, text: str, page_boundaries: List[int]) -> List[Dict]:
        """
        Segment text by semantic boundaries, not just newlines

        Strategy:
        1. Sentence tokenization (regex fallback if nltk unavailable)
        2. Identify discourse markers:
           - Section headers (^[A-Z][^a-z]{3,}$)
           - List items (bullets: •, -, numbers: 1., 2.)
           - Topic shifts (keyword density changes)
        3. Group into semantic chunks (3-8 sentences per chunk)
        4. Preserve multi-sentence compound statements
        5. Maintain page number metadata

        Expected yield: 800-1000 chunks (7-9 per page)
        """
        chunks = []

        # 1. Sentence tokenization
        sentences = self._tokenize_sentences(text)

        # 2. Identify boundaries
        boundaries = self._detect_discourse_boundaries(sentences)

        # 3. Group into chunks
        for start_idx, end_idx in boundaries:
            chunk_text = ' '.join(sentences[start_idx:end_idx])

            if len(chunk_text) >= 100:  # Minimum substantive length
                chunks.append({
                    'text': chunk_text,
                    'start_sentence': start_idx,
                    'end_sentence': end_idx,
                    'page': self._estimate_page(start_idx, page_boundaries)
                })

        return chunks
```

#### 2. Table Extraction + Conversion

**Current Problem:** Tables disabled (0% capture)
**Solution:** Extract tables with pdfplumber + convert to findings

```python
def extract_tables_as_findings(self, pdf_path: str) -> List[Dict]:
    """
    Extract ALL tables from PDF and convert to findings

    Each table becomes:
    1. Narrative finding (row-by-row description)
    2. Structured data (preserve table format)
    3. Metrics extraction (parse numeric values)

    Example (Page 50 water table):
    {
        'finding_id': 'apple_2022_table_05',
        'finding_text': 'Apple tracks corporate water use...1,527 Mgal...',
        'type': 'table',
        'structured_data': [[header], [row1], [row2], ...],
        'metrics': [
            {'name': 'total_water_use', 'value': 1527, 'unit': 'Mgal'},
            {'name': 'freshwater_pct', 'value': 90, 'unit': '%'}
        ]
    }
    """
    import pdfplumber

    table_findings = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()

            for table_idx, table in enumerate(tables):
                if not table or not table[0]:  # Skip empty
                    continue

                # Convert table to narrative
                narrative = self._table_to_narrative(table)

                # Extract metrics
                metrics = self._extract_table_metrics(table)

                table_findings.append({
                    'finding_id': f'table_{page_num+1:03d}_{table_idx+1}',
                    'finding_text': narrative,
                    'type': 'table',
                    'page': page_num + 1,
                    'structured_data': table,
                    'metrics': metrics,
                    'theme': self._classify_theme(narrative),
                    'framework': self._detect_framework(narrative)
                })

    return table_findings
```

#### 3. Entity Extraction (spaCy with Regex Fallback)

**Current Problem:** No entity extraction
**Solution:** spaCy NLP + regex fallback if unavailable

```python
def extract_entities(self, text: str) -> Dict[str, List[str]]:
    """
    Extract entities: organizations, dates, quantities

    Primary: spaCy NLP (en_core_web_sm)
    Fallback: Regex patterns if spaCy unavailable
    """
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)

        entities = {
            'organizations': [ent.text for ent in doc.ents if ent.label_ == 'ORG'],
            'dates': [ent.text for ent in doc.ents if ent.label_ == 'DATE'],
            'quantities': [ent.text for ent in doc.ents if ent.label_ in ['QUANTITY', 'PERCENT', 'MONEY']]
        }

    except (ImportError, OSError):
        # Fallback to regex
        entities = self._regex_entity_extraction(text)

    return entities


def _regex_entity_extraction(self, text: str) -> Dict[str, List[str]]:
    """Regex fallback for entity extraction"""
    import re

    return {
        'organizations': re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b', text),
        'dates': re.findall(r'\b\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b', text),
        'quantities': re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:%|Mgal|MW|GW|tons?|metric tons?)\b', text)
    }
```

#### 4. Relationship Extraction (Pattern Matching)

**Current Problem:** No relationship extraction
**Solution:** Pattern-based relationship detection

```python
def extract_relationships(self, text: str, entities: Dict) -> List[Dict]:
    """
    Extract relationships: partnerships, commitments, policies

    Patterns:
    - "[ORG] joined [ORG]" → partnership
    - "[ORG] committed to [GOAL]" → commitment
    - "compliant with [STANDARD]" → compliance
    """
    relationships = []

    # Partnership pattern
    partnership_matches = re.finditer(
        r'([\w\s]+)\s+joined\s+([\w\s,]+)',
        text,
        re.IGNORECASE
    )
    for match in partnership_matches:
        relationships.append({
            'type': 'partnership',
            'subject': match.group(1).strip(),
            'object': match.group(2).strip()
        })

    # Commitment pattern
    commitment_matches = re.finditer(
        r'([\w\s]+)\s+committed to\s+([\w\s]+(?:by \d{4})?)',
        text,
        re.IGNORECASE
    )
    for match in commitment_matches:
        relationships.append({
            'type': 'commitment',
            'subject': match.group(1).strip(),
            'object': match.group(2).strip()
        })

    return relationships
```

---

## File to Create

**Path:** `agents/crawler/extractors/enhanced_pdf_extractor.py`

**Size estimate:** ~800-1000 lines (comprehensive implementation)

**Structure:**
```
class EnhancedPDFExtractor:
    def __init__(self):
        # Initialize PDF extractor, theme keywords, framework patterns
        pass

    def extract(self, pdf_path: str) -> Dict[str, Any]:
        # Main entry point - orchestrates all extraction steps
        # Returns: {findings: [...], metadata: {...}}
        pass

    # Semantic Segmentation
    def semantic_segment(self, text: str, page_boundaries: List) -> List[Dict]:
        pass

    def _tokenize_sentences(self, text: str) -> List[str]:
        pass

    def _detect_discourse_boundaries(self, sentences: List[str]) -> List[Tuple]:
        pass

    # Table Extraction
    def extract_tables_as_findings(self, pdf_path: str) -> List[Dict]:
        pass

    def _table_to_narrative(self, table: List[List]) -> str:
        pass

    def _extract_table_metrics(self, table: List[List]) -> List[Dict]:
        pass

    # Entity/Relationship Extraction
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        pass

    def extract_relationships(self, text: str, entities: Dict) -> List[Dict]:
        pass

    def _regex_entity_extraction(self, text: str) -> Dict[str, List[str]]:
        pass

    # Theme/Framework Classification
    def _classify_theme(self, text: str) -> str:
        pass

    def _detect_framework(self, text: str) -> str:
        pass

    # Utility Methods
    def _estimate_page(self, sentence_idx: int, page_boundaries: List) -> int:
        pass

    def _is_section_header(self, text: str) -> bool:
        pass

    def _is_list_item(self, text: str) -> bool:
        pass
```

---

## Success Criteria (Post-Implementation)

After implementing `EnhancedPDFExtractor`, the MEA validation loop should show:

✅ **TDD Tests:** 15/15 pass (currently expect 15 failures)
✅ **Coverage:** ≥570 findings from Apple PDF (currently 31)
✅ **Theme Diversity:** ≥7 themes (currently 4)
✅ **Table Capture:** ≥20 tables (currently 0)
✅ **Determinism:** 100% (same input → same output)
✅ **Type Safety:** 0 mypy --strict errors
✅ **Complexity:** CCN ≤10, Cognitive ≤15

---

## Recommendation

**Implement `EnhancedPDFExtractor` now** following the design above, then run MEA validation loop to identify any gaps. This is a ~4-6 hour implementation effort for production-grade extraction authenticity.

Given session length, recommend:
1. **Option A:** Continue implementation now (4-6 hours)
2. **Option B:** Create implementation stub + save progress, resume in fresh session
3. **Option C:** User implements based on this detailed specification

**Current recommendation: Option B** (save progress, resume fresh) given token usage.

---

**Status:** Ready for implementation - All planning, design, and TDD tests complete
**Next:** Implement `EnhancedPDFExtractor` following specification above
