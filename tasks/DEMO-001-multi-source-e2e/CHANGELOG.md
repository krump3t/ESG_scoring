# Changelog

All notable updates to DEMO-001 are documented here, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and adhering to [Semantic Versioning](https://semver.org/).

## [2025-10-26] - Compliance sweep
### Added
- Task-specific `.env.example` enforcing deterministic offline defaults (SEED=42, PYTHONHASHSEED=0, LIVE_EMBEDDINGS/LALLOW_NETWORK=false).
- `demo_manifest.json` with canonical sources, rubric pointer, and Docker-friendly bronze parquet reference.
- Authenticity artifacts under `artifacts/tasks/DEMO-001/` covering parity, determinism, and placeholder scans.
- Task README describing scope, execution paths (Makefile & Docker), authenticity guardrails, and troubleshooting.
### Updated
- Context files (`hypothesis.md`, `design.md`, `assumptions.md`, `adr.md`) to reference the single source of truth rubric (`rubrics/maturity_v3.json`) without duplicating stage text.
- Evidence catalog to guarantee ≥2 quotes per rubric theme, each ≤30 words with provenance fields.
- Data source inventory with exact SHA256 hashes for cached Apple SEC, CDP, and PDF assets.
