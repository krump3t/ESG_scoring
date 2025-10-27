# Key Assumptions (AR-001)

1. **Rubric Stability**: rubrics/maturity_v3.json is immutable during this phase.
2. **Single-Source Truth**: maturity_v3.json is the only authoritative rubric source (no Markdown fallback).
3. **Deterministic Seeding**: SEED=42 and PYTHONHASHSEED=0 are set before all tests.
4. **Network Isolation**: Scoring runs in Docker container (read-only); no network egress in scorer.
5. **Evidence Provenance**: All evidence quotes originate from documents in ingestion manifest.
6. **Minimal CP Scope**: Only modify ledger.py, rubric_scorer.py, parity_checker.py, main.py; no other CP changes.
7. **Test Coverage Baseline**: All CP tests pass before validation; ≥95% coverage achieved.
8. **Determinism Achievability**: 3 identical runs ARE achievable with fixed seed and deterministic algorithms.
