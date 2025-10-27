# Architecture Decision Records (AR-001)

## ADR-001: Ledger-First Ingestion

**Decision**: Record every crawl in artifacts/ingestion/manifest.json with URL, headers, SHA256, status code.

**Rationale**:
- Enables audit trail and reproducibility
- Supports determinism verification (same crawl = same hash)
- Allows parity checking (evidence must come from recorded sources)

**Consequences**:
- Manifest grows with each crawl (append-only)
- No ability to delete historical entries (immutable by design)

---

## ADR-002: Rubric-as-JSON, Never Markdown

**Decision**: Load rubric from rubrics/maturity_v3.json; never parse Markdown at runtime.

**Rationale**:
- JSON is unambiguous, deterministic, schema-validatable
- Markdown parsing is brittle and non-deterministic
- Maturity_v3.json is the single source of truth

**Consequences**:
- All rubric updates must edit JSON, not Markdown
- No runtime interpretation of README or other docs

---

## ADR-003: Evidence-First Scoring

**Decision**: Refuse stage > 0 unless ≥2 quotes are provided per theme.

**Rationale**:
- Prevents spurious high-confidence scores on thin evidence
- Aligns with GRI/TCFD best practices (multiple citations)
- Enforces authenticity at the scoring gate

**Consequences**:
- Many low-evidence themes will be stage 0
- Requires deep evidence extraction (not surface-level)

---

## ADR-004: Parity Invariant

**Decision**: evidence_ids ⊆ fused_top_k_ids must always hold.

**Rationale**:
- If evidence is used in scoring, it should appear in retrieval results
- Catches inconsistencies between retrieval and scoring pipelines
- Enables root-cause analysis when parity is broken

**Consequences**:
- Retrieval and scoring phases are tightly coupled
- Cannot use evidence from outside the top-k
