# Hypothesis: MCP Server for watsonx.orchestrate Integration

## Core Hypothesis
Implementing a unified MCP server that aggregates all agent tools (Crawler, Normalizer, Scoring, Explainability) will enable watsonx.orchestrate to query sustainability maturity with full traceability via HTTP/stdio protocols and ngrok tunneling.

## Success Metrics
- Server responds to HTTP requests < 500ms (non-LLM queries)
- Supports both stdio and HTTP MCP protocols
- Tool discovery returns all 12+ agent tools
- Query handling: "What is [company]'s [theme] maturity?" returns score + evidence
- Explainability: "Why did [company] score [X]?" returns page-level evidence
- ngrok tunnel stability: > 99% uptime during testing
- watsonx.orchestrate integration: > 95% successful tool calls

## Critical Path
- mcp_server/server.py
- mcp_server/handlers/query_handler.py
- mcp_server/handlers/explainability_handler.py
- mcp_server/routes.py
- integrations/watsonx_orchestrate.py

## Input/Output
**Input**: HTTP POST to `/tools/call` with:
```json
{
  "tool": "esg.query.maturity",
  "params": {
    "org_id": "microsoft",
    "year": 2024,
    "theme": "Climate"
  }
}
```

**Output**:
```json
{
  "org_id": "microsoft",
  "year": 2024,
  "theme": "Climate",
  "maturity_level": 4,
  "maturity_label": "Leading",
  "confidence": 0.87,
  "evidence_count": 12,
  "key_findings": [...],
  "snapshot_id": 12345,
  "evidence_manifest_url": "astra://..."
}
```

## Risk Mitigation
- Rate limiting: 100 req/min per client
- Authentication: API key validation
- Error handling: Graceful degradation with partial results
- Logging: Full request/response traceability
