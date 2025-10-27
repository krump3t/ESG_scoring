# ESG Maturity Rubric v3.0 Migration

**Date**: 2025-10-21
**Status**: COMPLETE
**Impact**: Updated scoring pipeline to use evidence-based rubric with 7 standardized themes

---

## Summary

Migrated the ESG scoring system from custom theme-based rubrics to the standardized **ESG Maturity Rubric v3.0**. This rubric provides:

- **7 standardized themes** with evidence-based stage descriptors (0-4)
- **Framework detection** and automatic stage boosts (SBTi, ISSB/TCFD, GHG Protocol, CSRD/ESRS)
- **Freshness penalties** for evidence older than 24 months
- **Evidence requirements** (minimum 2 pieces per stage claim)
- **Confidence guidance** (weak/adequate/strong labels)

---

## Rubric v3.0 Themes

| Code | Theme Name                       | Intent                                                  |
|------|----------------------------------|---------------------------------------------------------|
| TSP  | Target Setting & Planning        | Evaluate ambition, structure, and credibility of targets |
| OSP  | Operational Structure & Processes | Evaluate ESG integration within operations and governance |
| DM   | Data Maturity                    | Assess data quality, automation, and system architecture |
| GHG  | GHG Accounting                   | Evaluate completeness, accuracy, and assurance of emissions data |
| RD   | Reporting & Disclosure           | Measure transparency, alignment, and timeliness of ESG reporting |
| EI   | Energy Intelligence              | Evaluate monitoring, optimization, and forecasting of energy/resources |
| RMM  | Risk Management & Mitigation     | Evaluate climate/ESG risk identification and mitigation integration |

---

## Changes Made

### 1. New Rubric Loader (`apps/scoring/rubric_v3_loader.py`)

Created a comprehensive loader class that:

- Loads `rubrics/esg_rubric_schema_v3.json`
- Provides theme access by code or name
- Generates LLM-friendly rubric text
- Applies framework boosts automatically
- Applies freshness penalties
- Validates evidence requirements

**Key Methods**:
```python
rubric_loader = get_rubric_v3()
rubric_loader.get_theme_names()  # ["Target Setting & Planning", ...]
rubric_loader.get_rubric_for_llm("TSP")  # {0: "No targets: ...", 1: "Foundational: ..."}
rubric_loader.apply_framework_boost("TSP", base_stage=2, ["SBTi"])  # Returns 3 or 4
rubric_loader.apply_freshness_penalty(confidence=0.8, evidence_age_months=30)  # Returns 0.7
```

### 2. Updated Scoring Pipeline (`apps/scoring/pipeline.py`)

**Modified Methods**:

- `_load_themes()`: Now loads themes from rubric v3.0 instead of hardcoded list
- `_load_rubric()`: Dynamically generates rubric from v3.0 schema
- `_score_theme()`: Enhanced with:
  - Framework detection (SBTi, ISSB/TCFD, GHG Protocol, CSRD/ESRS)
  - Automatic stage boosts based on detected frameworks
  - Freshness penalty calculation
  - Confidence label assignment (weak/adequate/strong)

**Added Methods**:

- `_get_theme_code(theme_name)`: Map theme name to code
- `_calculate_evidence_age(year)`: Calculate evidence age in months

**New Score Metadata**:

Theme scores now include:
```python
{
    "stage": 3,  # Final adjusted stage
    "confidence": 0.75,  # Adjusted confidence with freshness penalty
    "confidence_label": "adequate",
    "evidence_count": 12,
    "reasoning": "...",
    "key_findings": [...],
    "retrieval_count": 20,
    "detected_frameworks": ["SBTi", "ISSB_TCFD"],  # NEW
    "base_stage": 2,  # Stage before framework boost
    "base_confidence": 0.8,  # Confidence before freshness penalty
    "evidence_age_months": 24  # NEW
}
```

### 3. Framework Boost Rules

Per rubric v3.0 `scoring_rules.framework_signals`:

| Framework | Theme | Effect |
|-----------|-------|--------|
| SBTi (approved) | TSP | Sets stage to 4 |
| SBTi (pending) | TSP | Minimum stage 3 |
| ISSB/TCFD (assured + tagged) | RD | Sets stage to 4 |
| ISSB/TCFD (aligned) | RD | Minimum stage 2 |
| GHG Protocol (reasonable assurance) | GHG | Sets stage to 4 |
| GHG Protocol (compliant) | GHG | Minimum stage 3 |
| CSRD/ESRS | RD | Supports stages 3-4 |

**Detection Logic** (in `_score_theme`):
```python
if "sbti" in text_lower or "science-based target" in text_lower:
    detected_frameworks.append("SBTi")
if "issb" in text_lower or "tcfd" in text_lower:
    detected_frameworks.append("ISSB_TCFD")
if "ghg protocol" in text_lower:
    detected_frameworks.append("GHG_Protocol")
if "csrd" in text_lower or "esrs" in text_lower:
    detected_frameworks.append("CSRD_ESRS")
```

### 4. Freshness Penalty

Per rubric v3.0 `scoring_rules.freshness_months_penalty`:

- **Threshold**: 24 months
- **Penalty**: -0.1 confidence

**Example**:
- Evidence from 2023 report (24 months old): confidence 0.8 → 0.7
- Evidence from 2022 report (36 months old): confidence 0.8 → 0.7
- Evidence from 2024 report (12 months old): confidence 0.8 (no penalty)

### 5. Evidence Requirements

Per rubric v3.0 `scoring_rules.evidence_min_per_stage_claim`:

- **Minimum**: 2 evidence items per stage claim
- **Validation**: `rubric_loader.validate_evidence_count(count)`
- **Warning**: Pipeline logs warning if evidence count < 2

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `apps/scoring/rubric_v3_loader.py` | NEW - Complete rubric loader | 247 |
| `apps/scoring/pipeline.py` | Updated to use rubric v3.0 | ~50 lines modified |

---

## Files Not Modified (Reference Only)

| File | Status | Reason |
|------|--------|--------|
| `rubrics/esg_maturity_rubricv3.md` | Reference | Human-readable markdown version |
| `rubrics/esg_rubric_schema_v3.json` | Reference | Machine-readable schema (loaded by rubric_v3_loader) |
| `apps/scoring/scorer.py` | Stub | Main logic in pipeline.py |
| `rubrics/compile_rubric.py` | Legacy | For older v1.0 rubrics |

---

## Testing Recommendations

1. **Unit Tests**: Test rubric_v3_loader.py methods
   ```python
   def test_rubric_loader_themes():
       rubric = get_rubric_v3()
       assert len(rubric.get_theme_codes()) == 7
       assert "TSP" in rubric.get_theme_codes()

   def test_framework_boost():
       rubric = get_rubric_v3()
       boosted = rubric.apply_framework_boost("TSP", 2, ["SBTi"])
       assert boosted >= 3

   def test_freshness_penalty():
       rubric = get_rubric_v3()
       penalized = rubric.apply_freshness_penalty(0.8, 30)
       assert penalized < 0.8
   ```

2. **Integration Tests**: Score a sample company and verify:
   - All 7 themes are scored
   - Framework detection works (look for companies with SBTi targets)
   - Freshness penalties applied for old reports
   - Confidence labels assigned correctly

3. **Regression Tests**: Compare scores before/after migration
   - Document any significant stage changes
   - Verify changes align with framework boosts or freshness penalties

---

## Migration Benefits

| Benefit | Impact |
|---------|--------|
| **Standardization** | All 7 themes now use consistent rubric language |
| **Framework Recognition** | Automatic credit for SBTi, ISSB, GHG Protocol compliance |
| **Evidence Quality** | Freshness penalties encourage recent data |
| **Transparency** | Base vs. adjusted scores show impact of boosts/penalties |
| **Confidence Calibration** | Weak/adequate/strong labels provide clearer guidance |

---

## Overall Maturity Grade (Unchanged)

| Average Score | Maturity Level |
|---------------|----------------|
| 0-0.9         | Nascent        |
| 1.0-1.9       | Emerging       |
| 2.0-2.9       | Established    |
| 3.0-3.5       | Advanced       |
| 3.6-4.0       | Leading        |

---

## Next Steps

1. Test rubric v3.0 loader with sample data
2. Run scoring pipeline on 3-5 companies to verify framework detection
3. Update any reporting/visualization to display:
   - Detected frameworks
   - Base vs. adjusted scores
   - Confidence labels
   - Evidence age
4. Update API response schema to include new metadata
5. Document any scoring changes in migration report

---

**Migration Status**: ✓ COMPLETE
**Version**: v3.0
**Effective Date**: 2025-10-21
