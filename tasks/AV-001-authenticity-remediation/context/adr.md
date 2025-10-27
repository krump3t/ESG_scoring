# ADR-001: Authenticity Remediation Architecture Decisions

**Status**: ACCEPTED
**Date**: 2025-10-26
**Decision Maker**: SCA v13.8-MEA Protocol

---

## ADR-001.1: Sequential Phase Execution (vs. Parallel)

### Context
203 violations span 5 categories with potential interdependencies:
- Removing eval/exec (Phase 1) might affect code paths using randomness
- Seeding randomness (Phase 2) might require refactoring evaluated code
- Enforcing parity (Phase 3) might conflict with non-deterministic seeding

### Decision
Execute phases **sequentially** (1 → 2 → 3 → 4 → 5 → 6), not in parallel.

### Rationale
1. **Dependency clarity**: Each phase depends on success of previous phases
2. **Risk containment**: If Phase 2 fails, we haven't wasted effort on Phase 3-5
3. **Regression detection**: Full test suite run between phases catches cascading failures
4. **Audit trail**: Clear git commits per phase for regulatory compliance

### Alternatives Considered
- **Parallel execution** (phases 1-5 in separate branches)
  - **Rejected**: Higher merge conflict risk, harder to isolate regressions
- **Breadth-first** (fix 1 violation per category)
  - **Rejected**: Longer feedback loop, harder to track phase progress

### Consequences
- **Positive**: Clear progress tracking, isolated rollback capability
- **Negative**: Longer total execution time (14-22 hours), blocking upstream work

---

## ADR-001.2: Git Tag-Based Checkpointing (vs. Database Snapshots)

### Context
Need to preserve ability to revert if phase remediation causes regressions.

### Decision
Use **git tags** for phase checkpoints:
- `audit-baseline-20251026` - Pre-remediation baseline
- `audit-phase1-complete-<hash>` - After Phase 1
- `audit-phase2-complete-<hash>` - After Phase 2
- (etc.)

### Rationale
1. **Immutable audit trail**: Git history is cryptographically signed
2. **Low overhead**: Tags are lightweight, no storage cost
3. **Regulatory ready**: Full blame history for compliance audits
4. **Simple rollback**: `git reset --hard <tag>` recovers any phase

### Alternatives Considered
- **Database snapshots** (store artifact JSON)
  - **Rejected**: Harder to trace which code changes caused regressions
- **Backup branches** (separate branch per phase)
  - **Rejected**: More overhead, harder to manage long-term

### Consequences
- **Positive**: Clear audit trail, immutable checkpoints
- **Negative**: Requires discipline to tag consistently

---

## ADR-001.3: Real Data Validation for Phases 3-4 (vs. Synthetic Only)

### Context
Evidence parity (Phase 3) and error handling (Phase 4) benefit from validation against real ESG claims, but PII considerations limit access to production database.

### Decision
Use **cached public ESG reports** (not synthetic data) for validation:
- Apple Inc. 2024 ESG Report (public on investor relations)
- Microsoft Corp. 2024 Sustainability Report
- Real SEC EDGAR URLs (cached locally)

### Rationale
1. **Authenticity**: Real claims surface edge cases synthetic data misses
2. **Regulatory alignment**: Uses actual disclosure formats
3. **No PII leakage**: All sources are public (investor relations)
4. **Reproducibility**: Cached reports prevent URL availability issues

### Alternatives Considered
- **100% synthetic data** (e.g., generated via LLM)
  - **Rejected**: Misses real-world edge cases, not regulatory credible
- **Production database** (with PII redaction)
  - **Rejected**: Operational risk, PII exposure despite redaction

### Consequences
- **Positive**: Higher confidence in production readiness
- **Negative**: Requires fetching and caching reports (30-60 min setup)

---

## ADR-001.4: Determinism Verification via 3x Identical Runs (vs. Statistical Sampling)

### Context
Phase 2 (determinism) requires proving that 3x runs produce identical results. Options:
- 3x runs (binary yes/no)
- 10x runs with statistical confidence interval
- Monte Carlo sampling

### Decision
Use **3x runs with byte-identical comparison**:
```bash
export FIXED_TIME=1729000000.0 SEED=42
for i in {1..3}; do
  python evaluate.py > run_$i.json
  sha256sum run_$i.json >> hashes.txt
done
# ✅ All 3 hashes must be identical
```

### Rationale
1. **Determinism requirement**: "Identical" means byte-identical, not statistically similar
2. **Simplicity**: 3 runs = quick feedback (10 min), not 10x = 30 min
3. **Regulatory clarity**: Binary pass/fail easier to defend than CI intervals

### Alternatives Considered
- **10x runs + CI bounds** (95% confidence)
  - **Rejected**: Determinism is binary, not probabilistic
- **Single run + determinism unit tests**
  - **Rejected**: Misses integration-level non-determinism

### Consequences
- **Positive**: Clear yes/no validation, fast execution
- **Negative**: Doesn't detect rare non-determinism (very low probability)

---

## ADR-001.5: ISSUE_TRACKER.md as Manual Tracking (vs. Automated Tool)

### Context
203 violations need tracking as they're fixed. Options:
- Manual ISSUE_TRACKER.md (spreadsheet-like markdown)
- Automated tool (Jira, GitHub Issues)
- Git commits only

### Decision
Use **ISSUE_TRACKER.md** (markdown file with checkboxes) as primary tracking.

### Rationale
1. **Simplicity**: No tool setup, fits in existing git workflow
2. **Offline-friendly**: Works without internet/Jira access
3. **SCA compliance**: Markdown artifacts part of SCA deliverables
4. **Real-time collaboration**: Easy to see progress in pull request

### Alternatives Considered
- **GitHub Issues** (automated)
  - **Rejected**: Requires API access, slower iteration
- **Git commits only** (no separate tracking)
  - **Rejected**: Hard to see macro progress (are we 50% done?)

### Consequences
- **Positive**: Low overhead, human-readable
- **Negative**: Requires manual updates (but forces discipline on progress reporting)

---

## ADR-001.6: 6-Phase Structure (vs. Monolithic or 10-Phase)

### Context
203 violations span 5 categories. Should phases map 1:1 to categories or differently?

### Decision
Use **6-phase structure**:
1. Phase 1: FATAL violations (34 issues)
2. Phase 2: Determinism (87 issues)
3. Phase 3: Evidence parity + Rubric (29 issues)
4. Phase 4: Production posture (12 issues)
5. Phase 5: Silent failures & error handling (74 issues)
6. Phase 6: Final verification & completion

### Rationale
1. **Risk progression**: FATAL first (highest risk), Verification last (lowest risk)
2. **Natural dependencies**: Phase 1 must complete before Phases 2-5 can build on it
3. **Verification phase**: Separate final phase ensures no regressions after other phases
4. **Timeline realism**: 6 phases = ~4 hours each, manageable daily pace

### Alternatives Considered
- **5 phases** (no separate verification)
  - **Rejected**: Misses final validation step
- **10 phases** (one per violation category+subcategory)
  - **Rejected**: Too granular, slows down progress tracking

### Consequences
- **Positive**: Clear progression, manageable phase size
- **Negative**: Phase 3 combines 2 categories (but they're tightly coupled)

---

## ADR-001.7: Three-Day Timeline with Flexibility (vs. Strict Schedule)

### Context
Estimate is 14-22 hours across 3 days, but actual time may vary based on complexity.

### Decision
Target **3-day timeline** with flexibility:
- Day 1: Phases 1-2 (FATAL + Determinism) = 7-12 hours
- Day 2: Phases 3-4 (Evidence + Posture) = 7-10 hours
- Day 3: Phases 5-6 (Errors + Verification) = 3-6 hours

If Phase 1 runs long, roll Phase 2 into Day 2 (no hard deadline).

### Rationale
1. **Realistic estimation**: 14-22 hour range includes uncertainty
2. **Quality over speed**: Better to take 4 days with zero regressions than 3 days with bugs
3. **Morale**: Daily checkpoints (end-of-day) keep momentum up
4. **Regulatory audit trail**: Daily phase completions document progress

### Alternatives Considered
- **Hard 3-day deadline**
  - **Rejected**: Forces corner-cutting if Phase 1 runs long
- **Open-ended timeline**
  - **Rejected**: Loses urgency, work expands infinitely

### Consequences
- **Positive**: Achievable target, allows flexibility
- **Negative**: May extend into Day 4 for complex phases

---

## ADR-001.8: Rollback via Git Tag, Not Stashing

### Context
If a phase goes wrong, how to recover: revert commits, hard reset, or stash?

### Decision
Use **hard reset to git tag** (not revert, not stash):
```bash
git reset --hard audit-baseline-20251026  # Emergency rollback
```

### Rationale
1. **Clean state**: Hard reset clears all uncommitted changes
2. **Immutable**: Tag points to specific commit, can't be accidentally moved
3. **Speed**: One command, no merge conflict resolution
4. **Irreversible intent**: Hard reset signals "this phase failed" clearly

### Alternatives Considered
- **Revert commits** (`git revert`)
  - **Rejected**: Creates reverse-commit clutter, slower to understand history
- **Stash + branch**
  - **Rejected**: Leaves uncommitted work around, confusing

### Consequences
- **Positive**: Clean, fast recovery
- **Negative**: Destructive (clears uncommitted work, but phase work should be committed)

---

## Sign-Off

**ADR Review**: All 8 decisions approved
**Implementation Status**: Ready for Phase 1 execution
**Rollback Plan**: Activated (git tag: audit-baseline-20251026)

---

**Document**: ADR-001 - Authenticity Remediation
**Version**: 1.0
**Created**: 2025-10-26
