# Task 020 — Hybrid Retrieval with DuckDB Prefilter (STRICT)

## Goal
Combine real semantic retrieval (watsonx.ai + AstraDB) with DuckDB SQL prefilter on enriched Parquet to reduce semantic call volume deterministically while maintaining retrieval quality.

## Artifacts
- **Input Parquets**:
  - `data/ingested/esg_documents.parquet` (27 records, real ESG docs)
  - `data/ingested/esg_embeddings.parquet` (27 records, 768-dim vectors)
  - `data/ingested/esg_docs_enriched.parquet` (27 records, with ranking signals)
- **Manifests**:
  - `artifacts/lineage/duckdb_stats.json` (parity verification)
  - `artifacts/lineage/enriched_manifest.json` (enrichment lineage)
  - `artifacts/lineage/embeddings_manifest.json` (embedding lineage)
  - `artifacts/lineage/astradb_upsert_manifest.json` (vector load lineage)

## Invariants
- **Deterministic**: DuckDB queries with fixed ORDER BY (published_at DESC, id)
- **No Synthetic Data**: All Parquet materialized from real documents/embeddings
- **No Fallbacks**: STRICT mode (ESG_STRICT_AUTH=1) raises on missing enriched parquet or prefilter failure
- **Type-Safe**: 100% annotated, mypy --strict compliant

## Design Decision
DuckDB prefilter reduces candidate set BEFORE semantic search (expensive API call), deterministically filtering by (company, theme) and recent recency. Hybrid retrieval then combines lexical (ParquetRetriever) + semantic (SemanticRetriever) with deterministic ranking.
