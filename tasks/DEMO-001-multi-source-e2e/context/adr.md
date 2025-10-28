# ADR-DEMO-001: Multi-Source Demo Decisions

## ADR 1 — Cached multi-source inputs
- **Decision**: Use cached SEC EDGAR Item 1A, CDP climate disclosure, and Apple sustainability PDF (no live network).
- **Rationale**: Guarantees determinism, respects CP no-network policy, keeps data authentic.
- **Implication**: Any source refresh requires updating `context/data_sources.json` with new SHA256 values.

## ADR 2 — Parity as a hard gate
- **Decision**: Evidence doc IDs must be a subset of fused top-k results.
- **Rationale**: Prevents fabricated evidence; aligns with SCA authenticity rules.
- **Artifact**: `artifacts/tasks/DEMO-001/topk_vs_evidence.json` records verdict and inputs.

## ADR 3 — Evidence length & coverage
- **Decision**: Maintain ≥2 quotes per theme, each ≤30 words, with provenance metadata.
- **Rationale**: Matches rubric and microprompt mandates; simplifies manual audit.
- **Implementation**: Evidence catalog (`context/evidence.json`) enforces structure and word counts.

## ADR 4 — Canonical rubric reference
- **Decision**: Load maturity definitions exclusively from `rubrics/maturity_v3.json`.
- **Rationale**: Avoids divergence between docs and executable logic; single source of truth.
- **Check**: `artifacts/tasks/DEMO-001/authenticity_audit.json` verifies JSON presence and structure.
