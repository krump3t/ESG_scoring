# Assumptions - Task 005: Full Microsoft 2023 Report Analysis

**Task ID:** 005-microsoft-full-analysis
**Date:** 2025-10-22

---

## Data Assumptions

### A1: Microsoft 2023 Report Contains 50-100 Extractable Findings
**Assumption:** Microsoft's 2023 Environmental Sustainability Report contains at least 50 substantive ESG disclosures suitable for scoring.

**Justification:** Typical corporate ESG reports (80-120 pages) contain 100+ distinct statements about policies, practices, metrics, and commitments. Microsoft is a leading ESG discloser (MSCI AAA / CDP A-).

**Risk if Wrong:** If report contains <50 findings, reduce target to 30-40 (minimum viable coverage).

**Validation:** Count findings during extraction; if <50, document and adjust expectations.

---

### A2: Manual Extraction Achieves ≥95% Accuracy
**Assumption:** Manually extracted findings (text, theme, framework, page) are ≥95% accurate.

**Justification:** Manual review by domain-aware human reduces OCR errors, formatting issues, and context loss vs automated parsing.

**Risk if Wrong:** Scoring errors propagate from extraction errors.

**Validation:** Manual review of 10% sample; correct errors before scoring.

---

## Scoring Assumptions

### A3: Task 004 Scorer is Production-Ready
**Assumption:** Task 004 refined scorer (95.7% rubric compliance, 100% determinism) is suitable for production use without further changes.

**Justification:** Task 004 achieved +21.8 percentage point improvement (73.9% → 95.7%), 0 violations, 100% determinism.

**Risk if Wrong:** Under-prediction may persist.

**Validation:** If company maturity <3.0, document as limitation (not bug); no scorer changes in Task 005.

---

### A4: Determinism Maintained on Full Dataset
**Assumption:** Scorer maintains 100% determinism when applied to 50-100 findings (vs 2,447 differential test cases in Task 004).

**Justification:** Scorer has no randomness, no external API calls, no time-based logic; determinism validated in Task 004.

**Risk if Wrong:** Violates authenticity invariant.

**Validation:** Re-score 10 random findings 3 times; assert 100% identical results.

---

## Aggregation Assumptions

### A5: Maximum Aggregation Best Represents Company Maturity
**Assumption:** Taking the maximum score per dimension (across all findings) best represents company-level maturity.

**Justification:** Company maturity reflects **highest demonstrated capability**, not average performance. Aligns with ESG rating agency methodologies (MSCI, Sustainalytics).

**Risk if Wrong:** May over-estimate if single high-stage finding is anomalous.

**Validation:** Compare all 3 methods (max, avg, p75); document which aligns best with MSCI AAA / CDP A-.

---

### A6: Dimension Variance is Expected
**Assumption:** Different dimensions (TSP, OSP, DM, GHG, RD, EI, RMM) will score differently based on Microsoft's ESG priorities.

**Justification:** Microsoft is climate-focused (GHG, RD likely high) but may have less emphasis on operational tech (OSP) or advanced disclosure maturity (DM).

**Risk if Wrong:** If all dimensions score identically, may indicate scorer is not discriminating.

**Validation:** Calculate variance (σ); expect σ > 0.5 for ≥3 dimensions.

---

## External Rating Assumptions

### A7: MSCI AAA Maps to 3.5-4.0 on 0-4 Scale
**Assumption:** MSCI AAA rating (top ESG performer) corresponds to 3.5-4.0 (Advanced-Leading tier) in our rubric.

**Justification:** MSCI AAA represents "leader in managing industry-specific ESG risks" (top 2-5% of rated companies). Aligns with "Leading" tier in academic maturity models.

**Risk if Wrong:** Misaligned expectations; may under-predict or over-predict.

**Validation:** Check alignment; if |predicted - 3.5| ≤ 0.5, consider aligned.

---

### A8: CDP A- Maps to 3.0-3.5 on 0-4 Scale
**Assumption:** CDP A- score (strong climate action) corresponds to 3.0-3.5 (Established-Advanced tier).

**Justification:** CDP A/A- represents "comprehensive climate action and transparency" (top quartile). Aligns with "Established-Advanced" tier.

**Risk if Wrong:** Misaligned expectations.

**Validation:** Check alignment; if |predicted - 3.25| ≤ 0.5, consider aligned.

---

### A9: External Ratings Reflect Full Report, Not Excerpts
**Assumption:** MSCI AAA / CDP A- ratings are based on Microsoft's complete ESG disclosures (100+ page report + additional data requests), not limited excerpts.

**Justification:** Rating agencies have access to full reports + direct company data submissions.

**Risk if Wrong:** Our 50-100 finding analysis may under-predict due to limited coverage.

**Validation:** If under-prediction persists, document as expected limitation (not scorer bug).

---

## Validation Assumptions

### A10: 50-100 Findings Provide Sufficient Coverage
**Assumption:** Analyzing 50-100 findings (vs 8 in Task 003/004) provides sufficient coverage to produce company-level scores aligned with external ratings.

**Justification:** 50-100 findings represent 50-100% of typical ESG report content; should capture key maturity indicators across all 7 dimensions.

**Risk if Wrong:** May still under-predict if critical high-stage findings are missed.

**Validation:** Check dimension coverage (≥3 findings per dimension); if under-prediction persists, document and recommend full corpus analysis (Task 006).

---

### A11: Alignment Within ±0.5 is Acceptable
**Assumption:** Company maturity score within ±0.5 of external rating expected score is considered "aligned."

**Justification:** External ratings are ordinal/categorical (AAA, A-, B, etc.), not continuous scores. ±0.5 tolerance accounts for rating methodology differences.

**Risk if Wrong:** Too lenient; may miss systematic bias.

**Validation:** If |predicted - expected| > 0.5, investigate for systematic bias or scorer issues.

---

## Process Assumptions

### A12: Manual Extraction is Feasible for 50-100 Findings
**Assumption:** Manually extracting 50-100 findings from PDF is feasible within reasonable time (2-3 hours).

**Justification:** ~1-2 minutes per finding (read, extract text, identify theme/framework, record).

**Risk if Wrong:** Too time-intensive; may need automated parsing.

**Validation:** Track extraction time; if >4 hours, switch to automated parsing with manual review.

---

**Assumptions Complete: 12 assumptions documented**
