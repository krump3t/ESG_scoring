# DEMO-001 Multi-Source E2E Demo

## Scope
- Demonstrate deterministic ESG scoring using cached Apple assets (SEC EDGAR Item 1A, CDP Climate disclosure, Environmental Progress Report PDF).
- Produce evidence-first maturity scores for the seven canonical themes defined in `rubrics/maturity_v3.json`.
- Emit authenticity artifacts (parity, determinism, placeholder audit) under `artifacts/tasks/DEMO-001/`.

## Inputs & Outputs
**Inputs (all committed to the repo):**
- `data/pdf_cache/Apple_2023_sustainability.pdf`
- `data/crawler_cache/sec_edgar_apple_2023_10k.json`
- `data/crawler_cache/cdp_apple_2023_climate.json`
- `rubrics/maturity_v3.json`

**Outputs (deterministic)**
- Evidence catalog: `tasks/DEMO-001-multi-source-e2e/context/evidence.json`
- Compliance artifacts: `artifacts/tasks/DEMO-001/{topk_vs_evidence.json,determinism_report.json,authenticity_audit.json}`
- Demo manifest + docs: same task directory

## How to Run (Offline Defaults)
```bash
# install deps (offline cache)
make setup
# execute CP regression suite
make cp
# regenerate coverage + HTML
make coverage
```

### Docker-only Quickstart
```bash
make docker-build
make docker-smoke
docker-compose up
```

### Task-local Overrides
Copy `.env.example` to `.env` to pin SEED/embedded flags:
```bash
cp tasks/DEMO-001-multi-source-e2e/.env.example tasks/DEMO-001-multi-source-e2e/.env
```
Use `source` or `dotenv run` before invoking scripts.

## Authenticity Guarantees
- **Zero placeholders:** CP files (`apps/pipeline/score_flow.py`, `agents/scoring/evidence_aggregator.py`, `agents/scoring/parity_validator.py`) scanned for `TODO|FIXME|random|time()` – see `artifacts/tasks/DEMO-001/authenticity_audit.json`.
- **Evidence-first:** `tasks/DEMO-001-multi-source-e2e/context/evidence.json` stores ≥2 ≤30-word quotes per theme with doc path, hash provenance, and rubric linkage.
- **Parity hard check:** `artifacts/tasks/DEMO-001/topk_vs_evidence.json` verifies `evidence_doc_ids ⊆ fused_top_k`.
- **Rubric source of truth:** all scoring references the JSON schema at `rubrics/maturity_v3.json`; task docs never duplicate stage descriptors.

## Determinism Controls
- Environment defaults ship in `.env.example` (SEED=42, PYTHONHASHSEED=0, LIVE_EMBEDDINGS=false, ALLOW_NETWORK=false).
- `artifacts/tasks/DEMO-001/determinism_report.json` records SHA-256 digests for two identical runs (`semantic=0, alpha=0.6`) and one perturbation (`alpha=0.7`).
- Docker smoke job reuses these settings; integration requires explicitly exporting `LIVE_EMBEDDINGS=true ALLOW_NETWORK=true`.

## Parity Gate Workflow
1. Retrieval produces fused top-k slices (document IDs + scores).
2. Evidence aggregator selects quotes with provenance.
3. `ParityValidator.validate` ensures every evidence doc ID exists in the fused list.
4. Results captured in `artifacts/tasks/DEMO-001/topk_vs_evidence.json` with `parity_ok=true` when passing.

## Troubleshooting
- **Missing dependencies:** run `make setup` (or `pip install -r requirements.txt` inside a venv) before executing task scripts.
- **Coverage gate failures:** regenerate via `make coverage`; HTML saved to `htmlcov/` (uploaded by CI).
- **Docker healthcheck flapping:** ensure port 8000 free and rerun `make docker-stop && make docker-smoke`.
- **Parity failures:** inspect `violations` array inside `artifacts/tasks/DEMO-001/topk_vs_evidence.json` and confirm evidence quotes align with fused top-k doc IDs.

## Live E2E (Embeddings Required)
```bash
cd tasks/DEMO-001-multi-source-e2e
export SEC_USER_AGENT="IBM-ESG/ScoringApp/0.1 (Contact: <your-email>; Purpose: EDGAR 10-K fetch for ESG maturity demo)"
export ALLOW_NETWORK=true LIVE_EMBEDDINGS=true
export WX_API_KEY=... WX_PROJECT=... WX_MODEL_ID=...
python scripts/check_env_live.py
python scripts/edgar_validate.py --company "Apple Inc." --year 2024
python scripts/run_demo_live.py --company "Apple Inc." --year 2024 --query "climate strategy" --alpha 0.6 --k 10
pytest -m "integration and requires_api" -q
```
All commands fail-closed when environment variables or watsonx connectivity are missing. Reset `ALLOW_NETWORK=false LIVE_EMBEDDINGS=false` after live validation to return to deterministic CP mode.
