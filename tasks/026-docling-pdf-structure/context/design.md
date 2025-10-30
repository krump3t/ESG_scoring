# Task 026: Docling PDF Structure Extraction — Design & Architecture

**Task ID**: 026-docling-pdf-structure
**Phase**: Enhancement (PDF Processing Layer)
**Date**: 2025-10-30

---

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                    ESG Scoring Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐      ┌──────────────┐      ┌────────────┐ │
│  │   PDF Files │─────▶│ Extraction   │─────▶│   Silver   │ │
│  │  (Bronze)   │      │   Backend    │      │  (Parquet) │ │
│  └─────────────┘      └──────────────┘      └────────────┘ │
│                              │                               │
│                              │ [Task 026 Focus]              │
│                              ▼                               │
│              ┌───────────────────────────────┐              │
│              │  Parallel Backend Selection   │              │
│              │  ┌─────────────────────────┐  │              │
│              │  │ PARSER_BACKEND env var  │  │              │
│              │  └─────────────────────────┘  │              │
│              │           │         │         │              │
│              │  ┌────────▼──┐   ┌─▼──────┐  │              │
│              │  │  default  │   │docling │  │              │
│              │  │ PyMuPDF   │   │Vision  │  │              │
│              │  └───────────┘   └────────┘  │              │
│              └───────────────────────────────┘              │
│                       │           │                          │
│              ┌────────▼───────────▼──────┐                  │
│              │   Silver Locator         │                  │
│              │   Dynamic Path Resolver   │                  │
│              └───────────────────────────┘                  │
│                              │                               │
│                              ▼                               │
│              ┌───────────────────────────┐                  │
│              │  Downstream Consumers     │                  │
│              │  - Retrieval              │                  │
│              │  - Scoring                │                  │
│              │  - Evidence Extraction    │                  │
│              └───────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Design Principles

### 1. **Parallel Backend Architecture**
- **Strategy**: Two independent extraction backends, selectable via environment variable
- **Rationale**: Zero-risk deployment; instant rollback; side-by-side comparison
- **Implementation**: Protocol-based polymorphism (`PDFParserBackend`)

### 2. **Fail-Closed Validation**
- **Strategy**: Alignment audit, determinism tests, coverage gates must pass
- **Rationale**: Prevent silent quality regressions
- **Implementation**: Exit code 2 on failure; CI blocks merge

### 3. **Determinism-First**
- **Strategy**: Single-threaded, CPU-only, fixed seeds
- **Rationale**: Reproducibility is non-negotiable for scientific computing
- **Implementation**: Environment variables + PyTorch configuration

### 4. **Authentic Computation**
- **Strategy**: Real library calls, real PDFs, real differential tests
- **Rationale**: SCA v13.8 authenticity invariants
- **Implementation**: No mocks in production; fixtures only in unit tests

---

## Data Strategy

### Directory Layout

```
data/
├── raw/                          # Bronze: Original PDFs
│   ├── LSE_HEAD_2025.pdf
│   ├── AAPL_2023.pdf
│   └── JPM_2023.pdf
├── silver/                       # Default backend (PyMuPDF)
│   └── org_id=LSE_HEAD/
│       └── year=2025/
│           ├── LSE_HEAD_2025_chunks.parquet
│           └── LSE_HEAD_2025_chunks.parquet.prov.json
└── silver_docling/               # Docling backend (NEW)
    └── org_id=LSE_HEAD/
        └── year=2025/
            ├── LSE_HEAD_2025_chunks.parquet
            └── LSE_HEAD_2025_chunks.parquet.prov.json
```

**Design Decisions**:
- **Separate directories**: Prevents accidental overwrites; allows A/B comparison
- **Identical schemas**: Same columns (`doc_id, page, text, chunk_id`)
- **Provenance sidecars**: Track backend, source PDF SHA256, metadata

### Schema Specification

**Parquet Schema** (both backends):
```python
{
    "doc_id": str,       # Example: "LSE_HEAD_2025"
    "page": int,         # 1-indexed page number
    "text": str,         # Extracted text (default: plain, docling: markdown tables)
    "chunk_id": str      # Format: "{doc_id}_p{page:04d}_00"
}
```

**Provenance Sidecar Schema** (JSON):
```json
{
    "doc_id": "LSE_HEAD_2025",
    "org_id": "LSE_HEAD",
    "year": 2025,
    "backend": "docling",
    "source_pdf": "data/raw/LSE_HEAD_2025.pdf",
    "source_pdf_sha256": "abc123...",
    "row_count": 127,
    "schema_version": "1.0",
    "extraction_timestamp": "2025-10-30T12:34:56Z",
    "environment": {
        "SEED": "42",
        "PYTHONHASHSEED": "0",
        "DOCLING_THREADS": "1"
    }
}
```

---

## Component Design

### 1. Parser Backend Protocol

**File**: `libs/extraction/parser_backend.py`

**Purpose**: Define extraction interface using Protocol (PEP 544)

**Interface**:
```python
from typing import Protocol, List, Dict, Any

class PDFParserBackend(Protocol):
    """Protocol for PDF extraction backends.

    Implementations must provide deterministic, page-based extraction
    with standardized output schema.
    """

    def parse_pdf_to_pages(self, pdf_path: str, doc_id: str) -> List[Dict[str, Any]]:
        """Extract page-based chunks from PDF.

        Args:
            pdf_path: Absolute path to PDF file
            doc_id: Unique document identifier

        Returns:
            List of dicts with schema:
            {
                "doc_id": str,
                "page": int,  # 1-indexed
                "text": str,
                "chunk_id": str
            }
        """
        ...
```

**Design Rationale**:
- **Protocol over ABC**: Structural typing; no inheritance required
- **Single method**: Simple interface; easy to test
- **Standardized output**: All backends return same schema

---

### 2. Default Backend (PyMuPDF)

**File**: `libs/extraction/backend_default.py`

**Purpose**: Maintain existing PyMuPDF extraction behavior

**Implementation**:
```python
class DefaultBackend:
    def parse_pdf_to_pages(self, pdf_path: str, doc_id: str) -> List[Dict]:
        # 1. Open PDF with PyMuPDF (fitz)
        # 2. Iterate pages, extract text
        # 3. Return standardized schema with source="default"
        ...
```

**Key Characteristics**:
- **Text-only extraction**: `page.get_text("text")`
- **No structure preservation**: Tables → narrative text
- **Fast**: ~1-2 seconds per document
- **Deterministic**: Same PDF → same text (byte-for-byte)

---

### 3. Docling Backend

**File**: `libs/extraction/backend_docling.py`

**Purpose**: Advanced extraction with tables, layout, OCR

**Implementation**:
```python
class DoclingBackend:
    def __init__(self):
        # Configure PyTorch for determinism
        torch.manual_seed(SEED)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

        # Initialize DocumentConverter
        self.converter = DocumentConverter()

    def parse_pdf_to_pages(self, pdf_path: str, doc_id: str) -> List[Dict]:
        # 1. Convert PDF to DoclingDocument
        result = self.converter.convert(pdf_path)

        # 2. Extract page-level text (includes tables as markdown)
        pages = []
        for page in result.document.pages:
            pages.append({
                "doc_id": doc_id,
                "page": page.number,
                "text": page.plain_text,  # Tables formatted as markdown
                "chunk_id": _mk_chunk_id(doc_id, page.number, 0),
                "source": "docling"
            })

        return pages
```

**Key Characteristics**:
- **Structure-aware**: Tables preserved as markdown
- **Vision-based**: Layout analysis via deep learning
- **OCR-capable**: Handles scanned PDFs
- **Slower**: ~3-6 seconds per document (2-3x PyMuPDF)
- **Deterministic**: Requires careful configuration (CPU-only, single-threaded)

---

### 4. Silver Locator (Dynamic Path Resolution)

**File**: `libs/retrieval/silver_locator.py`

**Purpose**: Abstract silver directory location based on backend

**Implementation**:
```python
def locate_chunks_parquet(doc_id: str, org_id: str, year: int) -> str:
    """Locate chunks parquet file for given document.

    Strategy:
    1. Read PARSER_BACKEND environment variable
    2. If "docling", try silver_docling/ first
    3. Fall back to silver/ (default)
    4. Return path or empty string if not found
    """
    prefer_docling = (os.getenv("PARSER_BACKEND", "default") == "docling")

    if prefer_docling:
        docling_path = f"data/silver_docling/org_id={org_id}/year={year}/{doc_id}_chunks.parquet"
        if os.path.exists(docling_path):
            return docling_path

    default_path = f"data/silver/org_id={org_id}/year={year}/{doc_id}_chunks.parquet"
    return default_path if os.path.exists(default_path) else ""
```

**Design Decisions**:
- **Thread-safe**: Read-only environment variable access
- **Fallback logic**: Always try default if preferred not found
- **No caching**: Stateless function (can be called repeatedly)

---

### 5. Text Quality Module

**File**: `libs/extraction/text_clean.py`

**Purpose**: Detect and clean binary artifacts, assess text quality

**Functions**:
1. `is_binary_like(text: str) -> bool`
   - Detects null bytes, excessive control characters
   - Threshold: >2% control chars → binary

2. `clean_text(text: str) -> str`
   - Removes control chars (except \t, \n, \r)
   - Normalizes whitespace

3. `quality_score(text: str) -> float`
   - Returns 0.0-1.0 based on binary detection
   - 1.0 = clean text, 0.0 = empty/binary

4. `extract_clean_quote(text: str, max_length: int) -> Tuple[str, float]`
   - Clean + score + truncate

**Use Case**: Evidence quote selection (filter out PDF artifacts like "%PDF-1.4")

---

### 6. PDF to Silver Converter

**File**: `scripts/pdf_to_silver.py`

**Purpose**: CLI tool for batch PDF extraction

**Workflow**:
```
1. Parse arguments (--org_id, --year, --doc_id, --backend)
2. Locate PDF file (data/raw/ or auto-detect)
3. Select backend (pick_backend("default" | "docling"))
4. Extract pages (backend.parse_pdf_to_pages())
5. Write parquet (standardized schema)
6. Generate provenance sidecar (*.prov.json)
7. Print success message
```

**CLI Interface**:
```powershell
python scripts/pdf_to_silver.py \
    --org_id LSE_HEAD \
    --year 2025 \
    --doc_id LSE_HEAD_2025 \
    --backend docling
```

**Design Decisions**:
- **CLI-first**: Scriptable for batch processing
- **Auto-detect PDF**: Search data/raw/ if --pdf not provided
- **Provenance mandatory**: Always generate sidecar
- **Idempotent**: Safe to run multiple times (overwrites)

---

### 7. Alignment Audit

**File**: `scripts/alignment_audit.py`

**Purpose**: Validate evidence quotes against source PDFs

**Workflow**:
```
1. Find all evidence_audit.json files
2. For each document:
   a. Locate source PDF via provenance sidecar
   b. Extract ground-truth page text (PyMuPDF)
   c. Verify each quote appears on claimed page
   d. Compute per-page SHA256 hashes
3. Write failures to alignment_failures.json
4. Exit code 2 if any failures
```

**Validation Logic**:
```python
for theme in audit_data["themes"]:
    for evidence in theme["evidence"]:
        quote = evidence["quote"]
        page_num = evidence["page"]

        page_text = extract_page_text(pdf_path, page_num)

        if quote not in page_text:
            failures.append({
                "doc": doc_id,
                "theme": theme_name,
                "page": page_num,
                "quote_preview": quote[:120]
            })
```

**Design Decisions**:
- **Fail-closed**: Any mismatch → exit code 2
- **Ground truth**: Use PyMuPDF (not Docling) to avoid circular dependency
- **Page hashes**: SHA256 of each page for provenance

---

## Verification Plan

### Differential Testing

**Objective**: Validate Docling extracts same source content as default backend

**Method**: Jaccard similarity of text chunks

**Procedure**:
```python
def compute_parity(default_df, docling_df) -> float:
    """Compute extraction parity score.

    Returns:
        Jaccard similarity (0.0-1.0) of text content
    """
    default_text = set(" ".join(default_df["text"]).split())
    docling_text = set(" ".join(docling_df["text"]).split())

    intersection = len(default_text & docling_text)
    union = len(default_text | docling_text)

    return intersection / union if union > 0 else 0.0
```

**Threshold**: Parity ≥ 0.85 (85% overlap)

**Rationale**: Some formatting differences expected (tables → markdown), but core content must match

---

### Determinism Testing

**Objective**: Validate byte-for-byte reproducibility

**Method**: SHA256 hash comparison across 3 runs

**Procedure**:
```powershell
for ($i=1; $i -le 3; $i++) {
    Remove-Item data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet -ErrorAction SilentlyContinue

    python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend docling

    $hash = (Get-FileHash data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet).Hash
    Write-Output "Run $i: $hash"
}
```

**Success Criteria**: All 3 hashes identical

---

### Sensitivity Analysis

**Objective**: Validate determinism holds across different seeds

**Method**: Vary SEED, verify output changes deterministically

**Procedure**:
```powershell
$seeds = @(42, 123, 999)

foreach ($seed in $seeds) {
    $env:SEED = $seed

    # Run twice with same seed
    python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend docling
    $hash1 = (Get-FileHash data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet).Hash

    Remove-Item data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet
    python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend docling
    $hash2 = (Get-FileHash data/silver_docling/org_id=LSE_HEAD/year=2025/LSE_HEAD_2025_chunks.parquet).Hash

    if ($hash1 -eq $hash2) {
        Write-Host "✅ Seed $seed: Deterministic"
    } else {
        Write-Host "❌ Seed $seed: Non-deterministic"
    }
}
```

**Success Criteria**: All seeds produce deterministic output (hash1 == hash2 within seed)

---

## Success Thresholds

| Metric | Target | Validation |
|--------|--------|------------|
| **Extraction parity** | ≥85% | Jaccard similarity of text content |
| **Table capture rate** | 100% | Manual review: all tables → markdown |
| **Determinism** | 100% | 3 runs → identical SHA256 |
| **Latency** | <30s per doc | Acceptable for quality improvement |
| **Coverage** | ≥95% | pytest-cov on CP modules |
| **Alignment** | 100% | All quotes found on claimed pages |

---

## Data Normalization & Leakage Guards

### Normalization

**Challenge**: Docling may produce different whitespace, formatting than PyMuPDF

**Solution**: Schema guards after read_parquet

```python
df = pd.read_parquet(path)

# Handle legacy column names
if 'text' not in df.columns and 'extract_30w' in df.columns:
    df = df.rename(columns={'extract_30w': 'text'})

if 'page' not in df.columns and 'page_no' in df.columns:
    df = df.rename(columns={'page_no': 'page'})

# Validate required columns
assert {'text', 'page'}.issubset(df.columns), 'Missing required columns'
```

### Leakage Guards

**No leakage risk**: PDF extraction is deterministic preprocessing (no training data contamination)

**Provenance tracking**: SHA256 of source PDFs ensures no untracked modifications

---

## Rollback Strategy

### Trigger Conditions

Rollback if:
1. Determinism tests fail (3 runs produce different hashes)
2. Alignment audit fails (quotes not found on claimed pages)
3. Parity score <85% (Docling extracts different content)
4. Performance unacceptable (>60s per document)
5. Production issues (downstream consumers break)

### Rollback Procedure

```powershell
# Step 1: Set backend to default
$env:PARSER_BACKEND="default"

# Step 2: Verify default backend works
python scripts/pdf_to_silver.py --org_id LSE_HEAD --year 2025 --doc_id LSE_HEAD_2025 --backend default
pytest tests/cp/test_cp_gates.py

# Step 3: Clean Docling artifacts (optional)
Remove-Item -Recurse data/silver_docling

# Step 4: Update environment configs
# Edit .env, docker-compose.yml, Dockerfile to default backend

# Step 5: Re-run validation
python scripts/run_matrix.py --config configs/companies_local.yaml
pytest -k "cp"
```

### Recovery Time Objective (RTO)

- **Detection**: <5 minutes (CI fails immediately)
- **Rollback**: <2 minutes (environment variable change)
- **Validation**: <10 minutes (re-run CP tests)
- **Total RTO**: <20 minutes

---

## Dependencies

### Runtime Dependencies

```
docling==0.12.0          # Document AI library
pymupdf==1.24.10         # PyMuPDF (compatible with Docling)
pillow>=10.0.0           # Image processing
torch>=2.0.0             # Deep learning (CPU-only)
transformers>=4.30.0     # Vision models
pandas>=2.0.0            # DataFrame operations
pyarrow>=12.0.0          # Parquet I/O
```

### Development Dependencies

```
pytest>=7.0.0            # Test framework
pytest-cov>=4.0.0        # Coverage reporting
hypothesis>=6.0.0        # Property testing
mypy>=1.0.0              # Type checking
```

---

## Configuration Management

### Environment Variables

```bash
# Core determinism
SEED=42
PYTHONHASHSEED=0

# Backend selection
PARSER_BACKEND=docling  # or "default"

# Docling configuration
DOCLING_THREADS=1
DOCLING_DISABLE_GPU=1
DOCLING_CACHE_DIR=./artifacts/cache/docling

# Offline mode
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

### Configuration Files

**`.env`** (local development):
```bash
PARSER_BACKEND=docling
SEED=42
PYTHONHASHSEED=0
DOCLING_THREADS=1
DOCLING_DISABLE_GPU=1
```

**`docker-compose.yml`** (production):
```yaml
services:
  esg-scoring:
    environment:
      - PARSER_BACKEND=docling
      - SEED=42
      - PYTHONHASHSEED=0
      - DOCLING_THREADS=1
      - DOCLING_DISABLE_GPU=1
```

---

## Monitoring & Observability

### Metrics to Track

1. **Extraction latency**: Time per document (default vs Docling)
2. **Determinism rate**: % of runs producing identical hashes
3. **Parity score**: Jaccard similarity (default vs Docling)
4. **Table capture rate**: % of tables preserved as markdown
5. **Alignment failures**: Count of mismatched quotes

### Logging Strategy

```python
import logging

logger = logging.getLogger(__name__)

# Log extraction events
logger.info(f"Extracting {doc_id} with {backend} backend")
logger.info(f"Extracted {len(rows)} pages in {elapsed_time:.2f}s")

# Log determinism checks
logger.info(f"Hash: {sha256_hash}")

# Log alignment failures
logger.error(f"Quote not found on page {page_num}: {quote[:50]}...")
```

### Artifacts for Debugging

1. **Provenance sidecars**: Full metadata for each extraction
2. **Page hash manifest**: Per-page SHA256 for reproducibility
3. **Alignment failures**: Detailed list of mismatches
4. **Determinism report**: Hash comparison across runs

---

**End of design.md**
