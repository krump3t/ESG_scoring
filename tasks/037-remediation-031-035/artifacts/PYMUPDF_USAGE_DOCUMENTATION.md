# PyMuPDF Usage Documentation
## Task 037 - Phase 0 Baseline Documentation

### Executive Summary
**Date:** 2025-11-05
**Task:** 037-remediation-031-035
**Purpose:** Document existing PyMuPDF usage patterns before Docling migration

### Current PyMuPDF Dependencies

#### 1. Direct PyMuPDF Import Files
- **agents/extraction/pdf_text_extractor.py**
  - Import: `import fitz  # PyMuPDF`
  - Usage: Direct PDF text extraction using `fitz.open()`
  - Key methods:
    - `extract_text()`: Full document text extraction
    - `extract_text_by_pages()`: Page-level extraction with metadata
  - Features:
    - Multi-page handling
    - Page metadata (page numbers, char positions)
    - Text validation (minimum length checks)

#### 2. Docling Backend Already Implemented
- **libs/extraction/backend_docling.py** ✅
  - Already implements DoclingBackend class
  - Extends PDFParserBackend interface
  - Vision-based structure extraction with table preservation
  - Deterministic configuration (single-threaded, CPU-only)

- **libs/extraction/parser_backend.py**
  - Abstract base class for PDF backends
  - Defines standard interface for all parsers

#### 3. Structure-Aware Chunker Integration
- **libs/chunking/structure_aware_chunker.py** ✅
  - Already has Docling support via `use_docling` parameter
  - Falls back to basic chunking if Docling not available
  - Preserves markdown structure (headers, tables, lists)

### Migration Impact Analysis

#### Files Requiring Refactoring
1. **agents/extraction/pdf_text_extractor.py**
   - Current: Direct PyMuPDF usage
   - Required: Refactor to use DoclingBackend
   - Impact: High - Core CP module

2. **scripts/edgar_validate.py**
   - May use pdf_text_extractor
   - Required: Update imports and calls

3. **scripts/chunk_cli.py**
   - May instantiate chunker with PyMuPDF
   - Required: Ensure use_docling=True

4. **scripts/hybrid_cli.py**
   - May use extraction components
   - Required: Verify backend selection

#### Files Already Migrated
1. **libs/extraction/backend_docling.py** ✅
2. **libs/chunking/structure_aware_chunker.py** ✅
3. **agents/retrieval/hybrid_retriever.py** ✅

### PyMuPDF API Usage Patterns

#### Pattern 1: Basic Document Opening
```python
import fitz
doc = fitz.open(pdf_path)
```

#### Pattern 2: Page Iteration
```python
for page_num, page in enumerate(doc):
    text = page.get_text()
```

#### Pattern 3: Text Extraction with Positions
```python
text = page.get_text()
char_count = len(text)
```

#### Pattern 4: Document Cleanup
```python
doc.close()
```

### Docling Equivalent Patterns

#### Pattern 1: Backend Initialization
```python
from libs.extraction.backend_docling import DoclingBackend
backend = DoclingBackend()
```

#### Pattern 2: Document Processing
```python
pages = backend.parse_pdf_to_pages(pdf_path, doc_id)
```

#### Pattern 3: Structure-Aware Extraction
```python
for page in pages:
    text = page['text']  # Markdown with tables
    page_num = page['page']
```

### Validation Requirements

#### Before Migration
- [ ] All tests passing with PyMuPDF
- [ ] Baseline performance metrics captured
- [ ] Sample outputs archived

#### After Migration
- [ ] All tests passing with Docling
- [ ] Performance comparison documented
- [ ] Table extraction validated
- [ ] Deterministic output verified

### Risk Assessment

#### Low Risk
- Structure-aware chunker: Already supports both backends
- Backend abstraction: Clean interface separation

#### Medium Risk
- pdf_text_extractor: Direct PyMuPDF coupling
- Scripts: May have hardcoded assumptions

#### High Risk
- None identified - Docling backend already implemented

### Migration Strategy

#### Phase 1.1: Backend Switch
1. Update pdf_text_extractor to use DoclingBackend
2. Remove direct fitz imports
3. Maintain API compatibility

#### Phase 1.2: Script Updates
1. Update all scripts to use new backend
2. Set use_docling=True in chunkers
3. Verify offline model caching

#### Phase 1.3: Test Migration
1. Update test fixtures if needed
2. Add Docling-specific tests
3. Verify determinism with fixed seeds

### Dependencies to Update

#### Remove
- `PyMuPDF>=1.23.0`

#### Add/Verify
- `docling>=2.60.0`
- Model cache requirements

### Performance Expectations

#### PyMuPDF (Current)
- Speed: ~0.5-1 second per document
- Table extraction: None
- Structure preservation: Basic

#### Docling (Target)
- Speed: ~3-6 seconds per document
- Table extraction: 100% with markdown
- Structure preservation: Advanced (headers, lists, tables)

### Success Criteria

1. **Functional**
   - All PDF extraction working
   - Table extraction improved
   - Structure preservation enhanced

2. **Non-Functional**
   - Deterministic output (fixed seeds)
   - Offline operation (cached models)
   - <10 second processing time per document

3. **Quality Gates**
   - All tests passing
   - 95%+ code coverage maintained
   - No new static analysis violations

### Conclusion

The migration from PyMuPDF to Docling is well-positioned for success:
- DoclingBackend already implemented and tested
- Structure-aware chunker supports both backends
- Only pdf_text_extractor requires refactoring
- Clear migration path with minimal risk

**Recommendation:** Proceed with Phase 1 migration immediately.

---
*End of PyMuPDF Usage Documentation*