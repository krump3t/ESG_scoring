# LLM-Powered Narrative Report Generation - Implementation Guide

## Overview

This document describes the implementation of authentic LLM-powered ESG narrative report generation using watsonx.ai models, completing the end-to-end pipeline: **PDF Ingestion → Embeddings → Semantic Retrieval → Scoring → LLM Narrative Generation**.

## Implementation Status: ✅ CODE COMPLETE

All code components have been implemented and are ready for execution when watsonx.ai credentials are available.

## Architecture

### Components Created

1. **`libs/narrative/watsonx_narrator.py`** (220 LOC)
   - Main LLM orchestration class
   - Integrates with existing `WatsonxClient` from `libs/wx/wx_client.py`
   - Deterministic generation (temperature=0.0)
   - Full caching support via wx_cache infrastructure

2. **`scripts/generate_llm_reports.py`** (270 LOC)
   - CLI interface for LLM report generation
   - Two-phase execution: FETCH (online) → REPLAY (offline)
   - Processes all documents in artifacts/matrix/
   - Fail-closed validation (cache miss → error)

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Model: Llama-3-70B** | Higher quality reasoning, existing usage in edit_text() |
| **Temperature: 0.0** | Deterministic outputs, cache-friendly |
| **Two-Phase Architecture** | FETCH proves authenticity, REPLAY proves determinism |
| **Evidence Grounding** | All narratives reference specific pages/hashes |
| **Fail-Closed Replay** | RuntimeError on cache miss ensures no silent mocks |

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: FETCH (Online, populates cache)                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  artifacts/matrix/{doc_id}/                                 │
│  └── baseline/run_1/scoring_response.json                   │
│      │                                                       │
│      ├─> Extract: theme_scores, evidence_records            │
│      │                                                       │
│      └─> WatsonxNarrator.generate_full_report()            │
│          │                                                   │
│          ├─> generate_executive_summary()                   │
│          │   └─> wx_client.edit_text() [API CALL]          │
│          │       └─> Cache: wx_cache/edits/{hash}.json      │
│          │                                                   │
│          └─> generate_theme_analysis() × 7 themes           │
│              └─> wx_client.edit_text() [API CALL]           │
│                  └─> Cache: wx_cache/edits/{hash}.json      │
│                                                              │
│  Output: artifacts/reports/{doc_id}_llm_report.md           │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 2: REPLAY (Offline, cache-only)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Same code path as FETCH, but:                              │
│  - WX_OFFLINE_REPLAY=true forces cache-only mode            │
│  - Cache miss → RuntimeError (fail-closed)                  │
│  - Zero API calls, zero cost                                │
│  - Validates determinism: same prompts → same outputs        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Prompt Templates

### Executive Summary Prompt
```
You are an ESG analyst writing an executive summary...

COMPANY: {company} ({year})
OVERALL MATURITY: Average Stage {avg}

THEME SCORES:
- TSP: Stage 3 (confidence: 0.85)
- OSP: Stage 2 (confidence: 0.72)
...

INSTRUCTIONS:
1. Write 2-3 paragraphs (150-200 words)
2. Paragraph 1: Overall positioning
3. Paragraph 2: Top 3 strengths (Stage 3+)
4. Paragraph 3: Key gaps (Stage ≤1)
5. Evidence-based, concise language
6. DO NOT fabricate metrics
```

### Theme Analysis Prompt
```
You are an ESG analyst writing assessment for: {theme_name}

SCORE: Stage {stage} (confidence: {conf})
STAGE DESCRIPTOR: {descriptor}

EVIDENCE:
- Page 12: "quote..." (hash: f6bd2406)
- Page 45: "quote..." (hash: 88e9c41c)

INSTRUCTIONS:
1. Write 3-4 sentences explaining WHY Stage {stage}
2. Reference specific pages
3. Explain rubric alignment
4. If conf < 0.7, acknowledge limitations
5. DO NOT fabricate evidence
```

## Execution Instructions

### Prerequisites

1. **Watsonx.ai Credentials** (required for FETCH phase):
   ```bash
   export WX_API_KEY="your-ibm-cloud-api-key"
   export WX_PROJECT="your-watsonx-project-id"
   ```

2. **Completed Scoring Pipeline** (required):
   - Artifacts in `artifacts/matrix/{doc_id}/baseline/run_1/scoring_response.json`
   - Must contain: `theme_scores` array and `evidence_records` array
   - Currently BLOCKED: demo_flow import failed, scoring_response has empty scores

3. **Rubric File** (optional but recommended):
   - Path: `rubrics/maturity_v3.json`
   - Provides stage descriptors for richer LLM context

### Step 1: Fix Scoring Pipeline (PREREQUISITE)

**Current Issue**: The scoring responses are empty because `demo_flow` import failed during the offline replay. To use LLM narrative generation, you must first:

1. Fix the demo_flow import issue (venv problem identified earlier)
2. Re-run the scoring pipeline with proper imports
3. Ensure `scoring_response.json` contains actual theme_scores and evidence

**Command to verify scoring data**:
```bash
cd "C:/projects/Work Projects/ibm-projects/ESG Evaluation/prospecting-engine"
cat artifacts/matrix/msft_2023/baseline/run_1/scoring_response.json | jq '.scores | length'
# Should output > 0, not 0
```

### Step 2: FETCH Phase (Populate LLM Cache)

**When scoring pipeline is fixed and credentials are available**:

```bash
cd "C:/projects/Work Projects/ibm-projects/ESG Evaluation/prospecting-engine"

# Set environment
export WX_API_KEY="your-api-key"
export WX_PROJECT="your-project-id"
export SEED=42
export PYTHONHASHSEED=0

# Run FETCH
python scripts/generate_llm_reports.py \
  --base-dir artifacts/matrix \
  --offline-replay false \
  --rubric rubrics/maturity_v3.json
```

**Expected Output**:
```
LLM Report Generation (offline_replay=False)
======================================================================

Processing: apple_2023
  Company: Apple Inc.
  Themes: 7
  Evidence: 14
  Generating LLM narratives...
  ✓ Report generated: artifacts/reports/apple_2023_llm_report.md

Processing: exxonmobil_2023
  Company: ExxonMobil Corporation
  Themes: 7
  Evidence: 12
  Generating LLM narratives...
  ✓ Report generated: artifacts/reports/exxonmobil_2023_llm_report.md

...

======================================================================
Reports generated: 4/4
Output directory: artifacts/reports/

Status: SUCCESS
```

**Artifacts Created**:
- `artifacts/reports/*_llm_report.md` - LLM-generated markdown reports
- `artifacts/wx_cache/edits/*.json` - Cached LLM responses
- Updated `artifacts/wx_cache/ledger.jsonl` - Audit log with costs/timestamps

### Step 3: REPLAY Phase (Determinism Validation)

```bash
# Clear previous reports
rm artifacts/reports/*_llm_report.md

# Run REPLAY (cache-only, zero API calls)
export WX_OFFLINE_REPLAY=true
python scripts/generate_llm_reports.py \
  --base-dir artifacts/matrix \
  --offline-replay true \
  --rubric rubrics/maturity_v3.json
```

**Expected Output**:
```
LLM Report Generation (offline_replay=True)
======================================================================

Processing: apple_2023
  Company: Apple Inc.
  Themes: 7
  Evidence: 14
  Generating LLM narratives... [using cache]
  ✓ Report generated: artifacts/reports/apple_2023_llm_report.md

...

======================================================================
Reports generated: 4/4
Output directory: artifacts/reports/

Status: SUCCESS
```

**Key Validation**: 100% cache hit ratio (check ledger for zero online calls during replay)

### Step 4: Determinism Check (Run Replay ×3)

```bash
# Generate 3 times in replay mode
for i in 1 2 3; do
  rm artifacts/reports/*_llm_report.md
  python scripts/generate_llm_reports.py \
    --base-dir artifacts/matrix \
    --offline-replay true \
    --rubric rubrics/maturity_v3.json

  mkdir -p artifacts/llm_determinism/run_$i
  cp artifacts/reports/*_llm_report.md artifacts/llm_determinism/run_$i/
done

# SHA256 comparison
sha256sum artifacts/llm_determinism/run_1/*.md > artifacts/llm_determinism/hashes_1.txt
sha256sum artifacts/llm_determinism/run_2/*.md > artifacts/llm_determinism/hashes_2.txt
sha256sum artifacts/llm_determinism/run_3/*.md > artifacts/llm_determinism/hashes_3.txt

# Verify identical
diff artifacts/llm_determinism/hashes_1.txt artifacts/llm_determinism/hashes_2.txt
diff artifacts/llm_determinism/hashes_2.txt artifacts/llm_determinism/hashes_3.txt

# Expected output: (no differences)
```

**Success Criteria**: All 3 runs produce identical SHA256 hashes → Full determinism achieved

## Sample LLM Report Structure

```markdown
======================================================================
ESG MATURITY ASSESSMENT: Apple Inc. (2023)
======================================================================

**Document ID**: `apple_2023`
**Generated**: 2025-10-29T06:00:00Z
**Model**: meta-llama/llama-3-70b-instruct (temperature=0.0)

## Executive Summary

[LLM-generated 2-3 paragraphs]
Apple Inc. demonstrates an average ESG maturity of Stage 2.8, indicating
strong foundational practices with room for strategic advancement. The
organization excels in Target Setting & Planning (Stage 3), showcasing
ambitious net-zero commitments with interim 2030 targets...

## Theme-by-Theme Analysis

### TSP - Target Setting & Planning
**Maturity Stage**: 3 (confidence: 0.85)

[LLM-generated narrative]
Apple's Stage 3 maturity in Target Setting is evidenced by their
comprehensive 2030 carbon neutrality roadmap detailed on Page 12.
The commitment spans Scope 1, 2, and 3 emissions with measurable
interim milestones, aligning with the rubric's requirement for
"quantitative, time-bound targets across all material scopes"...

**Evidence Provenance**:
- Page 12: "By 2030, Apple will be carbon neutral across..." (hash: `f6bd2406...`)
- Page 45: "Scope 3 emissions reduction of 75% by 2030..." (hash: `88e9c41c...`)

[Repeat for all 7 themes: TSP, OSP, DM, GHG, RD, EI, RMM]

## Validation Gates

- **Determinism**: PASS
- **Parity**: PASS
- **Evidence Quality**: 14/14 themes with ≥2 quotes from ≥2 pages

---
*Generated with Watsonx.ai LLM (meta-llama/llama-3-70b-instruct) | SCA v13.8-MEA*
```

## Caching Mechanics

### Cache Key Generation
```python
def _build_cache_key(params, prompt, content):
    combined = json.dumps({
        "model_id": params["model_id"],
        "temperature": params["temperature"],
        "prompt": prompt,
        "content": content
    }, sort_keys=True)
    return hashlib.sha256(combined.encode()).hexdigest()
```

### Cache File Structure
```json
{
  "model_id": "meta-llama/llama-3-70b-instruct",
  "params": {
    "temperature": 0.0,
    "max_new_tokens": 512
  },
  "input_sha": "a1b2c3...",
  "output": "Apple Inc. demonstrates an average ESG maturity...",
  "output_sha": "d4e5f6...",
  "time_utc": "2025-10-29T06:15:00.123456+00:00",
  "doc_id": "apple_2023",
  "cost_estimate": 0.0023
}
```

### Ledger Entry
```jsonl
{"phase":"fetch","online":true,"cache_hit":false,"model":"llama-3-70b","doc_id":"apple_2023","timestamp":"2025-10-29T06:15:00Z","cost":0.0023}
{"phase":"replay","online":false,"cache_hit":true,"model":"llama-3-70b","doc_id":"apple_2023","timestamp":"2025-10-29T06:20:00Z","cost":0.0}
```

## Integration Testing

### Test 1: Import Check
```bash
cd "C:/projects/Work Projects/ibm-projects/ESG Evaluation/prospecting-engine"
python -c "from libs.narrative.watsonx_narrator import WatsonxNarrator; print('✓ Import successful')"
```

### Test 2: Narrator Initialization
```python
from libs.narrative.watsonx_narrator import WatsonxNarrator

# Offline mode (will fail on actual generation without cache)
narrator = WatsonxNarrator(offline_replay=True)
print(f"✓ Narrator initialized (offline_replay={narrator.offline_replay})")
```

### Test 3: Prompt Template Validation
```python
from libs.narrative.watsonx_narrator import WatsonxNarrator

narrator = WatsonxNarrator()
prompt = narrator.EXECUTIVE_SUMMARY_PROMPT.format(
    company_name="Test Corp",
    year=2023,
    overall_stage=2.5,
    theme_scores_text="- TSP: Stage 3\n- OSP: Stage 2"
)
print("✓ Prompt template valid")
print(f"Prompt length: {len(prompt)} chars")
```

## Troubleshooting

### Issue: "RuntimeError: Cache miss in offline replay mode"
**Cause**: Attempting REPLAY before FETCH, or prompt changed
**Solution**: Run FETCH phase first with credentials to populate cache

### Issue: "FileNotFoundError: scoring_response.json not found"
**Cause**: Scoring pipeline not completed
**Solution**: Run matrix pipeline first: `python scripts/run_matrix.py --config configs/companies_local.yaml`

### Issue: "ImportError: No module named 'libs.wx.wx_client'"
**Cause**: Python path issue
**Solution**: Ensure script runs from repo root with sys.path.insert(0, ...)

### Issue: Empty scores in scoring_response.json
**Cause**: demo_flow import failure during scoring (venv issue)
**Solution**: Fix venv activation, re-run scoring pipeline with proper environment

## Cost Estimation

**Per Document** (7 themes + 1 executive summary):
- 8 LLM calls × ~150 tokens average = ~1,200 tokens
- Cost (Llama-3-70B): ~$0.02-0.05 per document

**Full Matrix** (4 documents):
- 32 LLM calls
- Total cost: ~$0.08-0.20

**Replay Phase**: $0 (cache-only, no API calls)

## Success Criteria Checklist

- [x] Code implementation complete (WatsonxNarrator + generate_llm_reports.py)
- [x] Prompt templates with anti-hallucination instructions
- [x] Integration with existing WatsonxClient caching
- [x] Two-phase architecture (FETCH/REPLAY)
- [x] Fail-closed validation (cache miss → error)
- [ ] FETCH phase executed (requires credentials + fixed scoring)
- [ ] REPLAY phase validated (requires FETCH completion)
- [ ] Determinism proven (3× replay with identical hashes)
- [ ] Release pack updated with LLM reports

## Next Steps (Manual Execution Required)

1. **Fix Scoring Pipeline**: Resolve demo_flow import, re-run matrix scoring
2. **Obtain Credentials**: Set WX_API_KEY and WX_PROJECT environment variables
3. **Run FETCH**: Execute generate_llm_reports.py with --offline-replay false
4. **Run REPLAY ×3**: Validate determinism with cache-only execution
5. **Update Release Pack**: Copy LLM reports and update attestation

## References

- **WatsonX Client**: `libs/wx/wx_client.py`
- **Narrator Implementation**: `libs/narrative/watsonx_narrator.py`
- **Report Generator**: `scripts/generate_llm_reports.py`
- **Rubric**: `rubrics/maturity_v3.json`
- **Cache Directory**: `artifacts/wx_cache/`
- **Ledger**: `artifacts/wx_cache/ledger.jsonl`

---

**Status**: Implementation complete, awaiting credentials and fixed scoring pipeline for execution.

**Author**: SCA v13.8-MEA
**Date**: 2025-10-29
**Protocol**: Authentic computation, zero mocks, fail-closed validation
