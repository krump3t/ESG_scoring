# ESG Maturity Scoring System - Approved Implementation Plan

**Date**: 2025-10-23
**Protocol**: SCA v13.8-MEA
**Task ID**: 008-esg-data-extraction (Phase 3 Expansion)
**Status**: APPROVED - Ready for Execution

---

## Executive Summary

This plan implements a rubric-based ESG maturity scoring system with evidence-based assessment and IBM Envizi solution recommendations. The system supports two user personas (sellers and product managers) with three query types: single company scoring, multi-company comparison, and filtered ranking.

### Key Components
1. **Rubric-Based Scoring**: 7 ESG themes × 5 maturity stages (0-4)
2. **Evidence Tables**: Up to 10 prioritized evidence rows per theme
3. **Envizi Pitch Tables**: Solution recommendations mapped to gaps
4. **watsonx.ai Integration**: Embeddings for semantic matching + LLM for rationale generation
5. **Multi-Year Analysis**: Track maturity trends (2021-2023)

### Success Criteria
- Scoring accuracy >90% vs. gold set
- Semantic similarity ≥80% for qualitative answers
- All SCA v13.8 quality gates passing (coverage ≥95%, mypy clean, complexity ≤10)

---

## Architecture Alignment

### Data Model Updates

#### Silver Layer Enhancements (v2.0)
```sql
-- Characteristic matching fields
ALTER TABLE esg_evidence_normalized ADD COLUMN matched_characteristic VARCHAR;
ALTER TABLE esg_evidence_normalized ADD COLUMN matched_stage INTEGER;
ALTER TABLE esg_evidence_normalized ADD COLUMN match_confidence DOUBLE;

-- Priority ranking
ALTER TABLE esg_evidence_normalized ADD COLUMN priority_score INTEGER;

-- Business context
ALTER TABLE esg_evidence_normalized ADD COLUMN industry_sector VARCHAR;
ALTER TABLE esg_evidence_normalized ADD COLUMN sic_code VARCHAR;
ALTER TABLE esg_evidence_normalized ADD COLUMN revenue DOUBLE;
```

#### Gold Layer Enhancements (v2.0)
```sql
-- Rubric-compliant outputs
ALTER TABLE esg_maturity_scores ADD COLUMN evidence_table JSON;
ALTER TABLE esg_maturity_scores ADD COLUMN envizi_pitch_table JSON;
ALTER TABLE esg_maturity_scores ADD COLUMN shortcoming_summary JSON;
```

### Technology Stack
- **Python 3.11+**
- **watsonx.ai**: Embeddings (semantic matching) + LLM (rationale generation)
- **DuckDB + Parquet**: Structured storage and query layer
- **Docker**: Containerization for IBM Cloud Code Engine deployment
- **pytest + Hypothesis**: TDD testing framework

---

## Implementation Phases (11 Checkpoints)

### Phase Structure

Each phase follows the **Mandatory Execution Algorithm (MEA)**:
1. **Write tests first** (TDD guard)
2. **Write implementation**
3. **Run `validate-only.ps1`**
4. **If "ok"**: Run `snapshot-save.ps1` → CHECKPOINT REACHED
5. **If "blocked"**: Fix issues → retry (max 3 attempts)

---

### CP-1: Rubric Loader & Data Models ✅
**Duration**: 3 hours
**Status**: In Progress

#### Deliverables
- `rubrics/esg_rubric_v1.md` - Structured rubric (7 themes × 5 stages)
- `rubrics/esg_rubric_v1.json` - Cached structured format
- `agents/scoring/rubric_models.py` - Data classes (CP)
- `agents/scoring/rubric_loader.py` - Markdown parser (CP)
- `tests/scoring/test_rubric_models.py` - ≥10 tests
- `tests/scoring/test_rubric_loader.py` - ≥15 tests

#### Critical Path Files
- `agents/scoring/rubric_models.py`
- `agents/scoring/rubric_loader.py`

#### Data Models
```python
@dataclass
class StageCharacteristic:
    theme: str
    stage: int  # 0-4
    description: str
    keywords: List[str]

@dataclass
class ThemeRubric:
    theme_name: str
    theme_id: str
    stages: Dict[int, List[StageCharacteristic]]

@dataclass
class MaturityRubric:
    themes: Dict[str, ThemeRubric]
    version: str
```

#### Quality Gates
- ✅ ≥25 tests passing
- ✅ Coverage ≥95%
- ✅ `mypy --strict` clean
- ✅ ≥2 Hypothesis property tests
- ✅ ≥3 failure-path tests

---

### CP-2: Evidence Matcher + watsonx.ai Embeddings
**Duration**: 4 hours

#### Deliverables
- `agents/embedding/watsonx_embedder.py` - Embedding client (CP)
- `agents/scoring/characteristic_matcher.py` - Semantic matching (CP)
- `agents/scoring/evidence_table_generator.py` - Generate Evidence Table (CP)
- `tests/embedding/test_watsonx_embedder.py` - ≥8 tests
- `tests/scoring/test_characteristic_matcher.py` - ≥10 tests
- `tests/scoring/test_evidence_table_generator.py` - ≥8 tests

#### Critical Path Files
- `agents/embedding/watsonx_embedder.py`
- `agents/scoring/characteristic_matcher.py`
- `agents/scoring/evidence_table_generator.py`

#### Implementation Logic
```python
# watsonx_embedder.py
class WatsonxEmbedder:
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding via watsonx.ai API"""

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Batch embedding for efficiency"""

# characteristic_matcher.py
class CharacteristicMatcher:
    def match_evidence_to_characteristic(
        self,
        evidence_extract: str,
        theme: str,
        rubric: MaturityRubric
    ) -> Tuple[StageCharacteristic, float]:
        """Match evidence to best-fit characteristic via cosine similarity"""

# evidence_table_generator.py
@dataclass
class EvidenceRow:
    priority_score: int  # 1-10
    characteristic: str
    evidence_extract: str  # Max 30 words
    maturity_stage: int  # 0-4

def generate_evidence_table(...) -> List[EvidenceRow]:
    """Generate Evidence Table (up to 10 rows per theme)"""
```

#### Environment Requirements
```bash
# .env file
WATSONX_API_KEY=<api_key>
WATSONX_PROJECT_ID=<project_id>
WATSONX_ENDPOINT=https://us-south.ml.cloud.ibm.com
```

#### Quality Gates
- ✅ ≥26 tests passing
- ✅ Coverage ≥95%
- ✅ watsonx.ai integration tested (mocked for unit tests)
- ✅ Semantic matching accuracy >80% on test set

---

### CP-3: Scoring Engine
**Duration**: 3 hours

#### Deliverables
- `agents/scoring/scoring_engine.py` - Theme scoring logic (CP)
- `tests/scoring/test_scoring_engine.py` - ≥15 tests

#### Critical Path Files
- `agents/scoring/scoring_engine.py`

#### Scoring Algorithm
```python
@dataclass
class ThemeScore:
    theme: str
    stage: int  # 0-4
    evidence_table: List[EvidenceRow]
    confidence: float
    matched_characteristics: List[str]

class ScoringEngine:
    def score_theme(...) -> ThemeScore:
        """
        Score single theme (0-4).

        Algorithm:
        1. Match all evidence to characteristics
        2. Group by stage (0-4)
        3. Start at Stage 4, work down to Stage 0:
           - Count % of characteristics matched
           - If ≥60% matched → return that stage
        4. Generate evidence table from top 10 matches
        """
```

#### Quality Gates
- ✅ ≥15 tests passing
- ✅ Coverage ≥95%
- ✅ Test on 5 companies × 7 themes = 35 scoring tests

---

### CP-4: Envizi Knowledge Base
**Duration**: 2 hours

#### Deliverables
- `agents/envizi/solution_scraper.py` - Scrape 4 URLs (utility, non-CP)
- `agents/envizi/solution_mapper.py` - Map gaps to solutions (CP)
- `agents/envizi/envizi_knowledge_base.json` - Cached solution data
- `tests/envizi/test_solution_scraper.py` - ≥5 tests
- `tests/envizi/test_solution_mapper.py` - ≥10 tests

#### Critical Path Files
- `agents/envizi/solution_mapper.py`

#### Envizi URLs
1. https://www.ibm.com/products/envizi/target-setting-tracking
2. https://www.ibm.com/products/envizi/sustainability-program-tracking
3. https://www.ibm.com/products/envizi/sustainability-planning
4. https://www.ibm.com/products/envizi/supply-chain

#### Shortcoming Mapping
```python
SHORTCOMING_TO_SOLUTION = {
    "no_formal_targets": ["target-setting-tracking"],
    "no_scope_3_tracking": ["supply-chain"],
    "no_scenario_modeling": ["sustainability-planning"],
    "manual_data_collection": ["sustainability-program-tracking"],
    # ... comprehensive mapping
}
```

#### Quality Gates
- ✅ ≥15 tests passing
- ✅ Coverage ≥95%
- ✅ Mapping validated for 20+ shortcoming types

---

### CP-5: Pitch Generator
**Duration**: 3 hours

#### Deliverables
- `agents/envizi/pitch_generator.py` - Generate Envizi Pitch Table (CP)
- `tests/envizi/test_pitch_generator.py` - ≥12 tests

#### Critical Path Files
- `agents/envizi/pitch_generator.py`

#### Implementation Logic
```python
@dataclass
class PitchRow:
    row_number: int
    envizi_solution: str
    features: str
    rationale: List[str]  # Each 20-30 words

class PitchGenerator:
    def generate_pitch_table(...) -> List[PitchRow]:
        """
        Generate Envizi Pitch Table.

        Process:
        1. Identify missing characteristics (from stage+1)
        2. Map to Envizi solutions
        3. For each solution:
           - List relevant features
           - Generate 20-30 word rationales via watsonx.ai LLM
        """
```

#### Quality Gates
- ✅ ≥12 tests passing
- ✅ Coverage ≥95%
- ✅ Rationale length validation (20-30 words)

---

### CP-6: Query Type Expansion
**Duration**: 3 hours

#### Deliverables
- Update `agents/query/query_parser.py` - Add 4 new question types
- Update `tests/query/test_query_parser.py` - ≥15 new tests

#### New Question Types
```python
class QuestionType(Enum):
    # Existing...
    SCOPE_1_EMISSIONS = "scope_1_emissions"
    # ... others

    # NEW
    COMPANY_SCORING = "company_scoring"          # "What is Exxon's ESG rating?"
    THEME_SCORING = "theme_scoring"              # "Exxon's GHG score?"
    MULTI_COMPANY_COMPARISON = "multi_company_comparison"  # "Compare X, Y, Z"
    FILTERED_RANKING = "filtered_ranking"        # "List companies scoring <2 in..."
```

#### Query Patterns
- **Single Company**: "What is [company]'s ESG rating?"
- **Theme Specific**: "How does [company] score on [theme]?"
- **Comparison**: "Common shortcomings across [company A, B, C]?"
- **Filtered**: "List companies scoring <[X] in [theme] with [criteria]"

#### Quality Gates
- ✅ ≥15 tests passing
- ✅ Coverage ≥95%
- ✅ Pattern matching accuracy >90%

---

### CP-7: Answer Generator
**Duration**: 3 hours

#### Deliverables
- `agents/answer/answer_generator.py` - Format outputs (CP)
- `agents/answer/templates/` - Output templates
- `tests/answer/test_answer_generator.py` - ≥12 tests

#### Critical Path Files
- `agents/answer/answer_generator.py`

#### Output Formats
1. **Evidence Table** (Markdown)
2. **Envizi Pitch Table** (Markdown)
3. **Comparison Matrix** (Multi-company)
4. **Filtered Ranking** (List with justifications)

#### Quality Gates
- ✅ ≥12 tests passing
- ✅ Coverage ≥95%
- ✅ Markdown formatting validated

---

### CP-8: Business Context Extractor
**Duration**: 2 hours

#### Deliverables
- `agents/parser/business_context_extractor.py` - Extract from 10-K (CP)
- `tests/parser/test_business_context_extractor.py` - ≥10 tests

#### Critical Path Files
- `agents/parser/business_context_extractor.py`

#### Extraction Logic
```python
@dataclass
class BusinessContext:
    industry_sector: str
    sic_code: str
    revenue: float
    year: int

def extract_business_context(html_content: str, org_id: str, year: int) -> BusinessContext:
    """
    Extract from SEC 10-K:
    - Item 1 (Business): Industry, SIC code
    - Item 8 (Financials): Revenue
    """
```

#### Quality Gates
- ✅ ≥10 tests passing
- ✅ Coverage ≥95%
- ✅ Extraction accuracy >85%

---

### CP-9: Data Model Migration
**Duration**: 1 hour

#### Deliverables
- Update `data_model.md` - Document v2.0 schema
- `scripts/migrate_schema_v2.py` - Migration script
- Test backward compatibility

#### Schema Changes
See "Data Model Updates" section above.

#### Quality Gates
- ✅ Migration script tested
- ✅ Backward compatibility validated
- ✅ Documentation updated

---

### CP-10: Q&A Validation
**Duration**: 5 hours

#### Deliverables
- `tasks/008-esg-data-extraction/validation/gold_set.json` - Manual scoring (35 scores: 5 companies × 7 themes)
- `tasks/008-esg-data-extraction/validation/validation_harness.py` - Evaluation script
- `tasks/008-esg-data-extraction/validation/validation_results.json` - Results

#### Q&A Pairs (10 total)

**Seller Persona (5)**:
1. "What is Exxon's ESG rating?"
2. "How does Microsoft score on GHG Accounting?"
3. "Compare ESG maturity across Tesla, Apple, and Target"
4. "What are Exxon's critical ESG shortcomings?"
5. "Which companies score below 2 in Data Maturity?"

**Product Manager Persona (5)**:
1. "List companies scoring <2 in Target Setting with revenue >$50B"
2. "What are common gaps across energy sector companies?"
3. "Which accounts need Scope 3 supply chain solutions?"
4. "Generate a list of Stage 1 companies in Reporting & Disclosure"
5. "What themes does ExxonMobil score lowest in?"

#### Validation Metrics
1. **Scoring Accuracy**: Exact stage match (target: >90%)
2. **Characteristic Recall**: % of gold characteristics found (target: ≥85%)
3. **Evidence Quality**: Semantic similarity vs. gold evidence (target: ≥80%)
4. **External Correlation**: CDP/MSCI directional check

#### Quality Gates
- ✅ >90% exact match on gold set
- ✅ ≥85% characteristic recall
- ✅ ≥80% semantic similarity

---

### CP-11: Docker Containerization
**Duration**: 1 hour

#### Deliverables
- `Dockerfile` - Multi-stage build
- `.dockerignore` - Exclude unnecessary files
- `docker-compose.yml` - Local testing
- `deploy/ibm_cloud_code_engine.md` - Deployment guide

#### Dockerfile Structure
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY agents/ ./agents/
COPY rubrics/ ./rubrics/
COPY tasks/ ./tasks/

# Expose API
EXPOSE 8080

CMD ["python", "-m", "agents.service.api"]
```

#### Quality Gates
- ✅ Docker build succeeds
- ✅ Container runs locally
- ✅ Deployment guide validated

---

## SCA v13.8 Compliance

### Context Gate ✅
All required context files present:
- `hypothesis.md` - Metrics, thresholds, CP files
- `design.md` - Data strategy, verification plan
- `evidence.json` - ≥3 primary sources
- `data_sources.json` - Sources with SHA256
- `adr.md`, `assumptions.md` - Non-empty
- `cp_paths.json` - Critical path files defined

### TDD Guard ✅
- Tests written BEFORE implementation
- All CP tests marked with `@pytest.mark.cp`
- ≥1 Hypothesis property test per CP file
- ≥1 failure-path test per CP file

### Quality Gates ✅
- **Coverage**: ≥95% line & branch on CP files
- **Type Safety**: `mypy --strict` = 0 errors
- **Complexity**: CCN ≤10, Cognitive ≤15
- **Documentation**: `interrogate` ≥95%
- **Security**: `bandit` clean, `detect-secrets` clean
- **Traceability**: `qa/run_log.txt`, manifests, events

### MEA Loop Integration ✅
Each phase:
1. Write tests + implementation
2. Run `validate-only.ps1`
3. If "ok" → run `snapshot-save.ps1`
4. If "blocked" → fix → retry (max 3)

### Artifacts ✅
Per phase:
- `qa/run_log.txt` - Command outputs
- `artifacts/run_context.json` - Environment, versions
- `artifacts/run_manifest.json` - Files with SHA256
- `artifacts/run_events.jsonl` - Event stream
- `artifacts/state.json` - Phase state
- `reports/<phase>_snapshot.md` - Summary

---

## Resume Protocol

### To Resume from Any Checkpoint
1. Load `artifacts/state.json` to identify last completed phase
2. Load `artifacts/memory_sync.json` for context
3. Read `reports/<phase>_snapshot.md` for summary
4. Continue from next checkpoint

### Example
```powershell
# Check current state
cat tasks/008-esg-data-extraction/artifacts/state.json

# Output: { "last_checkpoint": "CP-5", "status": "ok", "timestamp": "..." }

# Resume from CP-6
# Start with tests for new question types...
```

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| CP-1: Rubric Loader | 3h | None |
| CP-2: Evidence Matcher | 4h | CP-1 |
| CP-3: Scoring Engine | 3h | CP-1, CP-2 |
| CP-4: Envizi KB | 2h | None (parallel) |
| CP-5: Pitch Generator | 3h | CP-3, CP-4 |
| CP-6: Query Expansion | 3h | CP-3 |
| CP-7: Answer Generator | 3h | CP-5, CP-6 |
| CP-8: Business Context | 2h | None (parallel) |
| CP-9: Data Model Migration | 1h | CP-2, CP-8 |
| CP-10: Q&A Validation | 5h | CP-7, CP-9 |
| CP-11: Docker | 1h | CP-10 |
| **Total** | **30h** | - |

---

## Success Metrics

### Phase Completion
- CP-0: ✅ Infrastructure (49 tests passing)
- CP-1: 🔄 Rubric Loader (In Progress)
- CP-2-11: ⏳ Pending

### Quality Tracking
| Gate | Target | Status |
|------|--------|--------|
| Test Coverage (CP) | ≥95% | ⏳ |
| Mypy Errors | 0 | ⏳ |
| Complexity CCN | ≤10 | ⏳ |
| Documentation | ≥95% | ⏳ |
| Scoring Accuracy | >90% | ⏳ |
| Semantic Similarity | ≥80% | ⏳ |

---

## Risks & Mitigations

### Risk 1: watsonx.ai API Rate Limits
**Mitigation**: Implement caching, batch requests, use VCR.py for tests

### Risk 2: Rubric Characteristic Ambiguity
**Mitigation**: Manual review of gold set, semantic similarity threshold tuning

### Risk 3: Schema Migration Data Loss
**Mitigation**: Backup before migration, backward compatibility testing

### Risk 4: Envizi URL Structure Changes
**Mitigation**: Cached knowledge base, graceful degradation, fallback to manual mapping

---

## Approval Record

**Approved By**: User
**Date**: 2025-10-23
**Approval Method**: ExitPlanMode tool approval
**Status**: ✅ APPROVED - Ready for Execution

---

**This plan supersedes all previous implementation plans and serves as the authoritative reference for Task 008 Phase 3 execution.**
