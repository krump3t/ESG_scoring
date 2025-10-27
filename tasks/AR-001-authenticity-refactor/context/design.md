# AR-001: Authenticity Refactor Design

## Data Strategy
- **Ingestion**: Use real company reports (Apple Inc., Microsoft) with documented crawl ledger
- **Splits**: No train/test split; all data is validation data (authenticity is deterministic)
- **Normalization**: Content hashes (SHA256) are deterministic; no normalization needed
- **Leakage Guards**: Ledger records are immutable; manifest is append-only

## Verification Plan
1. **Differential Tests**:
   - Run IngestLedger.add_crawl twice with same input → verify ledger entries are identical
   - Run RubricScorer.score with same evidence twice → verify score records are identical

2. **Sensitivity Tests**:
   - ParityChecker: verify behavior with varying k values (5, 10, 20)
   - RubricScorer: verify behavior with 1, 2, 3+ quotes per theme

3. **Property Tests**:
   - Ledger accepts URLs of all lengths and formats
   - Fusion determinism: fixed seed → fixed ordering
   - Quotes enforcement: stage is always 0 if quotes < MIN_QUOTES_PER_THEME

## Success Thresholds
- **Ingestion**: Manifest file written to artifacts/ingestion/manifest.json with ≥1 crawl entry
- **Parity**: demo_topk_vs_evidence.json generated; verdict="PASS" for demo fixture
- **Rubric**: RubricScorer enforces stage=0 when quotes < 2; stage ≥ 1 when quotes ≥ 2
- **Determinism**: 3 consecutive runs produce byte-identical maturity.parquet
- **API**: /trace endpoint returns status 200 with ledger_manifest and parity_verdict fields
