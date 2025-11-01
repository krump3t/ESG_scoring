# ESG Context Report (Framework)
_Generated: 2025-11-01T16:59:49.617200Z_

## 1. Repo Overview
- Root: `/mnt/c/projects/Work Projects/ibm-projects/ESG Evaluation/prospecting-engine`
- Files: 33111 | LOC: 2073306

## 2. Ingestion Scope
- Items scanned: 44

## 3. Retrieval & Ranking
- Methods: ['embedding', 'bm25', 'hybrid', 'rerank', 'tfidf', 'crossencoder']
- Stores: ['astra', 'duckdb', 'parquet', 'milvus', 'neo4j', 'faiss', 'weaviate']

## 4. Scoring Pipeline & Gates
- Rubric paths: ['CRITICAL_RUBRIC_GAP.md', 'RUBRIC_ALIGNMENT_COMPLETE.md', 'RUBRIC_V3_IMPLEMENTATION_COMPLETE.md', 'rubrics/esg_maturity_rubricv3.md', 'rubrics/esg_rubric_schema_v3.json', 'rubrics/esg_rubric_v1.md', 'rubrics/RUBRIC_V3_MIGRATION.md', '.mypy_cache/3.11/rubrics.data.json', '.mypy_cache/3.11/rubrics.meta.json', '.mypy_cache/3.11/rubrics/compile_rubric.data.json', '.mypy_cache/3.11/rubrics/compile_rubric.meta.json', '.mypy_cache/3.11/scoring/rubric_v3_scorer.data.json', '.mypy_cache/3.11/scoring/rubric_v3_scorer.meta.json', '.mypy_cache/3.11/agents/scoring/rubric_loader.data.json', '.mypy_cache/3.11/agents/scoring/rubric_loader.meta.json', '.mypy_cache/3.11/agents/scoring/rubric_models.data.json', '.mypy_cache/3.11/agents/scoring/rubric_models.meta.json', '.mypy_cache/3.11/agents/scoring/rubric_scorer.data.json', '.mypy_cache/3.11/agents/scoring/rubric_scorer.meta.json', '.mypy_cache/3.11/agents/scoring/rubric_v3_scorer.data.json', '.mypy_cache/3.11/agents/scoring/rubric_v3_scorer.meta.json', '.mypy_cache/3.11/scripts/qa/audit_rubric_conformance.data.json', '.mypy_cache/3.11/scripts/qa/audit_rubric_conformance.meta.json', 'artifacts/sca_qax/rubric_from_docx.json', 'artifacts/sca_qax/RUBRIC_V3_INTEGRATION_COMPLETE.md', 'rubrics/archive/esg_maturity_rubric.md', 'rubrics/archive/ESG_maturity_rubric_SOURCETRUTH.md', 'rubrics/archive/esg_rubric_v1.md', 'tasks/008-esg-data-extraction/ESG_maturity_rubric_SOURCETRUTH.md', 'tasks/003-rubric-v3-implementation/qa/differential_rubric_v3_results.json']
- Evidence gate present: True (min_quotes=2)
- Parity check present: ['topk_vs_evidence', 'parity', 'subset', 'evidence subset']

## 5. Orchestration
- See key_paths.orchestration in context_scan.json

## 6. Determinism & Authenticity
- See authenticity_issues in context_scan.json

## 7. Observability
- Metrics present: True
- Run artifacts present: ['artifacts/run_manifest.json', 'artifacts/run_events.jsonl', 'artifacts/pipeline_validation/topk_vs_evidence.json', 'artifacts/audit/determinism_report.json']

## 8. Docker Readiness
- Compose files: []

## 9. QA Surface
- Pytest exit: 2 | Mypy exit: 2

## 10. MVP Delta (Shadow Path)
- Planner/Executor/Verifier/Generator mapping: TODO (fill in from repo specifics).

## 11. Risks
- TODO

## 12. Actionable Next Steps (1–2 weeks)
1. TODO
