# Design: Iceberg Silver/Gold Layers

## Data Strategy

### Silver Layer: silver.esg_normalized
- Deduplicated, normalized ESG findings
- MERGE upserts based on (org_id, finding_hash)
- Hidden partitioning on org_id, year, theme
- Schema evolution enabled for backward compatibility

### Gold Layer: gold.esg_scores
- Maturity scores with confidence
- Linked to AstraDB evidence manifests
- Snapshot IDs for reproducibility
- Historical tracking via time-travel queries

## Normalization Strategy
- Deduplication: Hash-based on (org_id, finding_text, source_doc)
- Schema validation: PyArrow enforcement with error logging
- Consistency: ACID guarantees via Iceberg transactions

## Verification Plan

### Functional Tests
```python
@pytest.mark.cp
def test_merge_upsert_idempotency():
    """Test MERGE operations are idempotent"""
    result1 = normalizer.merge(findings)
    result2 = normalizer.merge(findings)
    assert result1.snapshot_id != result2.snapshot_id
    assert result1.record_count == result2.record_count

@pytest.mark.cp
@given(st.lists(st.builds(Finding)))
def test_scoring_confidence_variance(findings):
    """Property: Confidence varies with evidence quality"""
    scores = scorer.score(findings)
    assert max(scores.confidence) - min(scores.confidence) > 0.3
```

### Performance Tests
- MERGE throughput: Benchmark 10,000 records
- Time-travel overhead: Query historical snapshots
- Concurrent writes: Test snapshot isolation

### Differential Tests
- Compare scores: Legacy vs Iceberg implementation
- Validate evidence links: Cross-check AstraDB manifests
- Confidence calibration: Verify variance across quality levels

## Success Thresholds
- **MERGE Performance**: >= 1000 records/sec
- **Schema Evolution**: Zero downtime for column additions
- **Time-travel Overhead**: < 2 seconds
- **Confidence Variance**: > 30% across quality levels
- **watsonx.ai Success Rate**: > 95%
- **Coverage**: >= 95% line/branch on CP
- **Type Safety**: 0 mypy --strict errors on CP
