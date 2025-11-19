# Task 008: SEC Content Filtering

**Task ID:** 008-sec-content-filtering
**Protocol:** SCA v13.8-MEA
**Date:** 2025-11-19
**Depends On:** Task 007 (Pipeline Orchestration - COMPLETE)

---

## Objective

Remove XBRL/XML noise from SEC HTML filings to improve retrieval quality and ESG scoring accuracy.

**Problem:** Task 007 identified XBRL contamination in first 50 chunks, resulting in low-quality evidence retrieval and depressed ESG scores (0.29 vs expected 1.5+).

**Solution:** Implement content filtering layer to strip XBRL tags, XML metadata, and table-of-contents artifacts before chunking.

---

## Input

- **Raw SEC HTML:** data/raw/sec_edgar/AAPL_2024_10K.htm (1.43 MB)
- **Contaminants:** XBRL taxonomy tags, XML metadata, TOC artifacts

---

## Output

**Cleaned Text Chunks:**
- No XML/XBRL tags
- Actual narrative disclosure text (Item 1, 1A, 7)
- Ready for vectorization and scoring

---

## Success Criteria

1. ✅ Diagnostic confirms XBRL presence in raw HTML
2. ✅ Filter removes XBRL sections without losing disclosure text
3. ✅ Re-run Task 007 pipeline with filtered chunks
4. ✅ ESG score improves to >1.5 (from 0.29)
5. ✅ Retrieved evidence contains actual disclosure prose (not XML tags)

---

## Protocol Compliance

- **Authenticity:** Filters noise while preserving authentic disclosure text
- **Determinism:** Same input → same filtered output
- **Traceability:** Document which sections were filtered and why

---

**Task Status:** INITIALIZED
**Ready for Phase 1:** Diagnostic
