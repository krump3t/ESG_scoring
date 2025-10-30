
from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from agents.scoring.rubric_v3_scorer import DimensionScore, RubricV3Scorer
from apps.utils.provenance import sha256_text, trim_to_words
from libs.analytics import evidence_config  # Phase F
from libs.utils.clock import get_clock
from libs.utils.env import bool_flag, get
from libs.utils.determinism_guard import enforce as enforce_determinism

# Enforce determinism at module load
enforce_determinism()

clock = get_clock()

# Phase D: Retrieval tier configuration
RETRIEVAL_TIER = os.getenv("RETRIEVAL_TIER", "auto")  # "bronze", "silver", or "auto"
WX_OFFLINE_REPLAY = bool_flag("WX_OFFLINE_REPLAY")

DATA_ROOT = Path(get("DATA_ROOT", "artifacts"))
DEMO_ARTIFACT_DIR = DATA_ROOT / "demo"
PIPELINE_VALIDATION_DIR = DATA_ROOT / "pipeline_validation"
RUN_MANIFEST_PATH = DATA_ROOT / "run_manifest.json"


def run_score(
    company: str,
    year: int,
    query: str,
    semantic: bool = False,
    alpha: float = 0.6,
    k: int = 10,
    seed: int = 42,
) -> Dict[str, Any]:
    from libs.ranking.lexical import BM25Scorer
    from libs.retrieval.hybrid_semantic import fuse_lex_sem

    trace_id = _make_trace_id(company, year, query, alpha, k)

    manifest_record = _lookup_manifest(company, year)

    # Phase D: Intelligent tier selection (bronze vs silver)
    try:
        bronze_records = _load_data_records(manifest_record)
    except FileNotFoundError:
        if bool_flag("ALLOW_NETWORK"):
            # Fallback to live ingestion only if network allowed
            bronze_path = Path(manifest_record.get("bronze", ""))
            bronze_records = _build_bronze_from_live(company, year, bronze_path)
        else:
            bronze_records = []
    if not bronze_records:
        return {
            "company": company,
            "year": year,
            "scores": [],
            "trace_id": trace_id,
            "rubric_version": RubricV3Scorer().rubric.version,
            "model_version": "1.0",
            "parity": {"parity_ok": False, "evidence_ids": []},
        }

    # Phase E: Support both 'text' (PDF extraction) and 'extract_30w' (pre-processed bronze/silver)
    texts = [record.get("text") or record.get("extract_30w", "") for record in bronze_records]
    bm25 = BM25Scorer(k1=1.2, b=0.75).fit(texts)
    lex_scores_raw = bm25.score(query, texts)
    lex_scores = {
        bronze_records[index]["doc_id"]: float(lex_scores_raw[index])
        for index in range(len(bronze_records))
    }

    live_embeddings_enabled = semantic and bool_flag("LIVE_EMBEDDINGS")
    if live_embeddings_enabled:
        from apps.scoring import wx_client

        doc_vectors = wx_client.embed_text_batch(texts, use_live=True)
        query_vector = wx_client.embed_text_batch([query], use_live=True)[0]

        query_np = np.asarray(query_vector, dtype=np.float64)
        semantic_scores = {
            bronze_records[index]["doc_id"]: _cosine_similarity(
                query_np, np.asarray(doc_vectors[index], dtype=np.float64)
            )
            for index in range(len(bronze_records))
        }
    else:
        from libs.retrieval.embeddings.deterministic_embedder import DeterministicEmbedder

        embedder = DeterministicEmbedder(dim=128, seed=seed)
        query_vec = embedder.embed(query)
        # Phase E: Support both 'text' (PDF extraction) and 'extract_30w' (pre-processed)
        semantic_scores = {
            record["doc_id"]: _cosine_similarity(
                query_vec, embedder.embed(record.get("text") or record.get("extract_30w", ""))
            )
            for record in bronze_records
        }

    fused_results = fuse_lex_sem(lex_scores, semantic_scores, alpha=alpha)
    fused_topk = fused_results[: max(1, k)]
    fused_topk_ids = [doc_id for doc_id, _ in fused_topk]

    evidence_docs = [
        record for record in bronze_records if record["doc_id"] in fused_topk_ids
    ]
    evidence_entries = _build_evidence_entries(company, year, evidence_docs)
    parity_ok = len(evidence_entries) >= 2 and all(
        entry["doc_id"] in fused_topk_ids for entry in evidence_entries
    )

    scorer = RubricV3Scorer()
    dimension_scores = _aggregate_dimension_scores(
        scorer=scorer,
        documents=evidence_docs,
        evidence_entries=evidence_entries,
    )

    _write_parity_artifact(
        query=query,
        company=company,
        year=year,
        alpha=alpha,
        k=k,
        fused_topk=fused_topk,
        evidence_entries=evidence_entries,
        parity_ok=parity_ok,
        trace_id=trace_id,
    )
    _write_pipeline_artifacts(
        company=company,
        year=year,
        query=query,
        alpha=alpha,
        k=k,
        documents=bronze_records,
        evidence_entries=evidence_entries,
        dimension_scores=dimension_scores,
        trace_id=trace_id,
    )
    _write_retrieval_diagnostics(
        company=company,
        year=year,
        query=query,
        fused_topk=fused_topk,
        evidence_entries=evidence_entries,
        trace_id=trace_id,
    )

    scores_payload = [
        {
            "theme": payload["theme"],
            "stage": payload["stage"],
            "confidence": payload["confidence"],
            "stage_descriptor": payload["stage_descriptor"],
            "evidence": payload["evidence"],
        }
        for payload in dimension_scores
    ]

    return {
        "company": company,
        "year": year,
        "scores": scores_payload,
        "trace_id": trace_id,
        "rubric_version": scorer.rubric.version,
        "model_version": "1.0",
        "parity": {
            "parity_ok": parity_ok,
            "evidence_ids": [entry["doc_id"] for entry in evidence_entries],
        },
    }


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _make_trace_id(company: str, year: int, query: str, alpha: float, k: int) -> str:
    trace_input = json.dumps(
        {"company": company, "year": year, "query": query, "alpha": alpha, "k": k},
        sort_keys=True,
    )
    digest = sha256_text(trace_input)[:16]
    return f"sha256:{digest}"


def _lookup_manifest(company: str, year: int) -> Dict[str, Any]:
    manifest_path = Path("artifacts/demo/companies.json")
    if not manifest_path.exists():
        raise FileNotFoundError("No companies manifest found")
    manifest: List[Dict[str, Any]] = json.loads(manifest_path.read_text())
    for record in manifest:
        if record.get("company") == company and record.get("year") == year:
            return record
    raise FileNotFoundError(f"Company '{company}' with year {year} not found in manifest")


def _load_data_records(manifest_record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Phase D: Intelligent data loading with bronze/silver tier fallback.

    Strategy:
    - If layer="auto" (default): prefer silver, fallback to bronze
    - If layer="silver": only try silver
    - If layer="bronze": only try bronze (blocked in offline mode)
    - Bronze tier blocked when WX_OFFLINE_REPLAY=true (use silver for replay)

    Args:
        manifest_record: Company manifest entry with bronze/silver paths

    Returns:
        List of evidence records

    Raises:
        FileNotFoundError: If no data found in requested tier(s)
        RuntimeError: If bronze tier requested in offline replay mode
    """
    layer = manifest_record.get("layer", "auto")

    # Guard: Block bronze tier in offline replay mode UNLESS it's a PDF file (deterministic)
    if WX_OFFLINE_REPLAY and (layer == "bronze" or RETRIEVAL_TIER == "bronze"):
        bronze_path = Path(manifest_record.get("bronze", ""))
        is_pdf_file = bronze_path.is_file() and bronze_path.suffix.lower() == ".pdf"

        if not is_pdf_file:
            raise RuntimeError(
                "Bronze tier disabled for offline replay (set RETRIEVAL_TIER=silver or layer=auto). "
                "Offline mode requires deterministic silver layer data."
            )

    # Determine which tier(s) to try
    if layer == "silver" or RETRIEVAL_TIER == "silver":
        return _load_silver_records(manifest_record)
    elif layer == "bronze" or RETRIEVAL_TIER == "bronze":
        return _load_bronze_records_partitioned(manifest_record)
    else:  # layer == "auto" or RETRIEVAL_TIER == "auto"
        # Try silver first (consolidated, faster)
        try:
            return _load_silver_records(manifest_record)
        except FileNotFoundError:
            # Fallback to bronze if silver not available
            return _load_bronze_records_partitioned(manifest_record)


def _load_silver_records(manifest_record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Load from consolidated silver parquet file.

    Phase F Enhancement: Adds total_pages metadata to records for evidence validation.
    """
    silver_path_str = manifest_record.get("silver")
    if not silver_path_str:
        raise FileNotFoundError("No silver path in manifest")

    silver_path = Path(silver_path_str)
    if not silver_path.exists():
        raise FileNotFoundError(f"Silver file not found: {silver_path}")

    df = pd.read_parquet(silver_path)

    # Phase F: Compute total_pages from max page number
    if "page_no" in df.columns:
        max_page = df["page_no"].max()
        if pd.notna(max_page) and max_page > 0:
            total_pages = int(max_page)
        else:
            total_pages = 1  # Default if no valid page numbers
    elif "page_num" in df.columns:
        max_page = df["page_num"].max()
        if pd.notna(max_page) and max_page > 0:
            total_pages = int(max_page)
        else:
            total_pages = 1
    else:
        total_pages = 1  # Fallback if no page tracking

    # Add total_pages to all records
    df["total_pages"] = total_pages

    records = df.to_dict(orient="records")
    records.sort(key=lambda row: row.get("doc_id", ""))
    return records


def _load_bronze_records_partitioned(manifest_record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Load from theme-partitioned bronze directory OR extract from PDF.

    Phase F Enhancement: Adds total_pages metadata to records for evidence validation.
    """
    bronze_path_str = manifest_record.get("bronze")
    if not bronze_path_str:
        raise FileNotFoundError("No bronze path in manifest")

    bronze_path = Path(bronze_path_str)
    if not bronze_path.exists():
        raise FileNotFoundError(f"Bronze path not found: {bronze_path}")

    # Phase E: Check if bronze points to a PDF file (not a directory)
    if bronze_path.is_file() and bronze_path.suffix.lower() == ".pdf":
        # Extract directly from PDF with page tracking
        from agents.extraction.pdf_text_extractor import PDFTextExtractor

        extractor = PDFTextExtractor()
        chunks = extractor.extract_with_page_metadata(str(bronze_path), min_chunk_chars=100)

        if not chunks:
            raise RuntimeError(f"No chunks extracted from PDF: {bronze_path}")

        # Phase F: Get total page count from PDF
        total_pages = extractor.get_page_count(str(bronze_path))

        # Convert to records with doc_id
        doc_id = manifest_record.get("doc_id", bronze_path.stem)
        records = []
        for chunk in chunks:
            record = chunk.copy()
            record["doc_id"] = doc_id
            # Map page_num to page_no for consistency with existing evidence schema
            record["page_no"] = chunk["page_num"]
            # Phase F: Add total_pages metadata
            record["total_pages"] = total_pages
            records.append(record)

        records.sort(key=lambda row: (row.get("page_num", 0), row.get("char_start", 0)))
        return records

    # Original: Load from theme-partitioned directory
    if not bronze_path.is_dir():
        raise FileNotFoundError(f"Bronze path is neither PDF nor directory: {bronze_path}")

    # Load all theme partitions
    pattern = str(bronze_path / "theme=*" / "*.parquet")
    files = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(f"No bronze partition files found: {pattern}")

    dfs = []
    for file_path in sorted(files):  # Deterministic ordering
        df = pd.read_parquet(file_path)
        dfs.append(df)

    # Consolidate themes
    consolidated = pd.concat(dfs, ignore_index=True)
    if "evidence_id" in consolidated.columns:
        consolidated = consolidated.sort_values("evidence_id").reset_index(drop=True)

    # Phase F: Compute total_pages from max page number
    if "page_no" in consolidated.columns:
        max_page = consolidated["page_no"].max()
        if pd.notna(max_page) and max_page > 0:
            total_pages = int(max_page)
        else:
            total_pages = 1  # Default if no valid page numbers
    elif "page_num" in consolidated.columns:
        max_page = consolidated["page_num"].max()
        if pd.notna(max_page) and max_page > 0:
            total_pages = int(max_page)
        else:
            total_pages = 1
    else:
        total_pages = 1  # Fallback if no page tracking

    # Add total_pages to all records
    consolidated["total_pages"] = total_pages

    records = consolidated.to_dict(orient="records")
    return records


def _load_bronze_records(bronze_path: Path) -> List[Dict[str, Any]]:
    """Legacy bronze loader (kept for backward compatibility)."""
    if not bronze_path.exists():
        raise FileNotFoundError(f"Bronze file not found: {bronze_path}")
    df = pd.read_parquet(bronze_path)
    records = df.to_dict(orient="records")
    records.sort(key=lambda row: row.get("doc_id", ""))
    return records


def _build_bronze_from_live(company: str, year: int, bronze_path: Path) -> List[Dict[str, Any]]:
    """
    Build bronze records from live data source (SEC EDGAR or local PDF).

    Phase E Enhancement: Uses page-aware extraction to preserve page numbers
    for evidence provenance validation.
    """
    from agents.crawler.data_providers.sec_edgar_provider import fetch_10k
    from agents.extraction.pdf_text_extractor import PDFTextExtractor

    pdf_path = fetch_10k(company, year)

    # Phase E: Use page-aware extraction
    extractor = PDFTextExtractor()
    chunks = extractor.extract_with_page_metadata(str(pdf_path), min_chunk_chars=100)

    if not chunks:
        raise RuntimeError(f"No chunks extracted from SEC filing for {company} {year}.")

    # Convert to DataFrame with page numbers preserved
    df = pd.DataFrame(chunks)

    # Ensure required columns exist
    if "doc_id" not in df.columns:
        df["doc_id"] = f"{company.replace(' ', '_').lower()}_{year}"

    df["doc_id"] = df["doc_id"].astype(str)
    df["text"] = df["text"].fillna("").astype(str)

    # Ensure page_num is preserved (critical for evidence gates)
    if "page_num" not in df.columns:
        raise RuntimeError("Page tracking failed: 'page_num' not in extracted chunks")

    bronze_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(bronze_path, index=False)

    records = df.to_dict(orient="records")
    records.sort(key=lambda row: row.get("doc_id", ""))
    return records


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    denom = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / denom)


def _build_evidence_entries(
    company: str,
    year: int,
    documents: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build evidence entries with Phase F enhanced distinct page enforcement.

    Phase F Gate Requirements:
    - ≥3 distinct pages per theme (up from 2)
    - Page span ≥ get_min_span_for_doc(total_pages)
    - ≤5 evidence items per page (prevent concentration)

    Strategy:
    1. Collect evidence from all documents (not just first)
    2. Track unique pages seen
    3. Apply per-page capping to prevent concentration
    4. Prefer evidence from distinct pages with good span
    """
    evidence: List[Dict[str, Any]] = []
    pages_seen = set()

    # Get total_pages from first document (all should have same value)
    total_pages = 1
    if documents:
        total_pages = documents[0].get("total_pages", 1)

    # First pass: Collect evidence from ALL documents, tracking pages
    for doc in documents:
        doc_id = str(doc.get("doc_id", ""))
        # Phase E: Support both 'page_no' (from PDF extraction) and 'page' (from legacy records)
        page = doc.get("page_no") or doc.get("page_num") or doc.get("page", 0)
        # Phase E: Support both 'text' (PDF extraction) and 'extract_30w' (pre-processed)
        text_content = str(doc.get("text") or doc.get("extract_30w", ""))
        snippets = _generate_snippets(text_content)

        for index, snippet in enumerate(snippets):
            quote = trim_to_words(snippet, 30)
            if not quote:
                continue

            evidence_id = f"{doc_id}::{index:02d}"
            evidence.append(
                {
                    "evidence_id": evidence_id,
                    "doc_id": doc_id,
                    "quote": quote,
                    "sha256": sha256_text(f"{doc_id}::{quote}"),
                    "company": company,
                    "year": year,
                    "page": page,
                }
            )
            pages_seen.add(page)

        # Phase F: Stop after collecting enough evidence meeting enhanced gates
        min_distinct = evidence_config.EVIDENCE_PAGE_MIN_DISTINCT
        min_span = evidence_config.get_min_span_for_doc(total_pages)

        if len(evidence) >= 8:  # Collect more evidence to ensure quality after capping
            # Check if we have enough diversity
            pages_list = [e["page"] for e in evidence]
            validation = evidence_config.evidence_ok(pages_list, total_pages)
            if validation["passed"]:
                break

    # Phase F: Apply per-page capping to prevent concentration
    evidence = evidence_config.cap_per_page(evidence, max_per_page=evidence_config.EVIDENCE_PER_PAGE_CAP)

    # If we don't have enough distinct pages after capping, add fallback
    pages_list = [e["page"] for e in evidence]
    validation = evidence_config.evidence_ok(pages_list, total_pages)

    if documents and not validation["passed"] and len(pages_seen) < evidence_config.EVIDENCE_PAGE_MIN_DISTINCT:
        # Try to find documents with different pages than already seen
        for doc in documents:
            page = doc.get("page_no") or doc.get("page_num") or doc.get("page", 0)
            if page not in pages_seen:
                doc_id = str(doc.get("doc_id", ""))
                text = doc.get("text") or doc.get("extract_30w", "")
                fallback_quote = trim_to_words(str(text), 30)
                evidence.append(
                    {
                        "evidence_id": f"{doc_id}::fallback",
                        "doc_id": doc_id,
                        "quote": fallback_quote,
                        "sha256": sha256_text(f"{doc_id}::fallback::{fallback_quote}"),
                        "company": company,
                        "year": year,
                        "page": page,
                    }
                )
                pages_seen.add(page)

                # Re-check if we've met the gates
                pages_list = [e["page"] for e in evidence]
                validation = evidence_config.evidence_ok(pages_list, total_pages)
                if validation["passed"]:
                    break

    evidence.sort(key=lambda item: item["evidence_id"])
    return evidence[: max(8, len(evidence))]  # Return up to 8 evidence items


def _generate_snippets(text: str, max_segments: int = 4) -> List[str]:
    words = text.split()
    if not words:
        return []

    segments: List[str] = []
    step = max(10, len(words) // max_segments or 1)
    start = 0
    while start < len(words) and len(segments) < max_segments:
        segment_words = words[start : start + 30]
        if segment_words:
            segments.append(" ".join(segment_words))
        start += step

    if len(segments) < 2 and words:
        midpoint = len(words) // 2
        tail_segment = " ".join(words[midpoint : midpoint + 30])
        if tail_segment and tail_segment not in segments:
            segments.append(tail_segment)

    return segments


def _normalize_rd_candidate(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Phase F: Normalize RD (Risk & Disclosure) candidate for enhanced diagnostics.

    Returns:
        Dict with:
        - chunk_id: str - Document chunk identifier
        - page: int - Page number (normalized to int, default 0)
        - excerpt: str - Text excerpt (240 chars max with ellipsis)
    """
    # Normalize page to int
    page_raw = candidate.get("page") or candidate.get("page_no") or candidate.get("page_num") or 0
    try:
        page = int(page_raw)
    except (ValueError, TypeError):
        page = 0

    # Extract text content
    text = candidate.get("text") or candidate.get("extract_30w") or ""

    # Create excerpt (240 chars max)
    excerpt = (text[:240] + "…") if len(text) > 240 else text

    # Get chunk ID
    chunk_id = candidate.get("chunk_id") or candidate.get("id") or candidate.get("doc_id") or ""

    return {
        "chunk_id": str(chunk_id),
        "page": page,
        "excerpt": excerpt
    }


def _aggregate_dimension_scores(
    scorer: RubricV3Scorer,
    documents: Sequence[Mapping[str, Any]],
    evidence_entries: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    # Phase E: Include page_no in evidence payload for audit validation
    evidence_payload = [
        {
            "doc_id": entry["doc_id"],
            "quote": entry["quote"],
            "sha256": entry["sha256"],
            "page_no": entry.get("page", 0),  # Phase E: page tracking
        }
        for entry in evidence_entries
    ]

    document_scores: List[Mapping[str, DimensionScore]] = []
    # Phase F: Track RD candidates for enhanced diagnostics
    rd_candidates_diag: List[Dict[str, Any]] = []

    for doc in documents:
        # Phase E: Support both 'text' (PDF extraction) and 'extract_30w' (pre-processed)
        text_content = str(doc.get("text") or doc.get("extract_30w", ""))
        finding = {
            "finding_text": text_content,
            "framework": str(doc.get("framework", "")),
        }
        scores = scorer.score_all_dimensions(finding)
        document_scores.append(scores)

        # Phase F: Capture RD candidate diagnostics
        if "RD" in scores:
            rd_candidates_diag.append(_normalize_rd_candidate(doc))

    aggregated: List[Dict[str, Any]] = []
    for code in scorer.rubric.theme_order:
        theme = scorer.rubric.get_theme(code)
        candidates: List[DimensionScore] = [
            scores[code] for scores in document_scores if code in scores
        ]
        if candidates:
            best = max(candidates, key=lambda item: (item.score, item.confidence))
        else:
            fallback_descriptor = theme.get_stage(0).descriptor or theme.get_stage(0).label
            best = DimensionScore(
                score=0,
                evidence="No supporting evidence identified.",
                confidence=0.45,
                stage_descriptor=fallback_descriptor,
            )

        theme_result = {
            "theme": code,
            "stage": best.score,
            "confidence": best.confidence,
            "stage_descriptor": best.stage_descriptor,
            "evidence": evidence_payload,
        }

        # Phase F: Add RD diagnostics for Risk & Disclosure theme
        if code == "RD" and rd_candidates_diag:
            theme_result["rd_diagnostics"] = {
                "candidate_count": len(rd_candidates_diag),
                "candidates": rd_candidates_diag[:10]  # Limit to first 10 for brevity
            }

        aggregated.append(theme_result)

    aggregated.sort(key=lambda item: item["theme"])
    return aggregated


def _write_parity_artifact(
    query: str,
    company: str,
    year: int,
    alpha: float,
    k: int,
    fused_topk: Sequence[Tuple[str, float]],
    evidence_entries: Sequence[Mapping[str, Any]],
    parity_ok: bool,
    trace_id: str,
) -> None:
    PIPELINE_VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    sorted_topk = sorted(fused_topk, key=lambda item: (-item[1], item[0]))
    evidence_ids = sorted({entry["doc_id"] for entry in evidence_entries})
    payload = {
        "query": query,
        "company": company,
        "year": year,
        "alpha": alpha,
        "k": k,
        "fused_top_k": [{"doc_id": doc_id, "score": score} for doc_id, score in sorted_topk],
        "evidence_doc_ids": evidence_ids,
        "parity_ok": parity_ok,
        "trace_id": trace_id,
        "timestamp": clock.time(),
    }
    parity_path = PIPELINE_VALIDATION_DIR / "demo_topk_vs_evidence.json"
    parity_path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _write_pipeline_artifacts(
    company: str,
    year: int,
    query: str,
    alpha: float,
    k: int,
    documents: Sequence[Mapping[str, Any]],
    evidence_entries: Sequence[Mapping[str, Any]],
    dimension_scores: Sequence[Mapping[str, Any]],
    trace_id: str,
) -> None:
    DEMO_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    chunks_df = pd.DataFrame(documents)
    chunks_df.to_parquet(DEMO_ARTIFACT_DIR / "chunks.parquet", index=False)

    evidence_df = pd.DataFrame(evidence_entries)
    evidence_df.to_parquet(DEMO_ARTIFACT_DIR / "evidence.parquet", index=False)

    maturity_df = pd.DataFrame(
        {
            "theme": [score["theme"] for score in dimension_scores],
            "stage": [score["stage"] for score in dimension_scores],
            "confidence": [score["confidence"] for score in dimension_scores],
            "stage_descriptor": [score["stage_descriptor"] for score in dimension_scores],
        }
    )
    maturity_df.to_parquet(DEMO_ARTIFACT_DIR / "maturity.parquet", index=False)

    score_path = DEMO_ARTIFACT_DIR / "score.jsonl"
    with score_path.open("w", encoding="utf-8") as handle:
        for score in dimension_scores:
            handle.write(json.dumps(score, ensure_ascii=False) + "\n")

    manifest_payload = {
        "company": company,
        "year": year,
        "trace_id": trace_id,
        "query": {"text": query, "alpha": alpha, "k": k},
        "artifacts": {
            "chunks": str(DEMO_ARTIFACT_DIR / "chunks.parquet"),
            "evidence": str(DEMO_ARTIFACT_DIR / "evidence.parquet"),
            "maturity": str(DEMO_ARTIFACT_DIR / "maturity.parquet"),
            "score": str(score_path),
            "parity": str(PIPELINE_VALIDATION_DIR / "demo_topk_vs_evidence.json"),
        },
        "timestamp": clock.time(),
    }
    RUN_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_MANIFEST_PATH.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True))


def _write_retrieval_diagnostics(
    company: str,
    year: int,
    query: str,
    fused_topk: Sequence[Tuple[str, float]],
    evidence_entries: Sequence[Mapping[str, Any]],
    trace_id: str,
) -> None:
    """
    Write retrieval diagnostics for debugging and observability.

    Outputs:
    - retrieval_diag.json: Top-K candidates with scores and page metadata
    - evidence_selector.log: Evidence selection reasoning
    """
    PIPELINE_VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

    # Collect page information from evidence
    evidence_pages = {}
    for ev in evidence_entries:
        theme = "ALL"  # General evidence (not per-theme in current design)
        if theme not in evidence_pages:
            evidence_pages[theme] = []
        evidence_pages[theme].append({
            "doc_id": ev.get("doc_id"),
            "page": ev.get("page", 0),
            "evidence_id": ev.get("evidence_id"),
        })

    # Retrieval diagnostics
    retrieval_diag = {
        "query": query,
        "company": company,
        "year": year,
        "trace_id": trace_id,
        "top_k_candidates": [
            {"doc_id": doc_id, "score": float(score)}
            for doc_id, score in fused_topk
        ],
        "evidence_selected": len(evidence_entries),
        "evidence_pages": evidence_pages,
        "timestamp": clock.time(),
    }

    retrieval_diag_path = PIPELINE_VALIDATION_DIR / "retrieval_diag.json"
    retrieval_diag_path.write_text(json.dumps(retrieval_diag, indent=2, sort_keys=True))

    # Evidence selector log
    unique_pages = set(ev.get("page", 0) for ev in evidence_entries)
    selector_log = [
        f"Evidence Selection Log",
        f"Query: {query}",
        f"Company: {company} ({year})",
        f"Trace: {trace_id}",
        f"",
        f"Top-K Retrieval: {len(fused_topk)} candidates",
        f"Evidence Selected: {len(evidence_entries)} entries",
        f"Unique Pages: {len(unique_pages)} pages",
        f"Pages: {sorted(unique_pages)}",
        f"",
        f"Gate Status: {'PASS' if len(unique_pages) >= 2 else 'FAIL'} (≥2 distinct pages required)",
        f"",
        f"Evidence Details:",
    ]

    for ev in evidence_entries:
        selector_log.append(
            f"  [{ev.get('evidence_id')}] Page {ev.get('page', 0)}: {ev.get('quote', '')[:60]}..."
        )

    selector_log_path = PIPELINE_VALIDATION_DIR / "evidence_selector.log"
    selector_log_path.write_text("\n".join(selector_log), encoding="utf-8")


def lookup_manifest(company: str, year: int) -> Dict[str, Any]:
    return _lookup_manifest(company, year)


def build_evidence_entries(
    company: str, year: int, documents: Sequence[Mapping[str, Any]]
) -> List[Dict[str, Any]]:
    return _build_evidence_entries(company, year, list(documents))
