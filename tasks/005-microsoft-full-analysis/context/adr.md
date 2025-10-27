# Architecture Decision Records - Task 005

**Task ID:** 005-microsoft-full-analysis
**Date:** 2025-10-22

---

## ADR-001: Use Manual Extraction Over Automated PDF Parsing

**Status:** Accepted
**Date:** 2025-10-22

**Context:** Need to extract 50-100 findings from Microsoft 2023 PDF report. Two options: (1) manual extraction, (2) automated PDF parsing.

**Decision:** Use manual extraction for first iteration.

**Rationale:**
- Higher accuracy (≥95% vs 70-80% for automated)
- Better theme/framework identification (requires domain knowledge)
- Automated parsing prone to OCR errors, table formatting issues
- Manual extraction allows quality control at extraction time

**Consequences:**
- More time-intensive (estimated 2-3 hours for 50-100 findings)
- Not scalable to 100+ companies
- Future: Build automated pipeline once validated on manual baseline

---

## ADR-002: Use Maximum Aggregation as Primary Method

**Status:** Accepted
**Date:** 2025-10-22

**Context:** Three aggregation methods available: maximum, average, 75th percentile.

**Decision:** Use **maximum** as primary/recommended method for company-level maturity.

**Rationale:**
- Aligns with "best evidence" principle in ESG rating
- Company maturity should reflect highest demonstrated capability, not average
- Expected to align best with MSCI AAA / CDP A- external ratings
- Supported by academic literature on maturity assessment

**Consequences:**
- Sensitive to outliers (single high score can dominate)
- May over-estimate if high-stage finding is anomalous
- Mitigation: Report all 3 methods; document variance

---

## ADR-003: No Changes to Scorer Code (Task 004 Validated)

**Status:** Accepted
**Date:** 2025-10-22

**Context:** Task 004 achieved 95.7% rubric compliance. Option to make further refinements.

**Decision:** No changes to `rubric_v3_scorer.py` in Task 005.

**Rationale:**
- Task 004 scorer is production-ready (95.7% exact match, 100% determinism)
- Task 005 is a validation task, not a refinement task
- Changing scorer would invalidate Task 004 validation artifacts
- If under-prediction persists, document as limitation (not bug)

**Consequences:**
- If company maturity still under-predicts (< 3.0), cannot fix via scorer changes
- Document as expected limitation of analyzing 50-100 findings vs full 100+ page report
- Future Task 006 could address remaining edge cases if needed

---

## ADR-004: Target 50-100 Findings (Not Full Corpus)

**Status:** Accepted
**Date:** 2025-10-22

**Context:** Microsoft report likely contains 100+ ESG-relevant statements. How many to extract?

**Decision:** Target 50-100 findings (strategic sample, not exhaustive extraction).

**Rationale:**
- Balances coverage vs effort (50-100 provides sufficient dimension representation)
- Diminishing returns beyond 100 findings (redundancy increases)
- Sufficient to validate Task 004 refinements and test aggregation methods
- If under-prediction persists at 100 findings, unlikely to resolve with 200+

**Consequences:**
- May still under-predict vs MSCI AAA / CDP A- (limited coverage)
- Document as expected limitation
- Future: Full corpus extraction (200+ findings) if business case warrants

---

## ADR-005: Cross-Validate with MSCI and CDP Only

**Status:** Accepted
**Date:** 2025-10-22

**Context:** Multiple external ESG ratings exist (MSCI, CDP, Sustainalytics, S&P Global, etc.).

**Decision:** Cross-validate with MSCI AAA and CDP A- only.

**Rationale:**
- Microsoft's known ratings (publicly disclosed)
- Sufficient to assess alignment (two independent ratings)
- Adding more ratings doesn't add validation value (redundancy)
- MSCI (comprehensive ESG) and CDP (climate focus) provide complementary perspectives

**Consequences:**
- Cannot validate against other rating agencies
- Sufficient for Task 005 objectives (validate scorer, assess aggregation)

---

**End of ADRs**
