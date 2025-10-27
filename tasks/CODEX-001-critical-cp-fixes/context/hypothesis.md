# CODEX-001: Critical CP Fixes — Hypothesis

**Task ID**: CODEX-001
**Date**: 2025-10-27
**Protocol**: SCA v13.8-MEA

## Hypothesis

**Critical Path (CP) code contains placeholder/stub logic that violates SCA v13.8 authenticity requirements, blocking compliance gates.**

## Metrics

### Primary Metrics
1. **CP Authenticity Compliance**: 0 stub/placeholder violations in CP files
2. **Determinism**: 100% time calls use `get_audit_time()` in CP
3. **Dependency Hygiene**: All used dependencies declared in requirements.txt
4. **Protocol Version**: Config matches canonical protocol (v13.8)

### Success Thresholds
- ✅ All P0-P1 violations resolved (5 items)
- ✅ `apps/scoring/scorer.py` implements real logic OR has `# @allow-const` + tests
- ✅ `libs/retrieval/semantic_retriever.py` uses real similarity scores OR documented placeholder
- ✅ All `datetime.now()` calls in CP replaced with `get_audit_time()`
- ✅ `requests` package declared in requirements.txt
- ✅ `.sca_config.json` updated to protocol_version "13.8"

## Critical Path Scope

Files to remediate:
1. `apps/scoring/scorer.py` — Remove hardcoded stub returns
2. `libs/retrieval/semantic_retriever.py` — Replace placeholder scoring + non-deterministic time
3. `requirements.txt` — Add missing `requests` dependency
4. `.sca_config.json` — Update protocol version

## Exclusions
- Non-CP files (tests, scripts) — Acceptable to defer
- AV-001 violations already tracked — Continue in Phases 4-6
- P2-P3 findings — Address opportunistically

## Power Analysis & Confidence Interval
- **Sample**: 5 critical violations identified by Codex audit
- **Expected Impact**: Unblock CP compliance gates (authenticity_ast, placeholders_cp)
- **Confidence**: 95% that fixes will resolve blocking issues

## Risks
1. **Scorer stub**: May be unused (check call sites)
2. **Similarity score**: May need AstraDB API research
3. **Time replacement**: May affect existing tests
4. **Protocol update**: May reveal additional config mismatches

## Verification Plan
1. Grep for hardcoded returns in CP files → 0 matches without `# @allow-const`
2. Grep for `datetime.now()` in CP → 0 matches
3. Grep for `import requests` → matches declared dependency
4. Check protocol version → v13.8
5. Run validation gates → authenticity_ast PASS, placeholders_cp PASS
