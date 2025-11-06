# Task 037 Executive Summary
## Remediation of Tasks 031-035: Docling-Only Ingestion & Validation

**Task ID**: 037-remediation-031-035
**Status**: IN_PROGRESS (Validation Phase)
**Created**: 2025-11-04
**Last Updated**: 2025-11-04
**Priority**: HIGH (Blocks production deployment)

---

## Mission Statement

Migrate the Task 031-035 ingestion stack to a **Docling-only pipeline**, removing PyMuPDF dependencies while delivering production-grade chunking, retrieval, and orchestration with comprehensive validation to promote all modules to PROVEN status.

---

## Scope Overview

### In Scope (15 Critical Path Files)
1. **Core Implementations (4)**:
   - `libs/extraction/backend_docling.py` – Docling vision-based PDF converter (authoritative backend)
   - `libs/chunking/structure_aware_chunker.py` – Docling-aware chunking (replaces PyMuPDF logic)
   - `agents/retrieval/hybrid_retriever.py` – BM25 + AstraDB + RRF fusion (no mocks)
   - `agents/orchestration/langgraph_orchestrator.py` – LangGraph StateGraph with SQLite checkpointing

2. **Utility Scripts (8)**: CLI generation, CP manifest updates, documentation assembly, QA sweeps

3. **CLI Entry Points (3)**: chunk_cli.py, hybrid_cli.py, langgraph_cli.py

### Out of Scope (Explicitly Deferred)
- **Task 036**: Async orchestration, resilience infrastructure, chaos testing
- **Production Deployment**: Infrastructure setup follows validation
- **Performance Optimization**: Beyond determinism requirements
- **UI/Dashboard**: Backend focus only

---

## Success Criteria

### Hard Gates (Must Pass)
| Gate | Target | Verification Method |
|------|--------|---------------------|
| **Test Coverage** | ≥95% line coverage on all CP files | pytest --cov --cov-fail-under=95 |
| **E2E Determinism** | 100% hash match across 3 runs | SHA256 comparison with SEED=42 |
| **CLI Functionality** | 100% success with valid inputs | Smoke tests + integration tests |
| **Infrastructure Integration** | Docling, BM25, Astra, watsonx all functional | Integration tests |
| **Documentation Alignment** | 100% claims verified | Traceability matrix |

### Current Status
- **Context Files**: 8/8 complete (hypothesis, design, evidence, data_sources, adr, assumptions, cp_paths, claims_index)
- **Implementation Files**: 11/11 present (Docling backend + remediation targets)
- **Test Files**: 4/4 created with @pytest.mark.cp markers
- **Phase**: Ready for Phase V (Validation) execution

---

## Key Architectural Decisions

### ADR-037-001: Authentic Implementation Over Wrappers
**Decision**: Replace all stub code with real implementations
**Rationale**: EXPERIMENTAL status cannot be promoted without authentic algorithms
**Impact**: ~40 hours effort vs ~4 hours for wrappers, but production-ready

### ADR-037-002: Docling for Structure Detection
**Decision**: Use Docling vision models for table-aware chunking
**Rationale**: Provides structured markdown with tables, headings, and layout metadata
**Impact**: Single backend for ingestion and chunking; removes PyMuPDF dependency

### ADR-037-003: Sentence-Transformers for Local Embeddings
**Decision**: Use all-mpnet-base-v2 for 768-dim embeddings
**Rationale**: Deterministic with seed control, offline-capable, no API costs
**Impact**: ~420MB model download, GPU beneficial but not required

### ADR-037-004: LangGraph with SQLite Checkpointing
**Decision**: Use LangGraph StateGraph with SqliteSaver
**Rationale**: Deterministic routing with watsonx LLM (temperature=0), state persistence
**Impact**: Requires langgraph[sqlite]>=0.2.0, adds SQLite dependency

### ADR-037-005: RRF for Hybrid Fusion
**Decision**: Use Reciprocal Rank Fusion (k=60) to combine BM25 + vector results
**Rationale**: Handles incomparable scores, parameter-free, proven in production
**Impact**: Discards absolute scores, uses rank-based fusion

---

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **PDF Parsing** | Docling | ≥2.6.0 | Vision-based structure extraction |
| **Lexical Search** | rank-bm25 | Latest | BM25 Okapi implementation |
| **Vector DB** | AstraDB (astrapy) | ≥1.5.0 | Semantic similarity search |
| **Embeddings** | sentence-transformers | ≥3.0.1 | Local 768-dim embeddings |
| **Orchestration** | LangGraph | ≥0.2.53 | StateGraph with checkpointing |
| **LLM Router** | watsonx.ai | granite-13b-chat-v2 | Deterministic query routing |
| **Fusion** | Custom RRF | N/A | Reciprocal rank fusion |

---

## Dependencies & Credentials

### External Services (Require Credentials)
- **AstraDB**: Vector similarity search
  - Required: `ASTRA_DB_API_ENDPOINT`, `ASTRA_DB_APPLICATION_TOKEN`
  - Fallback: Mock for offline testing
- **watsonx.ai**: LLM for scoring & orchestration routing
  - Required: `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_MODEL_ID`
  - Usage: ESG rubric scoring, LangGraph router (temperature=0)

### Local Components (No External Dependencies)
- **Docling Backend**: Vision models cached locally
- **BM25 Search**: In-memory indices (no service required)
- **Sentence-Transformers**: Local model cache (~420MB download)
- **SQLite Checkpointing**: File-based persistence

---

## Validation Strategy

### Phase V: Validation (Zero-Touch Evidence Gathering)
11 validation gates executed sequentially without code changes:
- **V0**: Environment snapshot + pip-audit
- **V1**: Toolchain verification (ruff, mypy, pytest, bandit, detect-secrets)
- **V2**: Static hygiene (ruff check, mypy --strict)
- **V3**: Doc/config reconciliation (Task 036 status, .env.template)
- **V4**: Implementation smoke tests (chunker CLI, hybrid CLI)
- **V5**: Targeted pytest coverage (≥95% on CP modules)
- **V6**: Parity & determinism validation (3-run hash comparison)
- **V7**: Schema/vector dimension check (Astra collection)
- **V8**: TODO/digital exhaust audit
- **V9**: Security scans (bandit, detect-secrets)
- **V10**: Status synthesis (STATUS.json generation)

### Phase R: Remediation (Systematic Fixes)
Apply fixes only after validation review, then re-validate affected gates.

---

## Risk Assessment

### High Risks (Mitigated)
| Risk | Impact | Mitigation |
|------|--------|------------|
| AstraDB connection failures | Vector tests fail | Mock DB for offline, skip gracefully |
| watsonx API unavailable | Router fails | Fallback to rule-based routing |
| PDF parsing edge cases | Chunker crashes | Comprehensive test corpus |

### Medium Risks (Monitored)
- Dependency version conflicts → Fresh venv install test
- Non-deterministic LLM routing → Temperature=0, checkpointing
- Test environment setup complexity → Docker compose for services

### Low Risks (Accepted)
- Documentation drift → Automated generation
- Performance slower than optimized → Acceptable for v1
- Model download time → Cache in CI/CD

---

## Promotion Criteria

### Current Status: EXPERIMENTAL
**Modules remain EXPERIMENTAL** unless ALL gates pass (fail-closed per ADR-037-007)

### Target Status: PROVEN
**Promotion Decision Tree**:
```
IF (test_coverage >= 95%)
AND (e2e_determinism == PASS)
AND (cli_functionality == 100%)
AND (infrastructure == WORKING)
AND (documentation == ALIGNED)
THEN promote to PROVEN
ELSE remain EXPERIMENTAL with remediation plan
```

---

## Timeline & Effort

**Total Estimated Effort**: 40 hours (1 week full-time)

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 0: Setup | 2 hours | ✅ COMPLETE |
| Phase 1: Utility Scripts | 4 hours | ✅ COMPLETE |
| Phase 2: Authentic Implementations | 16 hours | ✅ COMPLETE |
| Phase 3: CLI Wrappers | 4 hours | ✅ COMPLETE |
| Phase 4: Testing | 8 hours | ✅ COMPLETE |
| Phase 5: E2E Validation | 4 hours | 🔄 IN PROGRESS |
| Phase 6: Documentation | 2 hours | ⏳ PENDING |

**Current Phase**: Phase 5 (E2E Validation) - Ready to execute Phase V validation gates

---

## Key Metrics

### Code Metrics (Target)
- **LOC per module**: ≥300 (authentic implementations)
- **Test coverage**: ≥95% line, ≥90% branch
- **Cyclomatic complexity**: ≤10 (Lizard)
- **Type safety**: mypy --strict = 0 errors

### Quality Metrics (Target)
- **Determinism**: 100% hash match (3 runs)
- **CLI success rate**: 100% with valid inputs
- **Infrastructure uptime**: 99%+ for Astra/watsonx
- **Documentation accuracy**: 100% claims verified

### Performance Metrics (Baseline, not optimized)
- **PDF chunking**: <30s per document
- **Hybrid retrieval**: <10s per query
- **E2E pipeline**: <60s per query (with scoring)

---

## Deliverables Checklist

### Context Documentation (8/8 Complete)
- [x] hypothesis.md - Metrics, success criteria, CP files
- [x] design.md - Data strategy, verification plan
- [x] evidence.json - 6 sources with DOIs
- [x] data_sources.json - 6 sources with provenance
- [x] adr.md - 7 architectural decisions
- [x] assumptions.md - 12 assumptions + Task 036 deferral
- [x] cp_paths.json - 14 CP files registered
- [x] claims_index.json - 12 claims with traceability

### Implementation Files (10/10 Present)
- [x] All critical implementation files verified

### Test Files (4/4 Created)
- [x] test_structure_aware_chunker_037.py
- [x] test_hybrid_retriever_037.py
- [x] test_langgraph_orchestrator_037.py
- [x] test_utility_scripts_037.py

### Validation Artifacts (Pending Phase V)
- [ ] STATUS.json (comprehensive gate results)
- [ ] coverage_037.xml (≥95% proof)
- [ ] determinism_report.json (3-run comparison)
- [ ] validation_report_037.json (analyst summary)

---

## Next Steps

### Immediate (Phase V Validation)
1. ✅ Execute V0-V2: Environment, toolchain, static hygiene
2. ✅ Execute V3: Doc reconciliation (Task 036 status verified)
3. ⏳ Execute V4-V9: Smoke tests, coverage, determinism, security
4. ⏳ Generate V10: STATUS.json with pass/fail/skip per gate

### After Validation (Phase R Remediation)
1. Review STATUS.json for any failures
2. Apply targeted fixes for failed gates
3. Re-run affected validation gates
4. Generate final validation report

### Completion Criteria
- All validation gates PASS or SKIP (with documented reason)
- Coverage ≥95% on all CP modules
- E2E determinism verified (3 runs)
- STATUS.json shows VALIDATION_PASSED
- Ready for PROVEN status promotion

---

## Contact & References

**Task Owner**: SCA v13.8-MEA Agent
**Protocol**: Scientific Coding Agent (SCA) v13.8 with Mandatory Execution Algorithm (MEA)
**Execution Plan**: tasks/037-remediation-031-035/EXECUTION_PLAN.md v4.0
**Scaffolding Analysis**: tasks/037-remediation-031-035/SCAFFOLDING_ANALYSIS.md

**Key Documents**:
- Hypothesis: `context/hypothesis.md`
- ADRs: `context/adr.md`
- Claims: `context/claims_index.json`
- Task 036 Status: `context/assumptions.md` (Task 036 Deferral section)

---

**End of Executive Summary**
**Status**: READY FOR PHASE V VALIDATION
**Next Action**: Execute `sca-protocol-skill/commands/validate-only.ps1` or run EXECUTION_PLAN.md Phase V gates
