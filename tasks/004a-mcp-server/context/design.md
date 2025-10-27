# Design: MCP Server for watsonx.orchestrate

## Architecture Overview

```
┌─────────────────────────────────────┐
│   watsonx.orchestrate (Cloud)       │
└──────────────┬──────────────────────┘
               │ HTTP/JSON
               │ (via ngrok)
┌──────────────▼──────────────────────┐
│        MCP Server (FastAPI)         │
│  - Tool Registry                    │
│  - Request Router                   │
│  - Response Formatter               │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    │          │          │          │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│Crawler│ │Normal │ │Scoring│ │Explain│
│ Agent │ │ Agent │ │ Agent │ │ Agent │
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │         │         │         │
┌───▼─────────▼─────────▼─────────▼───┐
│   Data Layer (Bronze/Silver/Gold)   │
│   MinIO + Iceberg + AstraDB          │
└──────────────────────────────────────┘
```

## MCP Server Components

### 1. Server Core (`mcp_server/server.py`)
- FastAPI application
- Stdio and HTTP protocol support
- Tool registry for all agent tools
- Health check endpoints
- Authentication middleware

### 2. Tool Handlers

#### Query Handler (`mcp_server/handlers/query_handler.py`)
```python
@app.post("/tools/call/esg.query.maturity")
async def handle_maturity_query(request: MaturityQueryRequest):
    """
    Query organization's ESG maturity for specific theme/year

    Returns:
    - Maturity level (0-5)
    - Confidence score
    - Key findings
    - Evidence links
    """
```

#### Explainability Handler (`mcp_server/handlers/explainability_handler.py`)
```python
@app.post("/tools/call/esg.explain.score")
async def handle_explain_score(request: ExplainScoreRequest):
    """
    Explain why organization received specific maturity score

    Returns:
    - Reasoning text
    - Supporting evidence (page-level)
    - Framework mappings
    - AstraDB graph links
    """
```

#### Ingestion Handler (`mcp_server/handlers/ingestion_handler.py`)
```python
@app.post("/tools/call/esg.ingest.report")
async def handle_ingest_report(request: IngestReportRequest):
    """
    Trigger ingestion of new sustainability report

    Orchestrates:
    1. Crawler agent: Download + extract
    2. Normalizer agent: Chunk + deduplicate
    3. Scoring agent: Maturity assessment
    """
```

### 3. Response Formatting

All responses follow MCP protocol:
```json
{
  "success": true,
  "tool": "esg.query.maturity",
  "result": {
    ...data...
  },
  "metadata": {
    "timestamp": "2025-10-22T...",
    "snapshot_id": 12345,
    "traceability": {
      "run_id": "...",
      "artifacts": [...]
    }
  },
  "errors": []
}
```

## Data Flow

### Query: "What is Microsoft's Climate maturity?"

1. **Request** → MCP Server
   ```
   POST /tools/call/esg.query.maturity
   {org_id: "microsoft", year: 2024, theme: "Climate"}
   ```

2. **Server** → Gold Layer (Iceberg)
   ```sql
   SELECT * FROM gold.esg_scores
   WHERE org_id = 'microsoft'
     AND year = 2024
     AND theme = 'Climate'
   ORDER BY scoring_timestamp DESC
   LIMIT 1
   ```

3. **Aggregate** → Organization-level summary
   - Average maturity across findings
   - Weighted confidence
   - Top N findings as evidence

4. **Response** → watsonx.orchestrate
   ```json
   {
     "maturity_level": 4,
     "maturity_label": "Leading",
     "confidence": 0.87,
     "findings_count": 12,
     "key_evidence": [...]
   }
   ```

### Query: "Why did they score 4?"

1. **Request** → MCP Server
   ```
   POST /tools/call/esg.explain.score
   {org_id: "microsoft", year: 2024, theme: "Climate"}
   ```

2. **Server** → Gold Layer + Silver Layer
   - Fetch score record
   - Fetch original findings
   - Fetch evidence manifest from AstraDB

3. **Build Explanation**
   - Extract reasoning text
   - Link to source pages
   - Show framework mappings
   - Provide confidence breakdown

4. **Response** → Structured explanation with citations

## Technology Stack

- **Web Framework**: FastAPI (async, OpenAPI auto-docs)
- **Protocol**: MCP (Model Context Protocol)
- **Authentication**: API Key via headers
- **Validation**: Pydantic models
- **Logging**: Structured JSON logs to `qa/run_log.txt`
- **Tunneling**: ngrok HTTP tunnel for external access

## Security

1. **API Key Authentication**
   ```python
   @app.middleware("http")
   async def validate_api_key(request, call_next):
       api_key = request.headers.get("X-API-Key")
       if not verify_api_key(api_key):
           return JSONResponse({"error": "Unauthorized"}, status_code=401)
       return await call_next(request)
   ```

2. **Rate Limiting**: 100 requests/minute per API key

3. **Input Validation**: Pydantic schemas prevent injection

4. **No Secrets in Responses**: Never expose internal paths/credentials

## Performance

- **Caching**: Redis cache for frequent queries (optional)
- **Connection Pooling**: Reuse MinIO/Trino connections
- **Async I/O**: FastAPI async handlers
- **Response Compression**: gzip for large responses

## Deployment

### Local Development
```bash
uvicorn mcp_server.server:app --reload --port 8000
```

### ngrok Tunnel
```bash
ngrok http 8000
```

### watsonx.orchestrate Configuration
```json
{
  "mcp_server": {
    "url": "https://[ngrok-url].ngrok.io",
    "auth": {
      "type": "api_key",
      "header": "X-API-Key"
    },
    "tools": [
      "esg.query.maturity",
      "esg.explain.score",
      "esg.ingest.report"
    ]
  }
}
```

## Validation & Testing

1. **Unit Tests**: Test each handler independently
2. **Integration Tests**: Full pipeline from HTTP → DB → Response
3. **Load Tests**: Simulate 100 concurrent users
4. **Protocol Compliance**: Verify MCP protocol adherence

## Traceability

Every request generates:
- `run_id` in response metadata
- Entry in `artifacts/run_events.jsonl`
- Logs in `qa/run_log.txt`
- Snapshot ID linking to gold layer data
