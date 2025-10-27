# Hypothesis - Rubric v3.0 Implementation

**Task ID:** 003-rubric-v3-implementation
**Date:** 2025-10-22
**Status:** Implementation Complete, Validation In Progress

---

## Primary Hypothesis

**H1:** Implementing the authentic 7-dimensional rubric v3.0 scoring algorithm will produce ESG maturity assessments that align with external ratings (MSCI, CDP, DJSI) within ±1 maturity stage.

**Null Hypothesis (H0):** The 7-dimensional rubric scores will not correlate with external ESG ratings.

---

## Metrics & Thresholds

### Success Metrics

1. **Dimension Score Validity:**
   - Each of 7 dimensions (TSP, OSP, DM, GHG, RD, EI, RMM) scores 0-4
   - Overall maturity = average of 7 dimensions (0.0-4.0)
   - Maturity label matches rubric v3.0 mapping (Nascent/Emerging/Established/Advanced/Leading)

2. **External Validation:**
   - Microsoft overall maturity: Expected 3.0-4.0 (Advanced-Leading) to match MSCI AAA, CDP A-
   - Correlation with external ratings: Pearson r >= 0.7

3. **Evidence Detection:**
   - TSP Stage 4 detection for SBTi validated targets: >= 95% accuracy
   - GHG Stage 2 detection for Scope 1/2/3 coverage: >= 90% accuracy
   - Framework boost (TCFD, SBTi, ISSB): >= 90% detection rate

### Performance Thresholds

- **Scoring Latency:** < 500ms per finding
- **Memory Usage:** < 100MB for rubric scorer instance
- **Throughput:** >= 100 findings/second

---

## Input/Output Specification

### Input

```json
{
  "finding_text": "string (sustainability report excerpt)",
  "theme": "Climate | Environmental | Social | Governance",
  "framework": "SBTi | TCFD | GRI | SASB | ISSB | ..."
}
```

### Output (7-Dimensional)

```json
{
  "tsp_score": 0-4,
  "tsp_evidence": "string",
  "tsp_confidence": 0.0-1.0,
  "osp_score": 0-4,
  ...  // 5 more dimensions
  "overall_maturity": 0.0-4.0,
  "maturity_label": "Nascent|Emerging|Established|Advanced|Leading"
}
```

---

## Critical Path (CP)

### CP Files (per cp_paths.json)

1. `agents/scoring/rubric_v3_scorer.py` - Core 7-dimensional scorer
2. `agents/scoring/mcp_scoring.py` - MCP agent integration
3. `iceberg/tables/gold_schema.py` - 7-dimensional schema
4. `agents/normalizer/mcp_normalizer.py` - Finding extraction
5. `iceberg/tables/silver_schema.py` - Normalized findings schema

### CP Coverage Requirements

- **Line Coverage:** >= 95%
- **Branch Coverage:** >= 95%
- **Mutation Score:** >= 80% (if mutation testing enabled)

---

## Exclusions

### Out of Scope

- LLM-based scoring (future enhancement)
- Real-time report ingestion (bronze layer handles this)
- Multi-language report processing (English only for v1)
- Historical trend analysis (future phase)

### Non-CP Files

- MCP server infrastructure (`mcp_server/`)
- Test scripts (`scripts/`)
- Documentation files (`*.md` except context files)

---

## Power & Confidence Intervals

### Statistical Power

- **Sample Size:** 3 companies (Microsoft, Shell, ExxonMobil) for initial validation
- **Target Power:** 0.80 (80% chance to detect true effect)
- **Alpha Level:** 0.05 (5% false positive rate)

### Confidence Intervals

- **Overall Confidence:** Average of 7 dimension confidences
- **95% CI:** Calculated via Wilson score interval
- **Minimum Acceptable Confidence:** 0.60 (60%)

---

## Risk Counters & Mitigation

### R1: Evidence Pattern False Positives

**Risk:** Regex patterns match irrelevant text, inflating scores
**Mitigation:**
- Evidence extraction validates matched context
- Confidence calibration based on match strength
- Manual review of top 10% scores
**Counter:** Differential testing with perturbed text (sensitivity < 0.3)

### R2: Dimension Imbalance

**Risk:** Some dimensions consistently score 0 (no evidence in reports)
**Mitigation:**
- Aggregate scores across multiple findings per org
- Report missing dimensions explicitly
- Weight overall maturity by coverage (optional future)
**Counter:** Track dimension coverage rate (>= 4 of 7 dimensions per org)

### R3: External Rating Misalignment

**Risk:** Our scores don't match MSCI/CDP ratings
**Mitigation:**
- Cross-validate against 3+ external sources
- Document methodology differences
- Tune evidence patterns based on validation feedback
**Counter:** Correlation coefficient >= 0.7 with external ratings

### R4: Schema Evolution Complexity

**Risk:** Adding 28 fields to gold schema breaks existing queries
**Mitigation:**
- All previous test results invalidated (documented)
- Migration plan for any existing gold data
- Backward compatibility not required (v3.0 is breaking change)
**Counter:** Zero production deployments using old schema

---

## Test Strategy

### Unit Tests

- Each dimension scorer method (`score_tsp`, `score_osp`, etc.)
- Evidence pattern matching
- Overall maturity calculation
- Schema validation

### Property Tests (Hypothesis)

- Monotonicity: More evidence → higher or equal score
- Consistency: Same input → same output (determinism)
- Bounds: All scores in valid range (0-4 per dimension, 0.0-4.0 overall)

### Failure-Path Tests (NEW - SCA v13.8 requirement)

- Invalid finding input → raises ValueError
- Missing required fields → raises KeyError
- Out-of-range scores → raises AssertionError
- Schema validation failure → returns False with logged error

### Integration Tests

- End-to-end: Bronze → Silver → Gold with rubric v3.0
- Real data: Microsoft, Shell, ExxonMobil sustainability reports
- Cross-validation: Compare to MSCI AAA, CDP A-, DJSI ratings

---

## Acceptance Criteria

### Must Have (Blocking)

1. ✅ All 7 dimensions implemented per rubric v3.0
2. ✅ Gold schema updated with 28 new fields
3. ✅ MCP scoring agent uses rubric v3.0 scorer
4. ✅ Test suite validates 7-dimensional output
5. ⏳ Failure-path tests for all CP files
6. ⏳ External validation: Microsoft score within ±1 stage of MSCI AAA

### Should Have (Important)

7. ⏳ Differential testing executed (>= 1,200 cases)
8. ⏳ State persistence (state.json, memory_sync.json)
9. ⏳ REPRODUCIBILITY.md documenting determinism
10. ⏳ Task directory structure compliance

### Nice to Have (Future)

11. LLM-based scoring option
12. Dimension-specific explainability
13. Historical trend tracking
14. Multi-language support

---

## Version

- **Rubric Version:** v3.0
- **Schema Version:** Gold v2.0 (7-dimensional)
- **Scorer Version:** v3.0
- **Protocol Version:** SCA v13.8
