# Hypothesis: QA and Explainability Agents

## Core Hypothesis
Adding QA/Assurance and Explainability agents will enable automated quality checks and transparent "why" explanations for ESG scores.

## Success Metrics
- QA gate pass rate: > 90%
- Drift detection: < 10% false positives
- Evidence retrieval: < 500ms per query
- Explanation completeness: > 95% of scores explainable

## Critical Path
- agents/qa/mcp_qa.py
- agents/explainability/mcp_explain.py
- views/report_card.sql
