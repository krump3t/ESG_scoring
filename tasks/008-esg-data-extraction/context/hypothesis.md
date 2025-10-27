# Task 008: ESG Maturity Evidence Extraction - Hypothesis
## ESG Prospecting Engine | SCA v13.8-MEA

**Task ID:** 008-esg-data-extraction
**Date:** 2025-10-22
**Protocol:** SCA v13.8-MEA
**Dependencies:** Task 007 (25 SEC filings downloaded)
**Alignment:** ESG Maturity Rubric v3.0 (7 themes)

---

## Primary Hypothesis

**Structured evidence for ESG maturity assessment can be extracted from SEC 10-K/20-F filings with ≥72% success rate (≥18/25 reports) across the 7 ESG Maturity Rubric themes, enabling automated stage scoring (0-4).**

### Specific Claims

1. **Theme Coverage per Report:**
   - **Claim:** ≥6/7 themes will have extractable evidence per report
   - **Threshold:** ≥4/7 themes minimum
   - **Rationale:** SEC filings emphasize governance and GHG more than operational details

2. **Extraction Success Rate:**
   - **Claim:** ≥18/25 reports (72%) will yield multi-theme evidence
   - **Threshold:** ≥15/25 reports (60%) minimum
   - **Rationale:** Some companies provide minimal ESG disclosure in 10-Ks

3. **Evidence Items per Report:**
   - **Claim:** ≥10 evidence spans per successfully extracted report
   - **Threshold:** ≥7 evidence spans minimum
   - **Evidence Span:** 30-word text excerpt + page number + confidence score

4. **Extraction Accuracy:**
   - **Claim:** ≥85% precision on manually validated spot-checks (5 reports)
   - **Threshold:** ≥75% precision minimum
   - **Validation:** Human review of stage assignments and evidence relevance

5. **Processing Time:**
   - **Claim:** <45 seconds per report (P95)
   - **Threshold:** <90 seconds per report
   - **Rationale:** Enables batch processing of large document sets

---

## ESG Maturity Rubric Alignment

This task extracts evidence for all **7 themes** from the ESG Maturity Rubric v3.0:

### Theme 1: Target Setting & Planning (TSP)
**Evidence to Extract:**
- Climate/ESG targets (quantitative, time-bound)
- Baseline year identification
- Target scope (Scope 1/2/3, operations vs. value chain)
- SBTi submission status / validation
- Science-based methodology references
- Supplier engagement in targets
- Financial integration (CAPEX/OPEX linkage)

**Stage Indicators:**
- Stage 0: No targets or generic CSR statements
- Stage 1: Short-term qualitative targets
- Stage 2: Time-bound quantitative targets + baseline
- Stage 3: SBTi pending + scenario modeling
- Stage 4: SBTi validated + financial integration

**Example Keywords:** "SBTi", "science-based target", "net-zero by 2050", "baseline year", "Scope 1/2/3 target", "supplier engagement"

---

### Theme 2: Operational Structure & Processes (OSP)
**Evidence to Extract:**
- ESG governance structure (committee, board oversight)
- Named ESG roles (Chief Sustainability Officer, VP ESG, etc.)
- Process documentation references
- Cross-functional collaboration
- Internal audit / assurance programs
- KPI tracking and accountability

**Stage Indicators:**
- Stage 0: No ESG governance
- Stage 1: Ad-hoc initiatives, isolated ownership
- Stage 2: Formalized processes, roles, policies
- Stage 3: Cross-functional collaboration + KPIs
- Stage 4: Embedded ESG management system + audit

**Example Keywords:** "Chief Sustainability Officer", "ESG committee", "Board oversight", "sustainability governance", "internal audit", "ESG KPIs"

---

### Theme 3: Data Maturity (DM)
**Evidence to Extract:**
- Data collection methodology (manual vs. automated)
- System architecture (databases, platforms, ETL)
- Data validation / QA protocols
- Centralized vs. distributed systems
- Supplier data exchange
- Real-time monitoring capabilities

**Stage Indicators:**
- Stage 0: Manual, inconsistent data entry
- Stage 1: Structured but manual collection
- Stage 2: Partially automated + QA protocols
- Stage 3: Centralized database + supplier integration
- Stage 4: Automated pipelines + real-time validation

**Example Keywords:** "automated data collection", "centralized platform", "data validation", "ETL", "supplier data", "real-time monitoring"

---

### Theme 4: GHG Accounting (GHG)
**Evidence to Extract:**
- Scope 1/2/3 emissions (values + units: tCO2e, mtCO2e)
- Accounting methodology (GHG Protocol, ISO 14064)
- Assurance level (limited, reasonable, none)
- Assurance provider (Deloitte, EY, etc.)
- Base year and recalculation policy
- Uncertainty / materiality thresholds
- Supplier engagement in Scope 3

**Stage Indicators:**
- Stage 0: No emissions accounting
- Stage 1: Partial Scope 1/2 estimates without methodology
- Stage 2: Scope 1/2 complete + partial Scope 3
- Stage 3: Comprehensive Scope 1/2/3 + limited assurance
- Stage 4: Reasonable assurance + GHG Protocol compliance

**Example Keywords:** "Scope 1", "Scope 2", "Scope 3", "tCO2e", "GHG Protocol", "limited assurance", "reasonable assurance", "Deloitte", "EY", "base year"

---

### Theme 5: Reporting & Disclosure (RD)
**Evidence to Extract:**
- Framework alignment (GRI, TCFD, ISSB, SASB, CSRD, ESRS)
- GRI index references
- TCFD alignment statements
- External assurance provider
- Assurance scope (limited vs. reasonable)
- Reporting frequency (annual, quarterly)
- Digital tagging (XBRL/ESRS) mentions
- Integrated reporting

**Stage Indicators:**
- Stage 0: No formal ESG reporting
- Stage 1: CSR/GRI index partial coverage
- Stage 2: ISSB/TCFD-aligned narrative
- Stage 3: Cross-framework alignment + dual materiality
- Stage 4: External assurance + digital tagging

**Example Keywords:** "GRI", "TCFD", "ISSB", "SASB", "CSRD", "ESRS", "external assurance", "XBRL", "sustainability report", "integrated report"

---

### Theme 6: Energy Intelligence (EI)
**Evidence to Extract:**
- Energy consumption (total, by source: electricity, gas, etc.)
- Renewable energy percentage / capacity
- Energy monitoring systems (EMS, IoT, SCADA)
- Energy efficiency projects
- Predictive maintenance programs
- AI/ML forecasting capabilities
- Cost-benefit analysis of energy projects

**Stage Indicators:**
- Stage 0: No tracking beyond invoices
- Stage 1: Basic metering + periodic reviews
- Stage 2: Systematic KPIs + improvement projects
- Stage 3: Automated monitoring + predictive maintenance
- Stage 4: AI/ML forecasting + optimization

**Example Keywords:** "renewable energy", "EMS", "energy management system", "energy efficiency", "predictive maintenance", "AI forecasting", "kWh", "MWh"

---

### Theme 7: Risk Management & Mitigation (RMM)
**Evidence to Extract:**
- Climate risk taxonomy (physical, transition)
- Physical risks (floods, wildfires, sea-level rise)
- Transition risks (policy, technology, market, reputation)
- Risk assessment methodology
- Scenario analysis (1.5°C, 2°C, 4°C pathways)
- Financial impact quantification
- Mitigation strategies
- Insurance / hedging strategies

**Stage Indicators:**
- Stage 0: No risk framework
- Stage 1: Qualitative risk statements
- Stage 2: Risk taxonomy + periodic assessments
- Stage 3: Quantified risks + scenario testing
- Stage 4: Enterprise risk integration + financial modeling

**Example Keywords:** "climate risk", "physical risk", "transition risk", "scenario analysis", "TCFD risk", "1.5°C", "2°C", "financial impact", "risk mitigation"

---

## Critical Path Definitions

### Critical Path (CP) Code

**What Constitutes CP for Task 008:**
- Theme-specific pattern matchers (7 modules, one per theme)
- Evidence extraction engine (confidence scoring, span extraction)
- Stage assignment logic (evidence → maturity score 0-4)
- Quality validation framework

**NOT Critical Path:**
- UI/visualization (future task)
- ML-based extraction (Phase 2 enhancement, rule-based sufficient for v1)
- Real-time processing (batch processing sufficient for PoC)

### CP File Patterns

```json
{
  "critical_path_patterns": [
    "agents/parser/evidence_extractor.py",
    "agents/parser/matchers/tsp_matcher.py",
    "agents/parser/matchers/osp_matcher.py",
    "agents/parser/matchers/dm_matcher.py",
    "agents/parser/matchers/ghg_matcher.py",
    "agents/parser/matchers/rd_matcher.py",
    "agents/parser/matchers/ei_matcher.py",
    "agents/parser/matchers/rmm_matcher.py",
    "agents/parser/stage_classifier.py",
    "tests/parser/test_evidence_extractor.py",
    "tests/parser/matchers/test_*_matcher.py"
  ],
  "entry_points": [
    "agents/parser/evidence_extractor.py:extract_evidence_from_filing"
  ]
}
```

---

## Evidence Output Schema

Based on ESG Maturity Rubric requirements (line 116-122):

```json
{
  "evidence_id": "uuid-v4",
  "org_id": "CIK or company identifier",
  "year": 2025,
  "theme": "TSP | OSP | DM | GHG | RD | EI | RMM",
  "stage_indicator": 0-4,
  "doc_id": "10-K_2025_AAPL",
  "page_no": 12,
  "span_start": 1523,
  "span_end": 1643,
  "extract_30w": "30-word window around match",
  "hash_sha256": "content hash for deduplication",
  "confidence": 0.92,
  "evidence_type": "SBTi_submission | assurance_letter | risk_matrix | etc.",
  "snapshot_id": "extraction run identifier"
}
```

---

## Exclusions

The following are **OUT OF SCOPE** for Task 008 (not in ESG Maturity Rubric):

- ❌ Water usage metrics
- ❌ Waste/recycling metrics
- ❌ Employee diversity/DEI metrics
- ❌ Safety incident rates (TRIR, DART)
- ❌ Board composition details
- ❌ Supply chain labor practices
- ❌ Community investment amounts

**Rationale:** ESG Maturity Rubric v3.0 focuses on climate/sustainability maturity, not broad ESG. Social and detailed governance metrics are not part of the 7 themes.

---

## Success Metrics

| Metric | Target | Threshold |
|--------|--------|-----------|
| Theme Coverage | ≥6/7 themes per report | ≥4/7 themes |
| Extraction Rate | ≥18/25 reports (72%) | ≥15/25 (60%) |
| Evidence Items | ≥10 spans per report | ≥7 spans |
| Extraction Accuracy | ≥85% precision | ≥75% |
| Processing Time P95 | <45s per report | <90s |
| False Positive Rate | ≤15% | ≤25% |

---

## Risks & Mitigations

### Risk 1: Low Theme Coverage in SEC Filings
**Risk:** SEC 10-Ks may not contain detailed evidence for all 7 themes (especially DM, EI)
**Mitigation:**
- Adjust threshold to 4/7 themes
- Document which themes are commonly missing
- Recommend dedicated sustainability reports for Task 009

### Risk 2: False Positives in Pattern Matching
**Risk:** Keywords like "risk" are common, may trigger false matches
**Mitigation:**
- Require contextual validation (e.g., "climate risk" not just "risk")
- Implement confidence scoring (0.0-1.0)
- Manual validation of 5 reports to measure precision

### Risk 3: Stage Assignment Ambiguity
**Risk:** Evidence may not clearly map to stage 0-4
**Mitigation:**
- Use conservative scoring (lower stage if ambiguous)
- Document stage assignment rationale
- Build explainability layer (show evidence → stage logic)

---

## Baseline Data

**From Task 007:**
- 25 SEC filings successfully downloaded (10-K, 20-F formats)
- Companies: 15 US, 4 Europe (with SEC filings), 6 Asia-Pacific (with SEC filings)
- File format: HTML (SEC EDGAR)
- Avg. file size: ~500 KB - 2 MB
- Avg. page count: ~100-200 pages per filing

---

## Next Phase Dependencies

**Task 008 Output enables:**
- **Task 009:** Automated Maturity Scoring (aggregate evidence → 0-4 scores per theme)
- **Task 010:** MCP-Iceberg Integration (store evidence in gold.esg_evidence table)
- **Task 011:** Explainability Agent (rank top-10 evidence excerpts by relevance)

---

**Version:** 2.0 (Revised for ESG Maturity Rubric v3.0 alignment)
**Status:** Hypothesis ready for validation
**Approval:** Pending user confirmation
