# Design: Ops Agent

## Agent Tools
- **timegate.check(table, stale_days)**: Scan Iceberg snapshots for records older than threshold
- **reingest.if_stale(org_ids)**: Trigger Crawler Agent for stale organizations
- **coverage.report(dimension)**: Generate data coverage metrics by org/theme/year

## Staleness Detection Strategy
```python
def check_staleness(table: str, threshold_days: int = 730):
    """Check for stale data using Iceberg snapshot metadata"""
    snapshots = iceberg.table(table).snapshots()
    cutoff_ts = datetime.now() - timedelta(days=threshold_days)

    stale_orgs = []
    for snapshot in snapshots:
        if snapshot.timestamp < cutoff_ts:
            stale_orgs.extend(get_org_ids(snapshot))

    return stale_orgs
```

## Quality-Triggered Fetching
- Monitor extraction_quality from bronze layer
- Monitor classification_confidence from gold layer
- Trigger MCP fetch if quality < 0.7 OR confidence < 0.65

## Success Criteria
- **Stale Detection**: 100% recall, 0% false negatives
- **MCP Trigger Accuracy**: > 90%
- **Re-ingestion Throughput**: > 5 companies/day
- **Coverage**: >= 95% line/branch on CP
