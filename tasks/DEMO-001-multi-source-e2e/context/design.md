# DEMO-001 Multi-Source E2E Demo — Design Snapshot

## Pipeline Overview
1. **Source loading (offline):**
   - `data/pdf_cache/Apple_2023_sustainability.pdf`
   - `data/crawler_cache/sec_edgar_apple_2023_10k.json`
   - `data/crawler_cache/cdp_apple_2023_climate.json`
2. **Extraction & normalization:**
   - SEC + CDP cached JSON is read directly.
   - PDF quotes curated to ≤30 words per evidence record.
   - Output schema matches `tasks/DEMO-001-multi-source-e2e/context/evidence.json`.
3. **Parity preparation:**
   - Top-k doc list constructed (`sec-edgar-apple-2023-10k`, `cdp-apple-2023-climate`, `apple-environmental-progress-2025`).
   - Evidence doc IDs validated against fused list (see `artifacts/tasks/DEMO-001/topk_vs_evidence.json`).
4. **Scoring:**
   - `RubricV3Scorer` loads canonical definitions from `rubrics/maturity_v3.json`.
   - Seven dimension scores derived from curated evidence (two quotes minimum per theme).
5. **Artifact emission:**
   - Parity, determinism, and authenticity audits are written under `artifacts/tasks/DEMO-001/`.

## Critical Path Files
- `apps/pipeline/score_flow.py` — orchestrates offline flow.
- `agents/scoring/evidence_aggregator.py` — enforces quote limits & provenance.
- `agents/scoring/parity_validator.py` — fail-closed parity gate.

These paths are tracked in `context/cp_paths.json` for authenticity scans.

## Data Contracts
| Artifact | Key Fields | Notes |
|----------|------------|-------|
| Evidence catalog | `theme`, `quote`, `doc_id`, `path`, `word_count` | Two entries per theme; ≤30 words. |
| Top-k parity | `fused_top_k[]`, `evidence_doc_ids[]`, `parity_ok` | Doc IDs map directly to evidence catalog. |
| Determinism | `runs[]` with `alpha`, `digest` | Confirms reproducibility at alpha 0.6 and 0.7. |

## Deterministic Settings
- Env defaults: `SEED=42`, `PYTHONHASHSEED=0`, `LIVE_EMBEDDINGS=false`, `ALLOW_NETWORK=false`.
- Dockerfile, docker-compose, Makefile, and `.env.example` all enforce these defaults.

## Execution Paths
| Tooling | Command | Purpose |
|---------|---------|---------|
| Makefile | `make cp` | CI-equivalent CP checks. |
| Makefile | `make docker-smoke` | Builds container and exercises `/health` + `/score`. |
| Docker Compose | `docker-compose up` | Launches API with deterministic defaults. |

## Documentation & Manifest
- `README_TASK.md` — operator quickstart + authenticity notes.
- `demo_manifest.json` — records bronze parquet pointer and cache hashes for Docker mounts.
- `.env.example` — task-scoped overrides, used by CI and developers alike.
