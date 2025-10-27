# Task 020 Hypotheses

## H1: DuckDB Prefilter Reduces Semantic Calls Without Losing Relevance
**Claim**: Deterministic SQL prefiltering on enriched Parquet (published_at DESC, limit 50) reduces semantic API calls by ~80% while maintaining top-k relevance for real queries.

**Test**: Compare (lexical + full semantic) vs (lexical + prefiltered semantic) retrieval results; verify top-5 relevance is stable across 10+ queries.

## H2: Parquet Lineage + Parity Checks Prevent Data Drift
**Claim**: Real-time parity checks (docs count == embeddings count, zero orphans) combined with deterministic Parquet materialization prevent silent data inconsistencies between documents, embeddings, and enriched views.

**Test**: Run DuckDB parity check; assert all counts match; verify enriched Parquet row count == docs count.

## H3: STRICT Mode Enforces Authenticity Without Fallbacks
**Claim**: When ESG_STRICT_AUTH=1, missing enriched Parquet or prefilter failure triggers explicit RuntimeError (no silent degradation to mocks).

**Test**: Run with ESG_STRICT_AUTH=1 and remove enriched Parquet; verify RuntimeError is raised before any retrieval attempt.
