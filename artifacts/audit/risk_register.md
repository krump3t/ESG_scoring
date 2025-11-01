# Risk Register (Top 10)

1. **Parity artifact is invalid (AV06)**  
   - severity: critical  
   - owner_hint: Retrieval/Scoring  
   - fix_window: 24h  
   - notes: Evidence doc_ids never overlap fused top-k (21/21 missing), so parity gate provides no protection.
2. **Scoring pipeline requires live WatsonX/Astra network (AV04)**  
   - severity: critical  
   - owner_hint: Platform/Scoring  
   - fix_window: 48h  
   - notes: `ESGScoringPipeline` bootstraps real clients during Airflow runs, violating docker-only posture.
3. **Ingestion ledger lacks headers/content-type and fake hashes (AV05/provenance)**  
   - severity: high  
   - owner_hint: Ingestion  
   - fix_window: 72h  
   - notes: 1,015 manifest entries use `test_hash` and omit content_type/headers, so provenance cannot be trusted.
4. **Evidence records lack chunk_id/source_hash (AV05/AV07)**  
   - severity: high  
   - owner_hint: Evidence/Traceability  
   - fix_window: 72h  
   - notes: `artifacts/demo/real_evidence.json` stores only doc_id/pdf_hash, making chunk-level trace impossible.
5. **Determinism gate missing maturity.parquet (AV03)**  
   - severity: high  
   - owner_hint: Data Lake  
   - fix_window: 48h  
   - notes: Determinism report fails because maturity.parquet is absent, so CP state cannot be hashed.
6. **Runtime rubric bypasses canonical JSON and =2 quotes rule (AV07)**  
   - severity: high  
   - owner_hint: Scoring  
   - fix_window: 48h  
   - notes: API uses `RubricV3Scorer` heuristics instead of `rubrics/maturity_v3.json`, allowing evidence-light stages.
7. **Non-deterministic chunk_ids and template selection (AV02)**  
   - severity: high  
   - owner_hint: Retrieval  
   - fix_window: 72h  
   - notes: Python `hash()` is used for chunk IDs and template selection, so trace IDs change between runs.
8. **Unseeded randomness in MCP and Astra health check (AV01)**  
   - severity: medium  
   - owner_hint: MCP/Infra  
   - fix_window: 72h  
   - notes: Random.uniform/unseeded np.random introduce run-to-run drift in quality scores and smoke tests.
9. **Workspace escapes to `data/` and `reports/` (AV09)**  
   - severity: medium  
   - owner_hint: Ingestion/QA  
   - fix_window: 96h  
   - notes: Parser caches PDFs under `data/pdf_cache` and response evaluator writes to `reports/…`, violating artifacts-only rule.
10. **JSON masquerading as Parquet in embedding snapshot (AV11)**  
    - severity: medium  
    - owner_hint: Retrieval Tooling  
    - fix_window: 96h  
    - notes: `scripts/embed_and_index.py` reads text JSON from files ending in `.parquet`, so downstream checks misinterpret formats.
