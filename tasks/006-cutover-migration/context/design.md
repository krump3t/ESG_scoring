# Design: Migration Strategy

## Dual-Run Approach
1. **Week 1**: Parallel execution, daily diff reports
2. **Week 2**: Validation period, stakeholder review
3. **Cutover**: Switch Watson Orchestrate endpoints when match rate > 95%
4. **Monitoring**: 2-week observation period

## Diff Reporting
```python
def compare_scores(legacy_scores, iceberg_scores):
    """Compare scores with tolerance"""
    matches = 0
    mismatches = []

    for org_id in legacy_scores.keys():
        legacy = legacy_scores[org_id]
        iceberg = iceberg_scores.get(org_id)

        if not iceberg:
            mismatches.append({"org_id": org_id, "issue": "missing_in_iceberg"})
            continue

        # Allow +/-1 stage difference
        if abs(legacy.stage - iceberg.stage) <= 1:
            matches += 1
        else:
            mismatches.append({
                "org_id": org_id,
                "legacy_stage": legacy.stage,
                "iceberg_stage": iceberg.stage,
                "diff": abs(legacy.stage - iceberg.stage)
            })

    match_rate = matches / len(legacy_scores)
    return match_rate, mismatches
```

## Rollback Strategy
- Tag Iceberg snapshots before cutover
- Preserve legacy system for 30 days
- One-command rollback via snapshot restore

## Success Criteria
- **Match Rate**: > 95%
- **Migration Time**: < 2 weeks
- **Data Loss**: 0 records
- **Rollback Time**: < 1 hour
