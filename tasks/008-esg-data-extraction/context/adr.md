# Architecture Decision Records (ADR)
## Task 008: ESG Maturity Evidence Extraction

**Task ID:** 008-esg-data-extraction
**Date:** 2025-10-22
**Protocol:** SCA v13.8-MEA

---

## ADR-001: Use Regex Pattern Matching Instead of ML/NLP Models

**Status:** Accepted

**Context:**
Evidence extraction could be implemented using:
1. Regex pattern matching (rule-based)
2. Named Entity Recognition (NER) models (spaCy, BERT)
3. Fine-tuned transformer models (custom BERT for ESG)

**Decision:**
Use **regex pattern matching with contextual validation** for Task 008 v1.

**Rationale:**
- **Speed:** Regex is 10-100x faster than transformer inference
- **Determinism:** Same input always produces same output (critical for SCA protocol)
- **Transparency:** Patterns are human-readable and explainable
- **Sufficient Precision:** Keyword-based matching can achieve 75-85% precision for well-defined evidence types (SBTi, GHG Protocol, TCFD)
- **Lower Complexity:** No model training, no GPU requirements, simpler deployment

**Trade-offs:**
- **Lower Recall:** May miss paraphrased or implicit evidence
- **Context Limitations:** Regex doesn't understand semantic similarity
- **Maintenance:** Adding new evidence types requires manual pattern authoring

**Consequences:**
- Fast batch processing (<45s per filing)
- Explainable results (can show which pattern matched)
- May require manual validation to ensure precision ≥75%
- Future Task 009 could enhance with ML for higher recall

---

## ADR-002: Extract 30-Word Context Windows Instead of Full Sentences

**Status:** Accepted

**Context:**
When evidence is found, we need to extract surrounding text for:
1. Human review (validate match relevance)
2. Explainability (show users why stage was assigned)
3. Traceability (link back to source document)

Options:
- Extract full sentence containing match
- Extract fixed N-word window (e.g., 15 words before + 15 after)
- Extract full paragraph containing match

**Decision:**
Extract **30-word window** (15 words before match + match + 15 words after).

**Rationale:**
- **Fixed Length:** Enables consistent database schema and UI display
- **Sufficient Context:** 30 words typically spans 1-2 sentences, enough to understand meaning
- **Performance:** Fast to extract (simple slice operation)
- **Alignment with Rubric:** ESG Maturity Rubric specifies "30w" extract (line 119)

**Trade-offs:**
- May truncate mid-sentence (mitigated by including ellipsis "..." indicator)
- May miss broader context (mitigated by storing page_no for lookup)

**Consequences:**
- Evidence database has consistent extract_30w field (max ~200 chars)
- UI can display evidence in standard card format
- Humans can quickly review relevance without reading full document

---

## ADR-003: Use SHA256 Hashing for Evidence Deduplication

**Status:** Accepted

**Context:**
The same evidence text may appear multiple times in a filing (e.g., "Scope 1 emissions" mentioned in executive summary, MD&A, and footnotes). Need to deduplicate to avoid inflating evidence counts.

Options:
1. No deduplication (keep all matches)
2. Fuzzy deduplication (Levenshtein distance)
3. SHA256 hash-based exact deduplication

**Decision:**
Use **SHA256 hash of extract_30w** for exact deduplication.

**Rationale:**
- **Deterministic:** Same text always produces same hash
- **Efficient:** O(1) hash table lookup for deduplication
- **Alignment with Rubric:** ESG Maturity Rubric requires hash_sha256 field (line 121)
- **Traceability:** Hash enables deduplication across extraction runs

**Trade-offs:**
- Only deduplicates exact matches (different wording not deduplicated)
- 30-word window may include different surrounding context for same core evidence

**Consequences:**
- Evidence table has hash_sha256 column
- Before inserting evidence, check if hash already exists
- Reduces evidence count by ~10-30% (empirical estimate)

---

## ADR-004: Process SEC Filings as HTML Instead of Converting to PDF

**Status:** Accepted

**Context:**
SEC filings are available in multiple formats:
1. HTML (native EDGAR format)
2. XBRL (structured financial data)
3. Can be converted to PDF (but requires additional tools)

**Decision:**
Parse **HTML directly** using BeautifulSoup, do NOT convert to PDF.

**Rationale:**
- **Native Format:** HTML is the primary SEC EDGAR format
- **Simpler Parsing:** BeautifulSoup handles HTML robustly, PDF parsing is error-prone
- **Faster Processing:** No conversion step required
- **Section Structure:** HTML preserves semantic structure (headings, tables)
- **Already Downloaded:** Task 007 downloaded HTML files

**Trade-offs:**
- HTML structure varies by company (not fully standardized)
- Nested tables can be complex to parse

**Consequences:**
- Filing parser uses BeautifulSoup4 library
- Must handle inconsistent HTML structure gracefully
- Page number extraction may be approximate (HTML doesn't have inherent pages)

---

## ADR-005: Assign Conservative Stage Scores When Evidence is Ambiguous

**Status:** Accepted

**Context:**
Some evidence may indicate multiple maturity stages. Example: "We are committed to science-based targets" could be Stage 3 (SBTi submission) or Stage 2 (quantitative target intent).

Options:
1. Assign highest stage indicated by any evidence
2. Assign average of all stage indicators
3. Assign lowest (most conservative) stage when ambiguous

**Decision:**
Use **conservative scoring**: When evidence is ambiguous or weak, assign lower stage.

**Rationale:**
- **Reduces False Positives:** Better to under-score than over-score maturity
- **Honesty:** Conservative approach aligns with SCA "Honest Status Reporting" invariant
- **Credibility:** Stakeholders trust conservative assessments more than inflated ones
- **Threshold Logic:** Require multiple Stage 4 evidence items to assign Stage 4 (see design.md Stage Classifier)

**Trade-offs:**
- May under-represent true maturity for companies with implicit evidence
- Bias toward lower scores

**Consequences:**
- Stage Classifier implements conservative logic (design.md line 450)
- Manual validation should check if conservative scoring is too strict
- Documentation explains conservative approach to stakeholders

---

## ADR-006: Store Evidence in JSON Files Instead of Database for Task 008

**Status:** Accepted

**Context:**
Extracted evidence needs to be stored for:
- Quality validation
- Maturity scoring (Task 009)
- MCP-Iceberg integration (Task 010)

Options:
1. JSON files (one per filing)
2. SQLite database
3. PostgreSQL database
4. Direct to Iceberg (Task 010)

**Decision:**
Store evidence in **JSON files** for Task 008, migrate to database in Task 010.

**Rationale:**
- **Simplicity:** JSON is human-readable, easy to inspect
- **PoC Appropriate:** For 25 filings, database overhead is unnecessary
- **Flexibility:** Easy to modify schema during development
- **Traceability:** JSON files are artifacts for SCA protocol
- **Future Migration:** Task 010 will migrate to Iceberg (gold.esg_evidence table)

**Trade-offs:**
- No SQL querying (must load JSON into memory)
- Not suitable for scale (>1000 filings)

**Consequences:**
- Evidence output: `tasks/008-esg-data-extraction/data/evidence/{company}_{year}.json`
- Aggregated evidence: `tasks/008-esg-data-extraction/qa/all_evidence.json`
- Task 010 will implement migration to Iceberg

---

## ADR-007: Use Parallel Processing (4 Workers) for Batch Extraction

**Status:** Accepted

**Context:**
Need to process 25 filings. Processing can be:
1. Sequential (one filing at a time)
2. Parallel (multiple filings concurrently)

**Decision:**
Use **multiprocessing with 4 worker processes** for batch extraction.

**Rationale:**
- **4 CPUs:** Most development machines have ≥4 cores
- **CPU-Bound:** Regex pattern matching is CPU-intensive
- **Linear Speedup:** 4 workers → ~4x speedup (25 filings @ 30s each = 750s → ~190s)
- **Target Met:** 190s total / 25 filings = 7.6s average (well under 45s P95 target)

**Trade-offs:**
- Memory usage increases (4 filings in memory concurrently)
- Slightly more complex error handling

**Consequences:**
- Use Python multiprocessing.Pool with 4 processes
- Must ensure thread safety (each worker has own matcher instances)
- Logging must be thread-safe (use multiprocessing.Queue or separate log files)

---

## ADR-008: Use Confidence Threshold of 0.5 for Evidence Inclusion

**Status:** Accepted

**Context:**
Pattern matching produces confidence scores 0.0-1.0. Need to decide minimum threshold for including evidence in results.

Options:
- 0.5 (moderate confidence)
- 0.7 (high confidence)
- 0.9 (very high confidence)

**Decision:**
Use **0.5 confidence threshold** for evidence inclusion, report all evidence ≥0.5.

**Rationale:**
- **Recall:** 0.5 threshold maximizes recall (captures more potential evidence)
- **Human Validation:** Manual validation (5 filings) will check precision
- **Explainability:** Including lower-confidence evidence allows users to see reasoning
- **Conservative Scoring:** Stage Classifier already applies conservative logic, so having more evidence inputs is beneficial

**Trade-offs:**
- Higher false positive rate (mitigated by manual validation)
- Larger evidence database (more storage)

**Consequences:**
- Evidence items with confidence ≥0.5 are stored
- Lower-confidence items (0.5-0.7) flagged for review
- Manual validation measures precision across confidence ranges

---

## Summary Table

| ADR | Decision | Rationale | Impact on Task 008 |
|-----|----------|-----------|-------------------|
| 001 | Regex pattern matching | Speed, determinism, transparency | Fast extraction, explainable results |
| 002 | 30-word context windows | Fixed length, sufficient context | Consistent evidence format |
| 003 | SHA256 deduplication | Deterministic, efficient | Reduced evidence count, traceability |
| 004 | Parse HTML directly | Native format, simpler parsing | BeautifulSoup4, no conversion step |
| 005 | Conservative stage scoring | Reduces false positives, honesty | Lower but more credible maturity scores |
| 006 | JSON storage for PoC | Simplicity, human-readable | Easy inspection, migrate later |
| 007 | 4-worker parallel processing | CPU-bound, linear speedup | <45s P95 target met |
| 008 | 0.5 confidence threshold | Maximize recall, manual validation | More evidence items, measured precision |

---

**Version:** 1.0
**Status:** All ADRs accepted and implemented in design.md
**Next:** Create assumptions.md
