# Design - Task 005: Full Microsoft 2023 Report Analysis

**Task ID:** 005-microsoft-full-analysis
**Date:** 2025-10-22
**Protocol:** SCA v13.8-MEA

---

## Overview

Task 005 analyzes Microsoft's complete 2023 Environmental Sustainability Report (50-100 findings vs previous 8 excerpts) to validate that the Task 004 refined scorer produces company-level maturity scores aligned with external ratings (MSCI AAA / CDP A-).

**Approach:** Data extraction → Scoring → Aggregation → Cross-validation → Reporting

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TASK 005 WORKFLOW                            │
└─────────────────────────────────────────────────────────────────┘

1. PDF EXTRACTION
   ├── Input: Microsoft 2023 ESG Report (PDF)
   ├── Method: Manual extraction or automated PDF parsing
   ├── Output: 50-100 findings (text, theme, framework, page, section)
   └── Validation: Manual review of 10% sample

2. SCORING (Task 004 Refined Scorer)
   ├── Input: Full findings dataset
   ├── Method: rubric_v3_scorer.score_all_dimensions()
   ├── Output: Scored findings (7 dimensions per finding)
   └── Validation: Determinism check (10 findings × 3 re-scores)

3. AGGREGATION
   ├── Input: Scored findings
   ├── Methods: Maximum, Average, 75th Percentile
   ├── Output: Company-level maturity (overall + per-dimension)
   └── Validation: Method comparison, variance check

4. CROSS-VALIDATION
   ├── Input: Company maturity + external ratings
   ├── Method: Absolute difference vs expected scores
   ├── Output: Alignment assessment (MSCI, CDP)
   └── Validation: |predicted - expected| ≤ 0.5

5. REPORTING
   ├── Input: All above results
   ├── Output: Comprehensive analysis report
   └── Validation: Task 004 refinement validation
```

---

## Data Extraction Strategy

### Source Document

**Primary Source:**
- Microsoft 2023 Environmental Sustainability Report
- URL: https://www.microsoft.com/en-us/sustainability
- Cached: `data/pdf_cache/ed9a89cf9feb626c5bb8429f8dddfba6.pdf` (if available)
- Expected Length: 80-120 pages
- Expected Findings: 50-100 ESG disclosures

### Extraction Method

**Option A: Manual Extraction** (Recommended for accuracy)
1. Read PDF page by page
2. Identify ESG disclosures (substantive statements about practices, policies, metrics)
3. Extract text, identify theme, framework, page, section
4. Record in JSON format matching existing schema

**Option B: Automated PDF Parsing** (Fallback if time-constrained)
1. Use PDF parsing library (PyPDF2, pdfplumber)
2. Extract all text blocks
3. Filter for ESG-relevant sections (regex patterns)
4. Manually review and correct errors

**Quality Gates:**
- ✅ Each finding ≥50 characters (substantive, not headings)
- ✅ Theme assigned (Climate, Operations, Governance, Energy, Risk, Water, Waste, Social)
- ✅ Framework identified if mentioned (TCFD, GRI, SASB, SBTi, GHG Protocol, CDP, RE100, etc.)
- ✅ Page number accurate
- ✅ Section name descriptive

### Target Distribution

| Dimension | Target Findings | Rationale |
|-----------|----------------|-----------|
| **TSP** (Tech & Sustainability Programs) | ≥5 | IoT, AI, predictive systems |
| **OSP** (Operational Sustainability) | ≥3 | Real-time monitoring, automation |
| **DM** (Disclosure Maturity) | ≥3 | SASB, integrated reporting |
| **GHG** (GHG Accounting) | ≥10 | Microsoft's climate focus |
| **RD** (Reporting & Disclosure) | ≥10 | TCFD, CDP, SBTi disclosures |
| **EI** (ESG Integration) | ≥5 | Executive comp, board oversight |
| **RMM** (Risk Management) | ≥5 | Climate scenario analysis, ERM |
| **Total** | ≥50 | Minimum viable coverage |

---

## Scoring Strategy

### Scorer Configuration

**Scorer:** `agents.scoring.rubric_v3_scorer.RubricV3Scorer` (Task 004 refined version)
- Rubric Compliance: 95.7% exact match
- Determinism: 100% (validated across 2,447 cases)
- Refinements: RD Stage 0, GHG assurance, RMM implicit, RD framework

**No Changes:** Scorer code is unchanged; this task validates scorer on full dataset.

### Scoring Process

```python
scorer = RubricV3Scorer()

for finding in full_findings:
    # Score all 7 dimensions
    scores = scorer.score_all_dimensions(finding)

    # Extract dimension scores
    dimension_scores = {dim: score.score for dim, score in scores.items()}

    # Store with metadata
    scored_finding = {
        "finding_id": finding["finding_id"],
        "finding_text": finding["finding_text"],
        "theme": finding["theme"],
        "framework": finding["framework"],
        "page": finding["page"],
        "section": finding["section"],
        "scores": dimension_scores,
        "evidence": {dim: score.evidence for dim, score in scores.items()},
        "confidence": {dim: score.confidence for dim, score in scores.items()}
    }
```

### Determinism Validation

**Protocol:**
1. Randomly select 10 findings
2. Re-score each finding 3 times
3. Assert 100% identical results (score, evidence, confidence)
4. If any variance detected → BLOCK and investigate

---

## Aggregation Strategy

### Method 1: Maximum (Best Evidence) - RECOMMENDED

**Rationale:** Company maturity should reflect **highest demonstrated capability** per dimension. A company with one Stage 4 finding and five Stage 0 findings in a dimension has **demonstrated** Stage 4 capability.

```python
max_scores = {
    dim: max(scores_for_dim) if scores_for_dim else 0
    for dim, scores_for_dim in dimension_aggregates.items()
}

overall_max = sum(max_scores.values()) / 7
```

**Pros:**
- Aligns with "best evidence" principle in ESG rating
- Reflects true capability (not penalized by sparse disclosures)
- Expected to best align with external ratings

**Cons:**
- Sensitive to outliers (single high score can dominate)
- May over-estimate if Stage 4 finding is anomalous

### Method 2: Average

**Rationale:** Central tendency across all findings.

```python
avg_scores = {
    dim: sum(scores_for_dim) / len(scores_for_dim) if scores_for_dim else 0
    for dim, scores_for_dim in dimension_aggregates.items()
}

overall_avg = sum(avg_scores.values()) / 7
```

**Pros:**
- Robust to outliers
- Reflects consistency of disclosures

**Cons:**
- Penalizes companies for sparse disclosures in some dimensions
- May under-estimate if high-stage findings are rare but valid

### Method 3: 75th Percentile

**Rationale:** Robust to outliers while capturing high-end performance.

```python
def percentile_75(scores_list):
    if not scores_list:
        return 0
    sorted_scores = sorted(scores_list)
    idx = int(len(sorted_scores) * 0.75)
    return sorted_scores[idx]

p75_scores = {
    dim: percentile_75(scores_for_dim)
    for dim, scores_for_dim in dimension_aggregates.items()
}

overall_p75 = sum(p75_scores.values()) / 7
```

**Pros:**
- Balanced between max and average
- Less sensitive to single anomalous high score

**Cons:**
- Requires ≥4 findings per dimension for meaningful percentile

### Method Comparison

**Hypothesis:** Maximum will align best with MSCI AAA / CDP A- (external ratings focus on demonstrated capability, not average performance).

**Validation:** Calculate all 3 methods; report alignment with external ratings for each.

---

## Cross-Validation Strategy

### External Ratings Mapping

| Rating | Expected Score (0-4) | Maturity Label | Rationale |
|--------|---------------------|----------------|-----------|
| **MSCI AAA** | 3.5-4.0 | Advanced-Leading | Top ESG performer |
| **CDP A-** | 3.0-3.5 | Established-Advanced | Strong climate action |
| **MSCI AA** | 3.0-3.5 | Established-Advanced | Above average |
| **CDP B** | 2.0-3.0 | Emerging-Established | Moderate performance |

**Microsoft 2023:**
- MSCI Rating: AAA
- CDP Climate: A-
- **Expected Score:** 3.0-3.5 (Established-Advanced range)

### Alignment Assessment

**Criteria:**
- ✅ **ALIGNED:** |predicted - expected| ≤ 0.5
- ⚠️ **PARTIAL:** 0.5 < |predicted - expected| ≤ 1.0
- ❌ **DIVERGENT:** |predicted - expected| > 1.0

**Dimension-Level Validation:**
- **GHG:** Expected ≥3.0 (Microsoft's climate leadership)
- **RD:** Expected ≥3.0 (Strong TCFD, CDP disclosure)
- **RMM:** Expected ≥2.0 (Climate scenario analysis)
- **EI:** Expected ≥3.0 (Board oversight, exec comp tied to ESG)

### Validation Outcomes

**Success (Aligned):**
- Predicted score: 3.0-3.5/4.0
- |predicted - MSCI_expected| ≤ 0.5
- |predicted - CDP_expected| ≤ 0.5
- Dimension-level scores align with Microsoft's known strengths

**Partial (Under-Prediction):**
- Predicted score: 2.5-3.0/4.0
- Likely due to incomplete coverage (50-100 findings vs full 100+ page report)
- Document as expected limitation

**Failure (Divergent):**
- Predicted score: <2.5 or >3.5/4.0
- Investigate for scorer bugs or data extraction errors
- May indicate Task 004 refinements need further adjustment

---

## Data Schema

### Full Findings Dataset (`microsoft_2023_full_findings.json`)

```json
[
  {
    "finding_id": "msft_2023_001",
    "finding_text": "Full text of ESG disclosure (≥50 chars)",
    "theme": "Climate | Operations | Governance | Energy | Risk | Water | Waste | Social",
    "framework": "TCFD | GRI | SASB | SBTi | GHG Protocol | CDP | RE100 | Internal | null",
    "page": 12,
    "section": "Carbon Negative Commitment"
  },
  ...
]
```

### Scored Findings (`microsoft_2023_scored_findings.json`)

```json
[
  {
    "finding_id": "msft_2023_001",
    "finding_text": "...",
    "theme": "Climate",
    "framework": "SBTi",
    "page": 12,
    "section": "Carbon Negative Commitment",
    "scores": {
      "TSP": 4,
      "OSP": 0,
      "DM": 0,
      "GHG": 4,
      "RD": 2,
      "EI": 0,
      "RMM": 0
    },
    "evidence": {
      "TSP": "Evidence text...",
      "GHG": "Evidence text...",
      ...
    },
    "confidence": {
      "TSP": 0.90,
      "GHG": 0.95,
      ...
    }
  },
  ...
]
```

### Company Maturity (`microsoft_2023_company_maturity.json`)

```json
{
  "company": "Microsoft",
  "year": 2023,
  "report_type": "Environmental Sustainability Report",
  "findings_analyzed": 75,
  "aggregation_methods": {
    "maximum": {
      "overall": 3.14,
      "label": "Established",
      "dimensions": {
        "TSP": 4,
        "OSP": 0,
        "DM": 1,
        "GHG": 4,
        "RD": 3,
        "EI": 3,
        "RMM": 4
      }
    },
    "average": {...},
    "percentile_75": {...}
  },
  "recommended_score": 3.14,
  "recommended_label": "Established",
  "cross_validation": {
    "msci": {"rating": "AAA", "expected": 3.5, "diff": 0.36, "alignment": "ALIGNED"},
    "cdp": {"score": "A-", "expected": 3.25, "diff": 0.11, "alignment": "ALIGNED"}
  },
  "timestamp": "2025-10-22T12:00:00Z"
}
```

---

## Success Criteria

### Data Extraction

- ✅ 50-100 findings extracted
- ✅ All 7 dimensions represented (≥3 findings each)
- ✅ Manual review of 10% sample shows ≥95% accuracy

### Scoring

- ✅ All findings scored successfully (no crashes)
- ✅ Determinism: 100% identical re-scores (10 findings × 3 iterations)

### Aggregation

- ✅ Company maturity: 3.0-3.5/4.0 (Established-Advanced)
- ✅ MSCI alignment: |predicted - 3.5| ≤ 0.5
- ✅ CDP alignment: |predicted - 3.25| ≤ 0.5

### Validation

- ✅ Maximum method aligns best with external ratings
- ✅ Dimension variance: σ > 0.5 for ≥3 dimensions
- ✅ Stage distribution follows maturity curve

---

## Design Complete
