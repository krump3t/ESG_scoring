# Task 037: Remediation Design - Authentic Implementation

## Overview

Transform experimental stub/wrapper modules into authentic, production-grade implementations with proper infrastructure integration, CLI interfaces, and comprehensive validation. Replace simple wrappers with real algorithms and data structures.

---

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                   Task 037 Remediation                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Structure   │  │   Hybrid     │  │  LangGraph   │      │
│  │    Aware     │→ │  Retriever   │→ │ Orchestrator │      │
│  │   Chunker    │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                 ↓                   ↓             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PyMuPDF     │  │  BM25 Index  │  │   SQLite     │      │
│  │  Font        │  │  AstraDB     │  │  Checkpoint  │      │
│  │  Analysis    │  │  Embeddings  │  │  StateGraph  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │         Utility Scripts (8)                        │     │
│  │  CLI Gen │ CP Update │ Context │ Design │ QA      │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Structure-Aware Chunker

**File:** `libs/chunking/structure_aware_chunker.py`

**Design Goals:**
- Real PDF parsing with PyMuPDF (not naive text splitting)
- Font-based header detection (size, weight, style)
- Table boundary preservation (no mid-table splits)
- List/bullet point awareness
- Paragraph-level semantic boundaries

**Algorithm:**
```python
1. Load PDF with PyMuPDF
2. Extract pages with layout info
3. For each page:
   a. Identify headers (font size > threshold)
   b. Detect tables (layout analysis)
   c. Detect lists (bullet patterns)
   d. Split paragraphs (double newlines)
4. Create chunks respecting boundaries:
   a. Never split mid-table
   b. Never split mid-list
   c. Prefer paragraph boundaries
   d. Target 512 tokens ± 50
5. Attach metadata:
   a. section_title (from headers)
   b. page_num
   c. chunk_type (header/table/list/text)
   d. char_start, char_end
```

**Data Structures:**
```python
@dataclass
class Chunk:
    text: str
    page_num: int
    chunk_type: ChunkType  # Enum: HEADER, TABLE, LIST, TEXT
    section_title: str
    char_start: int
    char_end: int
    metadata: Dict[str, Any]

class StructureAwareChunker:
    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.tokenizer = SimpleTokenizer()

    def chunk_pdf(self, pdf_path: str) -> List[Chunk]:
        """Main entry point"""
        doc = fitz.open(pdf_path)
        chunks = []
        current_section = ""

        for page_num, page in enumerate(doc):
            page_chunks = self._process_page(page, page_num, current_section)
            chunks.extend(page_chunks)
            # Update section from last header found
            headers = [c for c in page_chunks if c.chunk_type == ChunkType.HEADER]
            if headers:
                current_section = headers[-1].text

        return chunks

    def _process_page(self, page, page_num, section) -> List[Chunk]:
        # Font analysis for headers
        # Table detection
        # List detection
        # Paragraph splitting
        # Chunk assembly
        pass
```

**Verification Strategy:**
- Test with varied PDFs (reports, papers, forms)
- Validate no mid-table splits
- Validate header detection accuracy
- Validate chunk size distribution (mean=512, std<100)

---

### 2. Hybrid Retriever

**File:** `agents/retrieval/hybrid_retriever.py`

**Design Goals:**
- Build BM25 index from parquet chunks
- Connect to AstraDB for vector search
- Embed queries with SentenceTransformer
- Fuse results with RRF
- Single unified API

**Algorithm:**
```python
1. Load chunks from parquet
2. Build BM25 index (tokenize all chunks) using build_bm25_index()
3. Connect to AstraDB (credentials from args/env)
4. Load embedding model (SentenceTransformer)
5. For each query:
   a. BM25 search(bm25_index, chunks_df, query, k) → top-k results
   b. Embed query with SentenceTransformer → 768-dim vector
   c. AstraDB search_vector_astra(collection, embedding, k) → top-k results
   d. RRF fusion(bm25_results, vector_results, k_param) → final top-k
6. Return fused results
```

**Data Structures (CORRECTED - Task 037):**
```python
@dataclass
class RetrievalConfig:
    k_bm25: int = 40
    k_vec: int = 40
    rrf_k: int = 60
    enable_bm25: bool = True
    enable_vector: bool = True

class HybridRetriever:
    def __init__(
        self,
        chunks_path: str,
        astra_endpoint: Optional[str] = None,
        astra_token: Optional[str] = None,
        collection_name: str = "chunks",
        embedding_model: str = "sentence-transformers/all-mpnet-base-v2",
        config: Optional[RetrievalConfig] = None
    ):
        self.config = config or RetrievalConfig()

        # Load chunks DataFrame
        self.chunks_df = pd.read_parquet(chunks_path)

        # Build BM25 index (if enabled)
        if self.config.enable_bm25:
            from libs.retrieval.bm25_search import build_bm25_index
            self.bm25_index, self.tokenized_corpus = build_bm25_index(self.chunks_df)

        # Connect to Astra and load embedder (if vector enabled)
        if self.config.enable_vector:
            from astrapy import DataAPIClient
            from sentence_transformers import SentenceTransformer

            client = DataAPIClient(astra_token)
            database = client.get_database_by_api_endpoint(astra_endpoint)
            self.collection = database.get_collection(collection_name)
            self.embedding_model = SentenceTransformer(embedding_model)

    def retrieve(self, query: str) -> List[Dict]:
        bm25_results = []
        vector_results = []

        if self.config.enable_bm25:
            bm25_results = self._execute_bm25(query)

        if self.config.enable_vector:
            vector_results = self._execute_vector(query)

        # Return single method results or fuse
        if not self.config.enable_bm25:
            return vector_results
        if not self.config.enable_vector:
            return bm25_results

        return self._execute_fusion(bm25_results, vector_results)

    def _execute_bm25(self, query: str) -> List[Dict]:
        from libs.retrieval.bm25_search import search_bm25

        # CORRECT SIGNATURE: (bm25_index, chunks_df, query, k)
        results = search_bm25(
            self.bm25_index,
            self.chunks_df,
            query,
            k=self.config.k_bm25
        )
        return results

    def _execute_vector(self, query: str) -> List[Dict]:
        from libs.retrieval.vector_search_astra import search_vector_astra

        # Generate embedding
        query_embedding = self.embedding_model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )[0]

        # CORRECT SIGNATURE: (collection, query_embedding, k)
        results = search_vector_astra(
            self.collection,
            query_embedding,
            k=self.config.k_vec
        )
        return results

    def _execute_fusion(self, bm25_results, vector_results):
        from libs.fusion.rrf_fusion import rrf_fusion

        # CORRECT SIGNATURE: (bm25_results, vector_results, k_param)
        fused = rrf_fusion(
            bm25_results,
            vector_results,
            k_param=self.config.rrf_k
        )
        return fused
```

**API Fixes Applied (Task 037):**
- ✅ Fixed: `search_astra` → `search_vector_astra`
- ✅ Fixed: `fuse_rrf` → `rrf_fusion`
- ✅ Fixed: BM25 signature requires `(bm25_index, chunks_df, query, k)`
- ✅ Fixed: Vector signature requires `(collection, query_embedding, k)`
- ✅ Fixed: RRF parameter `k` → `k_param`
- ✅ Added: Real infrastructure building in `__init__`
- ✅ Added: Optional Astra for BM25-only mode

**Verification Strategy:**
- NO MOCKS: Use real BM25 indices from test data
- Astra tests are conditional (skip if credentials unavailable)
- Test BM25-only, vector-only, and hybrid modes
- Validate error handling (missing files, empty queries, missing credentials)
- Test with Unicode queries, long queries, batch retrieval
- Validate retrieval returns correct structure with all fields

---

### 3. LangGraph Orchestrator

**File:** `agents/orchestrator/langgraph_runner.py`

**Design Goals:**
- Real LangGraph StateGraph (not just JSON logging)
- LLM-driven router node (temperature=0)
- Conditional edges based on query type
- SQLite checkpointing for state persistence
- JSONL trace logging

**Algorithm:**
```python
1. Define state schema (query, route, results, metadata)
2. Create StateGraph
3. Add nodes:
   a. router (LLM classifies query type)
   b. keyword (BM25 search)
   c. semantic (vector search)
   d. hybrid (BM25 + vector + RRF)
   e. direct (SQL/graph query)
4. Add conditional edges from router
5. Compile with SQLite checkpointer
6. Execute graph for each query
7. Log events to JSONL
```

**Data Structures:**
```python
class OrchestratorState(TypedDict):
    query: str
    route: Optional[str]  # "keyword" | "semantic" | "hybrid" | "direct"
    results: List[Dict]
    metadata: Dict[str, Any]
    error: Optional[str]

class RouteType(Enum):
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    DIRECT = "direct"

class LangGraphRunner:
    def __init__(self, checkpoint_path: str = "checkpoints.db", trace_file: str = "trace.jsonl"):
        self.checkpoint_path = checkpoint_path
        self.trace_file = trace_file
        self.checkpointer = SqliteSaver.from_conn_string(checkpoint_path)
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledGraph:
        workflow = StateGraph(OrchestratorState)

        # Add nodes
        workflow.add_node("router", self._router_node)
        workflow.add_node("keyword", self._keyword_node)
        workflow.add_node("semantic", self._semantic_node)
        workflow.add_node("hybrid", self._hybrid_node)
        workflow.add_node("direct", self._direct_node)

        # Set entry point
        workflow.set_entry_point("router")

        # Conditional edges from router
        workflow.add_conditional_edges(
            "router",
            self._route_query,
            {
                RouteType.KEYWORD.value: "keyword",
                RouteType.SEMANTIC.value: "semantic",
                RouteType.HYBRID.value: "hybrid",
                RouteType.DIRECT.value: "direct",
            }
        )

        # All execution nodes end
        for node in ["keyword", "semantic", "hybrid", "direct"]:
            workflow.add_edge(node, END)

        return workflow.compile(checkpointer=self.checkpointer)

    def _router_node(self, state: OrchestratorState) -> OrchestratorState:
        # LLM classifies query type (temperature=0 for determinism)
        # Prompt: "Classify this query into: keyword, semantic, hybrid, direct"
        pass

    def _route_query(self, state: OrchestratorState) -> str:
        return state["route"]

    def _keyword_node(self, state: OrchestratorState) -> OrchestratorState:
        # Execute BM25 search
        pass

    def _semantic_node(self, state: OrchestratorState) -> OrchestratorState:
        # Execute vector search
        pass

    def _hybrid_node(self, state: OrchestratorState) -> OrchestratorState:
        # Execute hybrid retrieval
        pass

    def _direct_node(self, state: OrchestratorState) -> OrchestratorState:
        # Execute SQL/graph query (placeholder)
        pass

    def run(self, query: str) -> Dict:
        initial_state = {
            "query": query,
            "route": None,
            "results": [],
            "metadata": {},
            "error": None
        }

        result = self.graph.invoke(initial_state)
        self._log_trace(result)
        return result

    def _log_trace(self, state: Dict):
        with open(self.trace_file, 'a') as f:
            f.write(json.dumps(state) + '\n')
```

**Verification Strategy:**
- Test router with deterministic LLM (temperature=0)
- Test all execution nodes independently
- Test checkpoint save/restore
- Validate trace logging format

---

## Utility Scripts Design

### 1. generate_cli_wrapper.py

**Purpose:** Generate CLI wrapper for library module

**Interface:**
```bash
python scripts/generate_cli_wrapper.py <module_path> --entry <function> --out <cli_script>
```

**Algorithm:**
```python
1. Parse module to find entry function
2. Extract function signature (args, types, defaults)
3. Generate argparse code
4. Generate function call with arg mapping
5. Generate output serialization (JSON/parquet)
6. Write CLI script
```

---

### 2. update_cp_manifest.py

**Purpose:** Update CP manifest with new files

**Interface:**
```bash
python scripts/update_cp_manifest.py <manifest_path> <cp_file1> <cp_file2> ...
```

**Algorithm:**
```python
1. Load existing manifest JSON
2. Add new CP files to "cp" array
3. Deduplicate
4. Update timestamp/note
5. Write manifest
```

---

### 3. context_report_assembler.py

**Purpose:** Assemble context documentation from multiple tasks

**Interface:**
```bash
python scripts/context_report_assembler.py --tasks 031 032 033 --out report.md
```

**Algorithm:**
```python
1. For each task:
   a. Load all context files
   b. Extract key info (CP files, status, evidence)
2. Generate consolidated report
3. Include traceability matrix
4. Write markdown
```

---

### 4. update_design_refs.py

**Purpose:** Update design.md with implementation references

**Interface:**
```bash
python scripts/update_design_refs.py <design_md> <impl_file>
```

**Algorithm:**
```python
1. Parse design.md for claims/features
2. Scan impl_file for matching functions/classes
3. Add code references to design doc
4. Generate traceability links
5. Update design.md
```

---

### 5. reconcile_plan.py

**Purpose:** Validate plan vs implementation alignment

**Interface:**
```bash
python scripts/reconcile_plan.py --tasks 031 032 033 --out reconciliation.json
```

**Algorithm:**
```python
1. Load hypothesis.md for each task
2. Extract claimed deliverables
3. Check if files exist
4. Check if tests exist
5. Generate alignment report
6. Report gaps
```

---

### 6. qa_sweep.py

**Purpose:** Run comprehensive QA validation

**Interface:**
```bash
python scripts/qa_sweep.py --tasks 031 032 033 --out STATUS.json
```

**Algorithm:**
```python
1. Run pytest with coverage
2. Run mypy type checking
3. Run bandit security scan
4. Check import bans
5. Validate CP manifests
6. Generate status JSON
```

---

### 7. emit_contract.py

**Purpose:** Generate output contract JSON

**Interface:**
```bash
python scripts/emit_contract.py --tasks 031 032 033 --out contract.json
```

**Algorithm:**
```python
1. Collect all artifacts
2. Compute rubric SHA256
3. Check determinism results
4. Generate contract JSON with:
   - agent, model, protocol_version
   - status, e2e_determinism, coverage
   - artifacts list
5. Write contract
```

---

### 8. finalize_validation.py

**Purpose:** Generate final validation report

**Interface:**
```bash
python scripts/finalize_validation.py --tasks 031 032 033 --out FINAL.md
```

**Algorithm:**
```python
1. Load all validation artifacts
2. Check all gates (coverage, determinism, etc.)
3. Generate promotion decision
4. Create markdown report
5. Include all metrics
```

---

## CLI Wrapper Design

### Pattern for All CLI Wrappers

```python
#!/usr/bin/env python
"""CLI wrapper for <module_name>"""
import argparse
import json
import sys
from pathlib import Path

# Import the library module
from <module_path> import <MainClass>

def main():
    parser = argparse.ArgumentParser(description="<Description>")

    # Add arguments based on function signature
    parser.add_argument('--arg1', required=True, help="...")
    parser.add_argument('--arg2', type=int, default=10, help="...")
    parser.add_argument('--out', required=True, help="Output path")

    args = parser.parse_args()

    try:
        # Initialize module with infrastructure setup
        instance = <MainClass>(
            arg1=args.arg1,
            arg2=args.arg2,
            # ... infrastructure setup (DB connections, models, etc.)
        )

        # Execute main function
        results = instance.run()

        # Serialize output
        Path(args.out).write_text(json.dumps(results, indent=2))
        print(f"SUCCESS: {len(results)} results")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

---

## Data Strategy

### Input Data
- **Chunks:** `artifacts/ingestion/chunks.parquet`
- **Rubric:** `rubrics/esg_rubric_schema_v3.json`
- **Queries:** `configs/seed_queries_033.json`
- **PDFs:** `data/raw/*.pdf`

### Output Data
- **Retrieval:** `artifacts/demo/retrieval_topk.json`
- **Scoring:** `artifacts/demo/scoring_report.json`
- **Evidence:** `artifacts/demo/evidence.json`
- **Maturity:** `artifacts/demo/maturity.parquet`
- **Traces:** `artifacts/demo/run_events.jsonl`
- **Coverage:** `artifacts/diagnostics/coverage_core.xml`

### Leakage Prevention
- No test data in training
- Separate dev/test/validation sets
- Deterministic splitting (SEED=42)
- No information flow from future to past

---

## Verification Plan

### Unit Tests
- Each module has ≥95% coverage
- Each function has ≥1 test
- Property tests with Hypothesis
- Failure path tests

### Integration Tests
- BM25 + AstraDB + RRF pipeline
- Chunker → Embedder → Indexer
- Orchestrator → Retriever → Scorer
- ≥5 test cases per integration

### E2E Tests
- Full pipeline: PDF → Chunks → Embed → Index → Retrieve → Score
- 3-run determinism with hash verification
- All outputs match across runs

### Differential Tests
- Compare new vs old implementations
- Validate no regression
- Document intentional changes

### Sensitivity Tests
- Vary parameters (k, chunk_size, rrf_k)
- Measure output stability
- Document acceptable ranges

---

## Success Thresholds

**Coverage:** ≥95% line, ≥90% branch
**Determinism:** 100% hash match (3 runs)
**CLI Success Rate:** 100% with valid inputs
**Infrastructure:** All connections functional
**Documentation:** 100% claims verified

---

## Technology Stack

- **PDF Parsing:** PyMuPDF (fitz)
- **Search:** rank-bm25, AstraDB
- **Embeddings:** sentence-transformers
- **Fusion:** Custom RRF implementation
- **Orchestration:** LangGraph (with checkpoint.sqlite)
- **State:** SQLite (checkpointing)
- **Testing:** pytest, hypothesis, coverage
- **Type Checking:** mypy
- **Security:** bandit, detect-secrets

---

**Design Version:** 1.0
**Last Updated:** 2025-11-04
**Status:** Draft → Implementation
