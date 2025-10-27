# Phase 2: watsonx.ai Integration - Architecture Design (SCA v13.8)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ESG Evaluation Platform                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT LAYER              PROCESSING                   STORAGE   │
│  ════════════════════════════════════════════════════════════   │
│                                                                  │
│  ESG Documents  →  Document Extraction  →  Text Chunks        │
│  (PDF/Text)        (OCR/parsing)          (Semantic Split)    │
│        ↓                                         ↓              │
│  Real Files     →  Slate Embeddings API  →  384-dim Vectors   │
│  (10+ reports)     (Batch: 5 docs)           (Real AstraDB)    │
│        ↓                                         ↓              │
│  ESG Queries    →  Query Embedding  →  Similarity Search      │
│  (User Input)      (Slate 125m)         (ANN, Top-5)          │
│        ↓                                         ↓              │
│  Context         Granite LLM             RAG Response         │
│  Retrieval   +   (3.0-8B-Instruct)    (Augmented with docs)  │
│                  (Real inference)                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. watsonx_client.py (LLM Interface)

**Responsibilities**:
- Authenticate with IBM Cloud API key
- Call Granite 3.0-8B-Instruct
- Handle rate limiting (100 req/hr)
- Implement exponential backoff
- Return structured responses

**Interface**:
```python
class WatsonXClient:
    def __init__(api_key: str, project_id: str, url: str):
        pass

    def generate(prompt: str, max_tokens: int = 200) -> str:
        """Call Granite LLM with context-aware ESG prompt"""
        pass

    def generate_batch(prompts: List[str]) -> List[str]:
        """Batch inference for efficiency"""
        pass
```

**Real API**: IBM watsonx.ai Granite endpoint
**Rate Limit**: 100 requests/hour (exponential backoff)

---

### 2. watsonx_embedder.py (Embeddings)

**Responsibilities**:
- Call Slate 125m embeddings API
- Batch processing (5-10 documents)
- Validate 384-dimensional output
- Cache embeddings for reuse
- Measure latency

**Interface**:
```python
class WatsonXEmbedder:
    def __init__(api_key: str, project_id: str):
        pass

    def embed_text(text: str) -> np.ndarray:
        """Single embedding (384-dim)"""
        pass

    def embed_batch(texts: List[str]) -> np.ndarray:
        """Batch embeddings (N x 384)"""
        pass
```

**Real API**: IBM watsonx.ai Slate 125m endpoint
**Output**: Real 384-dimensional vectors
**Latency Target**: <5 seconds per document

---

### 3. astradb_vector.py (Vector Storage)

**Responsibilities**:
- Create vector collection (esg_documents)
- Upsert embeddings + metadata
- Similarity search (ANN)
- Delete/update operations
- Health checks

**Interface**:
```python
class AstraDBVector:
    def __init__(token: str, db_id: str, region: str):
        pass

    def create_collection(name: str, vector_dim: int = 384):
        """Create collection for embeddings"""
        pass

    def upsert(vectors: List, metadata: Dict):
        """Insert/update embeddings with document metadata"""
        pass

    def similarity_search(query_vector: np.ndarray, top_k: int = 5):
        """Find similar documents via ANN"""
        pass
```

**Real Database**: AstraDB (Cassandra-based)
**Collection**: esg_documents (384-dim vectors)
**Index**: SAI (Storage-Attached Index) for ANN

---

### 4. ingest_esg_documents.py (Data Ingestion)

**Responsibilities**:
- Load real ESG documents (PDF/text)
- Extract structured text
- Split into chunks
- Generate embeddings
- Store in AstraDB
- Track provenance

**Workflow**:
```
Load Document → Extract Text → Chunk → Embed → Store
(Real ESG)     (PDF/OCR)    (Semantic) (API)  (AstraDB)
```

**Real Data Sources**:
- Corporate ESG reports (PDF)
- Climate transition plans
- Governance structure documents
- Diversity & inclusion metrics

---

### 5. generate_esg_analysis.py (RAG Pipeline)

**Responsibilities**:
- Accept user query
- Generate query embedding
- Search AstraDB for relevant docs
- Construct prompt with context
- Call Granite LLM
- Return augmented response

**Workflow**:
```
Query → Embed → Search → Retrieve Top-5 → Context Prompt → LLM → Response
(User) (Slate) (ANN)     (AstraDB)      (Concatenate)   (Real) (Analysis)
```

**Latency Target**: <20 seconds end-to-end

---

## Data Flow Specifications

### Document Ingestion Flow
```
ESG Report (PDF)
    ↓
Extract Text (OCR/parsing)
    ↓
Chunk Text (500-word chunks)
    ↓
Batch 5 chunks together
    ↓
Call Slate Embeddings API → Get 384-dim vectors
    ↓
Upsert to AstraDB with:
  - Vector (384-dim)
  - Document ID
  - Chunk ID
  - Text excerpt
  - Metadata (source, date, type)
  - Embedding timestamp
    ↓
Store in: esg_documents collection
```

### RAG Query Flow
```
User Query: "What are company X's climate commitments?"
    ↓
Embed Query → 384-dim vector (Slate API)
    ↓
ANN Search in AstraDB:
  SELECT * FROM esg_documents
  WHERE similarity(vector, query_vector) > threshold
  ORDER BY similarity DESC
  LIMIT 5
    ↓
Retrieve Top-5 Chunks (with provenance)
    ↓
Construct Prompt:
  "Based on the following ESG documents:
   [Top-5 chunks concatenated]

   Answer: [Query]"
    ↓
Call Granite LLM → Get completion
    ↓
Return Response with:
  - Analysis text
  - Source attribution
  - Confidence score
  - Latency metrics
```

---

## Error Handling Strategy

| Scenario | Handler | Fallback |
|----------|---------|----------|
| API Rate Limit | Exponential backoff (2s→8s→32s) | Queue for retry |
| Embedding Dimension Wrong | Validate size, reject | Log and skip document |
| AstraDB Connection Lost | Retry with connection pool | Cache locally |
| LLM Timeout (>15s) | Abort and return error | Use cached response |
| Document Parse Error | Log error, skip chunk | Continue with next doc |

---

## Security & Compliance

- **API Keys**: Stored in `.env.production` (git-ignored)
- **Rate Limiting**: 100 req/hr per API
- **Data Retention**: Embeddings cached for reuse
- **Audit Trail**: Timestamp + source metadata on all vectors
- **Access Control**: AstraDB token with specific permissions

---

## Testing Strategy

### Unit Tests
- Embedding dimension validation
- API response parsing
- Error handling

### Integration Tests (20+)
- Real API calls (authenticated)
- Batch processing with real documents
- Vector storage operations
- RAG pipeline end-to-end

### Property Tests
- Embedding consistency (same input → same output)
- Vector dimensionality invariant (always 384)
- ANN search transitive property

### Failure Path Tests
- API authentication failure
- Rate limit handling
- Document extraction failure
- AstraDB connection loss
- LLM timeout

---

## Performance Specifications

| Operation | Target | SLA |
|-----------|--------|-----|
| Single Embedding | <5s | 95th percentile |
| Batch 5 Embeddings | <20s | 95th percentile |
| Similarity Search | <500ms | 99th percentile |
| LLM Inference | <10s | 95th percentile |
| RAG Pipeline E2E | <20s | 95th percentile |

---

## Verification Plan

**Differential Testing**:
- Compare embedding outputs across API calls
- Validate vector quality with cosine similarity
- Verify LLM responses for semantic coherence

**Sensitivity Analysis**:
- Vary document chunk size
- Vary number of retrieved documents
- Vary LLM temperature settings

**Leakage Guards**:
- Use separate train/test documents
- Disable caching during validation
- Verify no document cross-contamination

---

## Success Thresholds

- **SC6**: Embeddings exactly 384-dimensional ✓
- **SC7**: LLM generates coherent responses (no hallucinations) ✓
- **SC8**: 10+ documents processed successfully ✓
- **SC9**: Vectors stored and searchable in AstraDB ✓
- **SC10**: RAG pipeline latency <20s, retrieval quality >0.7 cosine ✓
