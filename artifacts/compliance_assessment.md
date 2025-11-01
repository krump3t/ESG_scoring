# SCA v13.8-MEA Compliance Assessment
## prospecting-engine E2E Orchestration

### PART A: GATE STATUS (Current State)

#### ✅ Gates PASSING (Verified with Artifacts)
1. **Docker Build** - esg-scoring:ci (3.23 GB) successfully built
2. **Baseline Orchestration** - 7/7 ESG themes extracted (TSP, OSP, DM, GHG, RD, EI, RMM)
3. **Single-Run Scoring** - output.json + scoring_response.json generated
4. **Parity Validation** - parity_ok=true in output artifacts
5. **Output Contract** - artifacts/output_contract.json exists with required schema

#### ⚠️ Gates REQUIRING REMEDIATION (Not Yet Fully Implemented)

1. **Determinism Lock** (Status: Partial)
   - ✓ Single run completed successfully
   - ✗ 3-run determinism validation incomplete (attempted but PYTHONPATH issues)
   - ✗ run_manifest.json (input file hashes + env snapshot) NOT CREATED
   - **Required:** Baseline 3×, UNIQUE(output_hash) == 1, determinism_report.json
   - **Blocker:** PYTHONPATH environment passing through bash scripts needs fixing

2. **Evidence Hardening** (Status: Not Started)
   - ✗ No evidence_audit.json (per-theme quote counts + page dispersion)
   - ✗ Evidence structure doesn't track page_id or sha256_pdf per quote
   - ✗ No validation that quotes come from distinct pages/sections
   - **Required:** ≥2 distinct quotes from ≥2 pages per theme
   - **Blocker:** Requires modifications to evidence extraction pipeline (agents/retrieval/*, apps/pipeline/*)

3. **RD Correction** (Status: Not Started)
   - ✗ No rd_sources.json (TCFD/SECR citations)
   - ✗ No targeted section surfacing for Resilience & Dependencies
   - ✗ Current RD scoring may not be TCFD/SECR-aware
   - **Required:** RD ≥ 2 if ≥2 TCFD/SECR citations with metrics/assurance
   - **Blocker:** Requires retrieval + scoring logic updates

4. **Parity & Differential** (Status: Partial)
   - ✓ Basic parity check in single run (evidence_ids ⊆ fused_top_k)
   - ✗ demo_topk_vs_evidence.json NOT CREATED with full per-theme details
   - ✗ Differential tests (α/TOPK variants) not completed due to PYTHONPATH
   - **Required:** Differential report + parity for ≥2 parameter variants
   - **Blocker:** Script execution environment needs hardening

5. **Proof Bundle (QA Gates)** (Status: Partial)
   - ✗ coverage.xml NOT GENERATED (coverage gate not run)
   - ✗ mypy.txt NOT GENERATED (mypy strict check incomplete)
   - ✗ lizard_report.txt NOT GENERATED
   - ✗ interrogate.txt NOT GENERATED
   - ✓ Security report skeleton created (artifacts/security/security_report.json)
   - ✗ SBOM NOT GENERATED
   - **Required:** All QA gates must emit verification artifacts
   - **Blocker:** CI/QA infrastructure needs to run in isolation with proper error handling

6. **Traceability** (Status: Partial)
   - ✗ run_log.txt NOT CREATED (unified execution log)
   - ✗ run_context.json NOT CREATED (input parameters + env snapshot)
   - ✗ run_manifest.json NOT CREATED (file hashes + dependencies)
   - ✗ run_events.jsonl NOT CREATED (per-stage event log)
   - ✗ compliance_status.md NOT CREATED (gate results + proof links)
   - **Required:** All traceability artifacts per SCA v13.8
   - **Blocker:** Requires structured logging integration across orchestration scripts

7. **Authenticity & Hygiene** (Status: Not Validated)
   - ✗ authenticity_ast NOT RUN (checks for TODO/FIXME/PLACEHOLDER/HARDCODED)
   - ✗ placeholders_cp NOT VERIFIED (CP files must be clean)
   - ✗ pinned_deps NOT VERIFIED (requirements.txt pinning check)
   - **Required:** All authenticity gates must pass
   - **Blocker:** AST-based linting tools need to be invoked

### PART B: ROOT CAUSE ANALYSIS

**Primary Blocker Chain:**
1. Bash script environment isolation → PYTHONPATH not propagating to Python subprocesses
2. QA infrastructure not integrated → coverage/mypy/lizard/interrogate gates not running in orchestration
3. Traceability infrastructure missing → no unified run_log/manifest/events
4. Evidence pipeline not evidence-aware → quotes don't track page_id/sha256_pdf/retrieval_rank

**Secondary Issues:**
- RD theme scoring not TCFD/SECR-aware
- Differential test scripts not completing due to environment issues
- Output contract has structural slots but missing detailed proof references

### PART C: REMEDIATION PRIORITY (Fail-Closed Order)

**MUST FIX FIRST (Blocks Everything):**
1. Fix PYTHONPATH propagation in bash scripts → enables 3-run determinism + differential
2. Create run_manifest.json + unified run_log.txt → enables traceability
3. Run QA gates (coverage/mypy/lizard/interrogate) → generates proof artifacts

**SHOULD FIX NEXT (Core Authenticity):**
4. Evidence hardening: Add page_id/sha256_pdf tracking + distinctness validation
5. RD correction: Add TCFD/SECR section surfacing + scoring thresholds
6. Authenticity AST: Run placeholder/TODO checks on CP files

**NICE TO HAVE (Polish):**
7. Differential tests with parameter variants
8. SBOM generation (cyclonedx)

### PART D: CURRENT ARTIFACT TRUTH TABLE

| Artifact | Required | Exists | Valid | Issue |
|----------|----------|--------|-------|-------|
| output_contract.json | ✓ | ✓ | Partial | Missing proof links, determinism/parity/QA refs |
| orchestrator/baseline/run_1/output.json | ✓ | ✓ | ✓ | - |
| orchestrator/baseline/run_2/output.json | ✓ | ✗ | - | Determinism lock not executed |
| orchestrator/baseline/run_3/output.json | ✓ | ✗ | - | Determinism lock not executed |
| determinism_report.json | ✓ | ✗ | - | Requires 3-run completion |
| evidence_audit.json | ✓ | ✗ | - | Requires evidence hardening |
| rd_sources.json | ✓ | ✗ | - | Requires RD correction |
| demo_topk_vs_evidence.json | ✓ | ✗ | - | Requires parity validation |
| run_manifest.json | ✓ | ✗ | - | Requires traceability infra |
| run_log.txt | ✓ | ✗ | - | Requires logging integration |
| coverage.xml | ✓ | ✗ | - | Requires test.cp target |
| mypy.txt | ✓ | ✗ | - | Requires qa.typing target |
| lizard_report.txt | ✓ | ✗ | - | Requires qa.complexity target |
| interrogate.txt | ✓ | ✗ | - | Requires qa.docs target |
| sbom.json | ✓ | ✗ | - | Requires sbom generation |
| compliance_status.md | ✓ | ✗ | - | Requires gate aggregation |

### CONCLUSION

**Current Status:** `status: "revise"`

The E2E orchestration framework is functional at 60% maturity. The system can execute single-run scoring with parity validation, but lacks:
1. Determinism verification (3-run locking)
2. Evidence quality validation (page diversity, distinctness)
3. QA proof artifacts (coverage, typing, complexity, docs)
4. Comprehensive traceability (manifests, logs, compliance report)

**Next Steps:** Implement remediation targets in priority order (see PART C).

---
**Generated:** 2025-10-28T05:30:00Z
**Protocol Version:** SCA v13.8-MEA
**Authenticity Level:** Partial (single-run proven; multi-run/QA unvalidated)
