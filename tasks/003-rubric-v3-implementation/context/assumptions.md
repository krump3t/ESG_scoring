# Assumptions - Rubric v3.0 Implementation

**Task ID:** 003-rubric-v3-implementation
**Date:** 2025-10-22

---

## Technical Assumptions

### A1: English-Only Reports

**Assumption:** All sustainability reports are in English.

**Rationale:**
- Microsoft, Shell, ExxonMobil publish English versions
- Regex patterns designed for English keywords
- No i18n/l10n requirements for v1

**Risk:** Non-English reports will score poorly or fail to parse.

**Validation:** Test suite uses English reports exclusively.

**Mitigation:** Document language limitation; future enhancement for multi-language.

---

### A2: Text-Based Scoring Sufficient

**Assumption:** Text excerpts contain enough evidence for maturity scoring.

**Rationale:**
- Sustainability reports are primarily text (not just tables/charts)
- SBTi validation, TCFD alignment, Scope 1/2/3 coverage all mentioned in text
- Rubric v3.0 evidence criteria based on textual descriptions

**Risk:** Important evidence in charts/tables may be missed.

**Validation:** Manual review of top 10% scores for completeness.

**Mitigation:** Future enhancement: table/chart extraction from PDFs.

---

### A3: Recent Reports More Relevant

**Assumption:** Sustainability reports older than 24 months have reduced relevance.

**Rationale:**
- ESG practices evolve rapidly (SBTi targets, net-zero commitments)
- Freshness affects confidence calibration (older = lower confidence)
- Most companies publish annually

**Risk:** Historical trend analysis requires older data.

**Validation:** Freshness warning logged for reports > 24 months old.

**Mitigation:** Confidence penalty for stale data; explicit date tracking.

---

### A4: Single Finding Per Report Excerpt

**Assumption:** Each bronze document contains one logical finding.

**Rationale:**
- Normalizer extracts discrete findings from paragraphs
- Findings scored independently
- Aggregation happens at org level, not finding level

**Risk:** Complex multi-topic paragraphs may be under-scored.

**Validation:** Normalizer creates multiple findings from complex text.

**Mitigation:** Deduplication logic handles overlapping findings.

---

## Data Assumptions

### A5: No PII in Sustainability Reports

**Assumption:** Public sustainability reports contain no personally identifiable information.

**Rationale:**
- Reports are public corporate disclosures
- Focus on organizational metrics, not individuals
- GDPR/CCPA not applicable to aggregated org data

**Risk:** Rare mentions of named executives.

**Validation:** No PII detected in test data (Microsoft, Shell, ExxonMobil).

**Mitigation:** `pii_flag: false` in data_sources.json.

---

### A6: SHA256 Hashes Provide Sufficient Integrity

**Assumption:** SHA256 hashing prevents data tampering and ensures reproducibility.

**Rationale:**
- Cryptographically secure hash function
- Detects any byte-level changes to source data
- Industry standard for data integrity

**Risk:** Hash collisions (negligible probability).

**Validation:** Hashes recorded at bronze ingestion, verified before scoring.

**Mitigation:** Re-hash on read; log mismatches as critical errors.

---

### A7: Bronze Layer Data is Immutable

**Assumption:** Once ingested, bronze data never changes.

**Rationale:**
- Iceberg snapshot IDs track versions
- Source reports are point-in-time snapshots
- No updates to historical data

**Risk:** Report corrections/errata.

**Validation:** New ingestion creates new bronze record, doesn't overwrite.

**Mitigation:** Version tracking via snapshot IDs and ingestion timestamps.

---

## Scoring Assumptions

### A8: Pattern Matching Captures Key Evidence

**Assumption:** Regex patterns accurately detect rubric stage evidence.

**Rationale:**
- Patterns based on actual sustainability report language
- Tested against Microsoft, Shell, ExxonMobil real text
- Evidence extraction validates matched context

**Risk:** Synonym variations, unusual phrasings missed.

**Validation:** Differential testing with varied phrasings; sensitivity analysis.

**Mitigation:** Pattern tuning based on false negative analysis; future LLM enhancement.

---

### A9: All 7 Dimensions Equally Important

**Assumption:** Overall maturity is simple average of 7 dimension scores (no weighting).

**Rationale:**
- Rubric v3.0 doesn't specify dimension weights
- Transparency and simplicity prioritized
- Domain experts can apply custom weights post-hoc

**Risk:** Some dimensions (e.g., GHG) may be more material for certain sectors.

**Validation:** Correlation with external ratings validates unweighted approach.

**Mitigation:** Documented in ADR-003; can add weighting option if needed.

---

### A10: Stage Criteria Are Mutually Exclusive

**Assumption:** A finding cannot simultaneously match multiple stages within same dimension.

**Rationale:**
- Stages are progressive (stage 4 implies stages 1-3)
- Matching order (4→3→2→1) ensures highest stage wins
- Rubric defines clear stage boundaries

**Risk:** Ambiguous findings with mixed evidence.

**Validation:** Top-down matching order prevents multi-stage matches.

**Mitigation:** Evidence snippets show exact match for transparency.

---

## External Validation Assumptions

### A11: MSCI AAA Maps to Overall 3.6-4.0

**Assumption:** MSCI's AAA rating (leader) corresponds to our "Leading" maturity level (3.6-4.0).

**Rationale:**
- AAA is top tier (7 levels: AAA, AA, A, BBB, BB, B, CCC)
- Our "Leading" is top tier (5 levels: Nascent, Emerging, Established, Advanced, Leading)
- Qualitative alignment based on methodology review

**Risk:** Different methodologies may not align perfectly.

**Validation:** Cross-check against CDP A- score; expect consistency.

**Mitigation:** Document methodology differences; use correlation, not exact mapping.

---

### A12: CDP A- Maps to Overall 3.0-3.5

**Assumption:** CDP's A- (leadership) corresponds to our "Advanced" maturity level (3.0-3.5).

**Rationale:**
- A- is high tier (8 levels: A, A-, B, B-, C, C-, D, D-)
- Our "Advanced" is second-highest tier
- Microsoft A- likely reflects strong but not perfect performance

**Risk:** CDP focuses heavily on GHG/RD dimensions, not all 7.

**Validation:** Check dimension breakdown; expect high GHG/RD, moderate others.

**Mitigation:** Dimension-level comparison more informative than overall.

---

## Process Assumptions

### A13: Determinism Achievable Without Random Ops

**Assumption:** Rule-based scoring with fixed regex patterns is fully deterministic.

**Rationale:**
- No random number generation
- No LLM sampling (temperature=0 would still vary)
- Regex matching is deterministic by nature

**Risk:** None identified.

**Validation:** Consistency tests (10 iterations, same input → same output).

**Mitigation:** None needed; inherent property of rule-based approach.

---

### A14: Test Suite Represents Production Workload

**Assumption:** Microsoft, Shell, ExxonMobil reports are representative of typical corporate sustainability reports.

**Rationale:**
- Large-cap companies with mature ESG programs
- Diverse sectors (tech, energy, oil/gas)
- TCFD/GRI/SASB/SBTi framework adoption common

**Risk:** Small-cap or emerging market companies may differ.

**Validation:** Expand test set to include mid-cap and international companies.

**Mitigation:** Document test data scope; iterate on broader dataset.

---

### A15: Failure-Path Tests Prevent Production Errors

**Assumption:** Testing exception handling prevents runtime failures in production.

**Rationale:**
- SCA v13.8 mandates failure-path tests for all CP files
- Exception tests validate error conditions (invalid input, missing fields, etc.)
- Defensive coding reduces production risk

**Risk:** Unanticipated edge cases.

**Validation:** Code coverage includes exception paths; failure tests exist for each CP function.

**Mitigation:** Continuous monitoring; add tests for production errors.

---

**Total Assumptions:** 15
**Last Reviewed:** 2025-10-22
**Next Review:** Before external deployment
