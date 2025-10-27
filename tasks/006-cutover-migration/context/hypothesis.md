# Hypothesis: Cutover and Migration

## Core Hypothesis
Running legacy and Iceberg systems in parallel with automated diff reporting will enable confident migration with measurable score agreement and zero data loss.

## Success Metrics
- **Dual-Run Match Rate**: > 95% score agreement
- **Migration Duration**: < 2 weeks total
- **Data Loss**: 0 records
- **Rollback Capability**: < 1 hour to revert
- **Stakeholder Acceptance**: 100% sign-off

## Critical Path Components
- `migration/dual_run.py` - Parallel execution of legacy + Iceberg
- `migration/diff_reporter.py` - Automated score comparison
- `migration/cutover.py` - Endpoint migration for Watson Orchestrate
- `migration/rollback.py` - Snapshot-based rollback mechanism

## Input/Output Specifications
**Inputs:**
- Legacy scores from current system
- Iceberg scores from new system
- Comparison thresholds (tolerance for match)

**Outputs:**
- Diff reports highlighting discrepancies
- Match rate statistics
- Go/no-go recommendation
- Rollback snapshots

## Verification Strategy
- Run both systems on identical input data
- Compare outputs with tolerance for rounding
- Validate evidence linkage preserved
- Test rollback mechanism
