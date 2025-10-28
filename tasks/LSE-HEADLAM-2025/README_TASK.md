# LSE-HEADLAM-2025 Task

## Scope
- Headlam Group Plc 2025 sustainability evaluation using rubric `rubrics/maturity_v3.json`.
- Offline critical path with deterministic ingestion, scoring, parity, and evidence gates.
- Optional live/semantic run (watsonx embeddings) via guarded scripts.

## Inputs & Outputs
**Inputs (committed)**
- `rubrics/maturity_v3.json`
- `/mnt/data/LSE_HEAD_2025.pdf`

**Generated artifacts (`artifacts/tasks/LSE-HEADLAM-2025/`)**
- `bronze/chunks.parquet`
- `score.jsonl`
- `evidence.json` (≥2 quotes per theme, ≤30 words, sha256)
- `topk_vs_evidence.json`
- Optional live run summary JSON

## Offline CP Quickstart
```bash
python tasks/LSE-HEADLAM-2025/scripts/ingest_headlam.py
python tasks/LSE-HEADLAM-2025/scripts/run_headlam_offline.py
```

## Optional Live Path (watsonx embeddings)
```bash
cd tasks/LSE-HEADLAM-2025
export SEC_USER_AGENT="IBM-ESG/ScoringApp/0.1 (Contact: <your-email>; Purpose: EDGAR 10-K fetch for ESG maturity demo)"
export ALLOW_NETWORK=true LIVE_EMBEDDINGS=true
export WX_API_KEY=... WX_PROJECT=... WX_MODEL_ID=...
python scripts/check_env_live.py
python scripts/edgar_validate.py --company "Headlam Group Plc" --year 2025
python scripts/run_headlam_offline.py  # refresh parity/evidence
python scripts/run_headlam_live.py --query "GHG inventory and net zero pathway"
```

Reset `ALLOW_NETWORK=false LIVE_EMBEDDINGS=false` after live testing to restore deterministic defaults.

## Troubleshooting
- **Manifest missing entry:** rerun `ingest_headlam.py` to rebuild bronze and update manifests.
- **Evidence length violation:** inspect `evidence.json` to confirm quotes ≤30 words; regenerate if manual edits occur.
- **Parity failure:** ensure fused top-k doc IDs cover evidence (rerun offline pipeline).

Refer to `./README.md` for CI gates and to `tasks/DEMO-001-multi-source-e2e/README_TASK.md` for canonical workflow patterns.
