# Authenticity Audit Remediation Revert Playbook

**Audit**: ESG Authenticity Audit v13.8 (AV-001)
**Purpose**: Recovery procedures if remediations need to be rolled back
**Created**: 2025-10-26

---

## Quick Rollback (Full Revert to Baseline)

If remediation efforts need to be abandoned entirely:

```bash
# Revert to baseline commit before any remediations
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- apps/ libs/ scripts/ agents/

# Or, hard reset to baseline
git reset --hard c8798c56fd71826c7cb0093d9f3c65a68059926c

# Verify revert
git status
git log --oneline -5
```

---

## Baseline Commit Reference

| Property | Value |
|----------|-------|
| SHA | `c8798c56fd71826c7cb0093d9f3c65a68059926c` |
| Message | Enforce JSON schema as single source of truth for ESG rubric |
| Date | ~2025-10-26 |
| Files | apps/, libs/, scripts/, agents/ |

---

## Selective Revert by Violation Type

### 1. Revert eval/exec() Removals (34 FATAL)

These changes affected CLI tools and script utilities.

```bash
# If eval/exec remediations were applied to these files:
# - scripts/generate_headlam_report.py
# - scripts/diagnose_quality_issues.py
# - agents/*/utilities.py
# - Any other eval()/exec() sites

# Selective revert:
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- scripts/
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- agents/

# Or revert specific file:
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- scripts/generate_headlam_report.py
```

### 2. Revert datetime.now() Overrides (76 WARN)

Time-related overrides were added to:
- apps/evaluation/
- apps/ingestion/
- apps/scoring/

```bash
# Revert all scoring/evaluation/ingestion:
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- apps/scoring/ apps/evaluation/ apps/ingestion/

# Or revert specific file:
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- apps/scoring/pipeline.py
```

### 3. Revert Silent Exception Logging (74 WARN)

Logging was added to exception handlers in:
- apps/ingestion/validator.py
- scripts/compare_esg_analysis.py
- libs/retrieval/hybrid_retriever.py

```bash
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- apps/ingestion/validator.py
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- scripts/compare_esg_analysis.py
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- libs/retrieval/hybrid_retriever.py
```

### 4. Revert JSON→Parquet Migration (8 WARN)

Parquet migrations affected:
- libs/storage/ (data writers)
- scripts/generate_*.py (report generation)

```bash
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- libs/storage/
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- scripts/generate_*.py
```

### 5. Revert Dict Ordering Fixes (9 WARN)

Sorting changes in:
- libs/scoring/
- libs/retrieval/

```bash
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- libs/scoring/
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- libs/retrieval/
```

### 6. Revert Unseeded Random Fixes (2 FATAL)

Random seeding changes:
- libs/embedding/deterministic_embedder.py
- Any agent using random sampling

```bash
git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- libs/embedding/deterministic_embedder.py
```

---

## Per-Commit Revert (If Tracking Individual Fixes)

If remediations were committed incrementally:

```bash
# List all commits since baseline
git log c8798c56fd71826c7cb0093d9f3c65a68059926c..HEAD --oneline

# Revert specific commit(s)
git revert <commit-sha>  # Creates new commit undoing the change
# OR
git reset --hard <commit-before-fix>  # Hard reset to state before fix
```

---

## Validation After Revert

After any revert operation:

1. **Verify git state**:
   ```bash
   git status
   git log --oneline -5
   ```

2. **Run audit again** to confirm baseline violations return:
   ```bash
   export PYTHONHASHSEED=0 SEED=42
   python scripts/qa/authenticity_audit.py --root . --out artifacts/authenticity
   ```

3. **Expected outcome**: report.json should match BASELINE_SNAPSHOT.json

4. **Run tests** to ensure code still works:
   ```bash
   pytest tests/ -v
   ```

---

## Revert with Stash (Preserve Working Changes)

If you have uncommitted remediation work in progress:

```bash
# Save current work
git stash push -m "remediation-work-in-progress"

# Revert to baseline
git reset --hard c8798c56fd71826c7cb0093d9f3c65a68059926c

# Restore work later if needed
git stash pop
```

---

## Emergency Full Revert

If something critical breaks:

```bash
# The nuclear option - discard all local changes
git clean -fdx
git reset --hard c8798c56fd71826c7cb0093d9f3c65a68059926c

# Verify clean state
git status  # Should show "nothing to commit"
```

---

## Audit Trail

All reverts are tracked in git history:

```bash
# See all revert commits
git log --grep="Revert" --oneline

# See full diff of revert
git show <revert-commit-sha>
```

---

## Prevention: Atomic Commits

When remediating, use atomic commits per violation class:

```bash
# Commit pattern for safety
git commit -m "fix(authenticity): eval/exec in scripts/ - AV-001"  # All eval fixes
git commit -m "fix(authenticity): datetime.now in apps/scoring - AV-001"  # All time fixes
git commit -m "fix(authenticity): silent exceptions in validator - AV-001"  # All exception fixes
```

This allows selective revert:
```bash
git revert <commit-sha>  # Revert just one class of fixes
```

---

## Rollback Decision Tree

```
Did something break?
├─ YES, need full revert
│  └─ git reset --hard c8798c56fd71826c7cb0093d9f3c65a68059926c
│
└─ NO, need selective revert
   ├─ eval/exec fixes broke something?
   │  └─ git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- scripts/ agents/
   │
   ├─ datetime overrides broke something?
   │  └─ git checkout c8798c56fd71826c7cb0093d9f3c65a68059926c -- apps/
   │
   └─ Other issue?
      └─ Use REMEDIATION_LOG.md to find specific commit SHA
         └─ git revert <commit-sha>
```

---

## Verification Checklist

After any revert, verify:

- [ ] `git status` shows clean or expected state
- [ ] `git log` shows correct commit order
- [ ] `pytest tests/test_authenticity_audit.py` passes
- [ ] Audit re-run produces expected baseline violations
- [ ] No unintended files were reverted (check git diff)
- [ ] Remote not yet pushed (if planning different approach)

---

## Support

If revert goes wrong:

1. Check `git reflog` for previous commit states
2. Contact team lead with `git log -20 --oneline`
3. File issue: "Authenticity Audit Revert Failed" with full git history

---

**Last Updated**: 2025-10-26
**Baseline Commit**: c8798c56fd71826c7cb0093d9f3c65a68059926c
