# Hypothesis: Iceberg Core - Silver and Gold Layers

## Core Hypothesis
Implementing Iceberg tables for silver (normalized) and gold (scored) layers with Normalizer and Scoring agents will enable ACID transactions, schema evolution, and reproducible ESG maturity scoring with full audit trails.

## Success Metrics
- MERGE upsert performance: > 1000 records/sec
- Schema evolution: Zero downtime for column additions
- Time-travel queries: < 2 second overhead
- Confidence calibration: Variance > 30% across data quality levels
- watsonx.ai integration: > 95% API success rate

## Critical Path
- agents/normalizer/mcp_normalizer.py
- agents/scoring/mcp_scoring.py
- iceberg/tables/silver_schema.py
- iceberg/tables/gold_schema.py
- integrations/watsonx_improved.py
