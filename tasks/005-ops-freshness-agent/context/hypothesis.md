# Hypothesis: Ops and Freshness Agent

## Core Hypothesis
Implementing an Ops/Freshness Agent that monitors Iceberg snapshot timestamps and triggers quality-based re-ingestion will ensure ESG data remains current without manual intervention.

## Success Metrics
- **Stale Detection Recall**: 100% for data > 24 months old
- **MCP Trigger Accuracy**: > 90% when quality < 0.7
- **Re-ingestion Throughput**: > 5 companies/day
- **False Trigger Rate**: < 5%
- **Monitoring Overhead**: < 1% CPU utilization

## Critical Path Components
- `agents/ops/mcp_ops.py` - MCP Ops Agent with tool registration
- `agents/ops/timegate.py` - Iceberg snapshot-based staleness detection
- `agents/ops/quality_monitor.py` - Quality-triggered MCP fetch
- `agents/ops/coverage.py` - Data coverage reporting
- `integrations/mcp_fetcher.py` - Integration with mcp_report_fetcher.py

## Input/Output Specifications
**Inputs:**
- Iceberg snapshot metadata (timestamps, record counts)
- Quality metrics from QA Agent
- Coverage requirements per org/theme

**Outputs:**
- Staleness reports with org_id lists
- MCP fetch triggers when quality < threshold
- Coverage gap analysis

## Verification Strategy
- Test staleness detection with synthetic old snapshots
- Validate MCP triggering with known low-quality data
- Benchmark re-ingestion throughput
