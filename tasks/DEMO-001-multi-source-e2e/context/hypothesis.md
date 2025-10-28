# DEMO-001 Multi-Source E2E Demo — Hypothesis & Metrics

## Hypothesis
With cached Apple assets (SEC EDGAR Item 1A, CDP climate disclosure, 2023 Environmental Progress PDF) and the canonical rubric in `rubrics/maturity_v3.json`, the pipeline can produce deterministic, evidence-first maturity scores across all seven themes while satisfying parity and authenticity gates offline.

## Success Criteria
| Requirement | Metric | Verification |
|-------------|--------|--------------|
| Multi-source ingestion | SEC + CDP + PDF available locally | `tasks/DEMO-001-multi-source-e2e/context/data_sources.json` |
| Evidence-first | ≥2 quotes per theme, ≤30 words | `tasks/DEMO-001-multi-source-e2e/context/evidence.json` |
| Parity | `evidence_doc_ids ⊆ fused_top_k` | `artifacts/tasks/DEMO-001/topk_vs_evidence.json` |
| Rubric alignment | Uses `rubrics/maturity_v3.json` | CP code paths + docs |
| Determinism | 2 identical digests, 1 variant | `artifacts/tasks/DEMO-001/determinism_report.json` |
| Authenticity | No TODO/FIXME/random/time misuse | `artifacts/tasks/DEMO-001/authenticity_audit.json` |

## Required Artifacts
```
artifacts/tasks/DEMO-001/
├── topk_vs_evidence.json   # parity proof (semantic=0, alpha=0.6)
├── determinism_report.json # repeats + alpha variant digests
└── authenticity_audit.json # placeholder/random scan & rubric validation
```

## Quality Gates (inherit from CI)
- `pytest -m cp -q` (evidence-first behaviour covered by CP tests)
- `coverage run -m pytest && coverage report --fail-under=95`
- `mypy --strict apps/ agents/ libs/`
- `lizard -C 10 apps/ agents/ libs/`
- `interrogate -v -f 95 apps/ agents/ libs/`

## Determinism Baseline
| Run | Alpha | Digest | Result |
|-----|-------|--------|--------|
| Run 1 | 0.6 | `feb0e9ac279623ec9ef9cba727895f7ba4bc7eac02131ca9d9b0a571873855c5` | Baseline |
| Run 2 | 0.6 | `feb0e9ac279623ec9ef9cba727895f7ba4bc7eac02131ca9d9b0a571873855c5` | Matches Run 1 |
| Run 3 | 0.7 | `a6d7f4f1e694b39c14d20f4f0794d8c81d1a80cb2dae13866f8ea6d7e102bfdd` | Expected divergence |

## Risks & Mitigations
- **Parity drift** — Monitor `violations` array in `topk_vs_evidence.json`; rerun retrieval if doc IDs fall out of fused top-k.
- **Sparse evidence** — Evidence catalog already sources from SEC + CDP + PDF; augment from cached PDF extracts if any theme drops below two quotes.
- **Dependency gaps** — Operate inside virtualenv or Docker (see README_TASK) to keep pyarrow/fastapi stack aligned with CI.
