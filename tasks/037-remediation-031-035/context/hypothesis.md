# Task 037: Remediation of Tasks 031-035 - Authentic Implementation

## Hypothesis

Migrating the structure-aware chunker and ingestion stack to Docling, alongside production-grade retrieval and orchestration with proper infrastructure setup, CLI interfaces, and comprehensive testing, will enable promotion from EXPERIMENTAL to PROVEN status while eliminating PyMuPDF dependencies. Success is defined as ≥95% test coverage, 3-run determinism validation, and Docling-exclusive ingestion.

## Metrics & Success Criteria

### Primary Metrics

1. **Implementation Completeness**
   - **Metric:** LOC of authentic implementation vs stub/wrapper code
   - **Threshold:** ≥300 LOC per module with real algorithms (not simple pass-through)
   - **Measurement:** Code review + algorithmic fidelity check

2. **Test Coverage**
   - **Metric:** Line and branch coverage for new implementations
   - **Threshold:** ≥95% coverage for all CP files
   - **Measurement:** `pytest --cov --cov-report=xml`

3. **E2E Determinism**
   - **Metric:** SHA256 hash consistency across 3 independent runs
   - **Threshold:** 100% hash match across all output artifacts (scoring, evidence, maturity)
   - **Measurement:** 3-run E2E test with SEED=42, PYTHONHASHSEED=0

4. **CLI Functionality**
   - **Metric:** Success rate of CLI execution with real inputs
   - **Threshold:** 100% success for all CLI wrappers with valid inputs
   - **Measurement:** CLI smoke tests + integration tests

### Secondary Metrics

5. **Infrastructure Integration**
   - **Metric:** Successful connections to AstraDB, embedding models, checkpoint databases
   - **Threshold:** All infrastructure components functional
   - **Measurement:** Integration test suite

6. **Documentation Alignment**
   - **Metric:** Design claims matching implemented features
   - **Threshold:** 100% of design.md claims verifiable in code
   - **Measurement:** Traceability matrix (claim → implementation → test)

## Critical Path (CP) Files

**New Implementations (3):**
1. `libs/extraction/backend_docling.py` - Docling vision-based PDF backend
2. `libs/chunking/structure_aware_chunker.py` - Docling-aware chunking with markdown semantics
3. `agents/retrieval/hybrid_retriever.py` - Real BM25 + AstraDB + RRF fusion with infrastructure setup
4. `agents/orchestrator/langgraph_orchestrator.py` - LangGraph StateGraph with SQLite checkpointing

**Utility Scripts (8):**
1. `scripts/generate_cli_wrapper.py` - CLI wrapper generator
2. `scripts/update_cp_manifest.py` - CP manifest updater
3. `scripts/context_report_assembler.py` - Context documentation assembler
4. `scripts/update_design_refs.py` - Design doc reference updater
5. `scripts/reconcile_plan.py` - Plan reconciliation validator
6. `scripts/qa_sweep.py` - QA validation sweeper
7. `scripts/emit_contract.py` - Output contract generator
8. `scripts/finalize_validation.py` - Final validation report generator

**CLI Entry Points (3):**
1. `scripts/chunk_cli.py` - Structure-aware chunker CLI
2. `scripts/hybrid_cli.py` - Hybrid retriever CLI
3. `scripts/langgraph_cli.py` - LangGraph orchestrator CLI

**Total CP Files:** 14

## Exclusions

**Out of Scope:**
- Task 036 resilience infrastructure (deferred to separate task)
- Production deployment (deployment phase follows validation)
- Performance optimization beyond determinism requirements
- UI/dashboard components
- Real-time monitoring infrastructure

## Power Analysis & Confidence Intervals

**Statistical Requirements:**
- **Determinism tests:** 3 runs minimum (binomial test, p<0.01 for hash mismatch detection)
- **Coverage sampling:** All lines executed at least once (100% code path coverage)
- **Integration tests:** ≥5 test cases per integration point (95% CI on failure detection)

**Confidence Levels:**
- **95% CI on determinism:** 3 runs with 0 hash mismatches → 99.9% confidence of deterministic behavior
- **95% CI on coverage:** ≥95% line coverage → 95% confidence all critical paths tested

## Risk Assessment

**High Risks:**
1. **AstraDB connection failures** - Mitigation: Fallback to mock DB for offline testing
2. **Embedding model download failures** - Mitigation: Cache models, provide local copies
3. **LangGraph version incompatibility** - Mitigation: Pin exact versions in requirements
4. **Test environment torch conflicts** - Mitigation: Isolated test environments

**Medium Risks:**
1. **PDF parsing edge cases** - Mitigation: Comprehensive test corpus with varied PDFs
2. **RRF fusion parameter sensitivity** - Mitigation: Parameter sweep tests
3. **CLI wrapper complexity** - Mitigation: Template-based generation

**Low Risks:**
1. **Documentation drift** - Mitigation: Automated doc generation
2. **CP manifest sync** - Mitigation: Automated manifest updates

## Validation Gates

**Gate 1: Context Complete**
- All 7 context files present and valid
- CP paths registered (14 files)
- Evidence sources ≥3 with DOIs

**Gate 2: Implementation Complete**
- All 3 authentic modules implemented (≥300 LOC each)
- All 8 utility scripts functional
- All 3 CLI wrappers operational

**Gate 3: Test Coverage ≥95%**
- pytest --cov reports ≥95% line coverage
- pytest --cov reports ≥90% branch coverage
- All CP files have ≥1 test marked @pytest.mark.cp

**Gate 4: E2E Determinism PASS**
- 3 runs produce identical SHA256 hashes
- All output artifacts match across runs
- SEED=42, PYTHONHASHSEED=0 enforced

**Gate 5: Documentation Aligned**
- Design claims match implementation
- Traceability matrix complete
- README updated with new module usage

**Gate 6: Promotion Decision**
- All gates passed → PROVEN
- Any gate failed → EXPERIMENTAL with remediation plan

## Timeline & Phases

**Phase 0: Setup (2 hours)**
- Create task structure
- Create context files
- Create git branch

**Phase 1: Utility Scripts (4 hours)**
- Implement 8 utility scripts
- Test each script independently

**Phase 2: Authentic Implementations (16 hours)**
- Structure-aware chunker (6 hours)
- Hybrid retriever (6 hours)
- LangGraph orchestrator (4 hours)

**Phase 3: CLI Wrappers (4 hours)**
- Generate 3 CLI entry points
- Test CLI functionality

**Phase 4: Testing (8 hours)**
- Write comprehensive test suites
- Achieve ≥95% coverage
- Fix all test failures

**Phase 5: E2E Validation (4 hours)**
- Run 3-run determinism tests
- Generate validation artifacts
- Create final reports

**Phase 6: Documentation (2 hours)**
- Update design docs
- Create traceability matrix
- Update README

**Total Estimated Effort:** 40 hours (1 week full-time)

## Success Criteria Summary

**Must Have (Hard Gates):**
1. ✅ Test coverage ≥95% for all CP files
2. ✅ E2E 3-run determinism PASS (100% hash match)
3. ✅ All CLI wrappers functional
4. ✅ All infrastructure integrations working
5. ✅ Documentation aligned with implementation

**Should Have (Soft Gates):**
1. ⭐ Response time <5s for chunking operations
2. ⭐ Retrieval precision ≥0.8 on test corpus
3. ⭐ Orchestrator routing accuracy ≥90%

**Nice to Have:**
1. 💡 Performance benchmarks
2. 💡 Error rate monitoring
3. 💡 Integration with CI/CD

## Acceptance Criteria

**Task 037 is COMPLETE when:**
1. All 14 CP files implemented and tested
2. Coverage ≥95% on all CP files
3. E2E determinism PASS (3 runs)
4. All modules promoted to PROVEN status
5. Final validation report generated
6. Git branch merged to main

---

**Task ID:** 037
**Task Slug:** remediation-031-035
**Created:** 2025-11-04
**Estimated Effort:** 40 hours
**Priority:** High (blocks production deployment of experimental modules)
