# DEMO-001 — Assumptions & Constraints

## Assumptions
1. **Local assets are authoritative**  
   Apple SEC, CDP, and PDF caches in `data/` remain immutable; hashes recorded in `context/data_sources.json`.
2. **Rubric JSON is the single source**  
   All scoring logic loads from `rubrics/maturity_v3.json`; task docs never duplicate stage text.
3. **Evidence set is sufficient**  
   Curated quotes already meet ≥2-per-theme coverage. If new evidence is needed, reuse the same sources and update `context/evidence.json`.
4. **CP files stay offline**  
   `score_flow.py`, `evidence_aggregator.py`, and `parity_validator.py` must not import networking modules. Authenticity audit enforces this.

## Constraints
- **Deterministic environment** — Use `.env.example` defaults (SEED=42, PYTHONHASHSEED=0, LIVE_EMBEDDINGS=false, ALLOW_NETWORK=false).
- **Parity fail-closed** — Do not accept evidence outside `fused_top_k`. Update `artifacts/tasks/DEMO-001/topk_vs_evidence.json` on any retrieval change.
- **≤30 word quotes** — Evidence updates must preserve the limit and provenance metadata.
- **Documentation sync** — README, manifest, and context files should be updated together whenever sources or gates change.
