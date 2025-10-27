# Design: QA and Explainability Agents

## QA Agent Tools
- **assurance.checks**: Validate data quality metrics (completeness, accuracy, consistency)
- **iceberg.profile**: Statistical profiling of Iceberg tables (null rates, distributions)
- **drift.compare**: Detect scoring drift between snapshots

## Explainability Agent Tools
- **evidence.table**: Retrieve evidence rows for specific scores with page references
- **graphrag.expand**: Expand evidence via AstraDB graph traversal
- **join.columnar**: Join Iceberg scores with AstraDB evidence manifests

## Verification Plan

### QA Gate Tests
```python
@pytest.mark.cp
def test_qa_drift_detection():
    """Test drift detection between snapshots"""
    baseline = iceberg.snapshot(snapshot_id=baseline_id)
    current = iceberg.snapshot(snapshot_id=current_id)
    drift = qa_agent.detect_drift(baseline, current)
    assert drift.false_positive_rate < 0.1

@pytest.mark.cp
def test_explainability_completeness():
    """Test all scores have explanations"""
    scores = gold.esg_scores.read()
    for score in scores:
        explanation = explain_agent.explain(score.id)
        assert explanation.evidence_count > 0
        assert explanation.page_refs is not None
```

## Success Criteria
- **QA Pass Rate**: >= 90% of checks passing
- **Drift False Positives**: < 10%
- **Evidence Retrieval**: < 500ms per query
- **Explanation Completeness**: > 95% of scores explainable
- **Coverage**: >= 95% line/branch on CP
