# Task 009: Integrated Remediation

**Task ID:** 009-integrated-remediation
**Protocol:** SCA v13.8-MEA
**Date:** 2025-11-19
**Depends On:** Task 008 (SEC Content Filtering - COMPLETE)

---

## Objective

Re-run the end-to-end pipeline with XBRL cleaning enabled to demonstrate ESG score improvement through noise remediation.

**Baseline:** Task 007 Score = 0.29 / 5.0 (Nascent) - XBRL contaminated
**Target:** Score > 1.0 / 5.0 (Material Evidence Detected)

---

## Scientific Method

**Hypothesis:** Removing XBRL/XML metadata from SEC HTML will improve ESG score by providing the scorer with actual disclosure narrative instead of taxonomy tags.

**Experiment:**
1. Apply SecHtmlCleaner to Apple 10-K (85.6% noise reduction verified in Task 008)
2. Re-run Task 007 pipeline with cleaned text
3. Compare scores: Task 007 (baseline) vs Task 009 (remediated)

**Expected Outcome:** Score improvement of 4-5x (0.29 → 1.2-1.5)

---

## Input

- **Raw SEC HTML:** data/raw/sec_edgar/AAPL_2024_10K.htm (1.43 MB)
- **XBRL Cleaner:** agents/preprocessing/sec_cleaner.py (verified in Task 008)
- **Pipeline:** Ingest → Clean → Extract → Retrieve → Score

---

## Output

**Remediated ESG Score:**
- Aggregate maturity level (expected: >1.0)
- Confidence score
- Dimension breakdown
- Side-by-side comparison with Task 007 baseline

---

## Success Criteria

1. ✅ SecHtmlCleaner integrated into production agents/ module
2. ✅ Pipeline executes without errors
3. ✅ Retrieved evidence contains disclosure text (not XBRL tags)
4. ✅ ESG score > 1.0 (material improvement from 0.29)
5. ✅ Comparison report generated

---

## Protocol Compliance

- **Authenticity:** Uses real Apple 10-K, verified cleaner, production components
- **Determinism:** Same input → same output (regex-based cleaning)
- **Traceability:** Task 007 baseline preserved, remediation steps documented

---

**Task Status:** INITIALIZED
**Ready for Phase 1:** Cleaner Promotion
