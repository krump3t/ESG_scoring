"""
Task 009: Orchestrator V3 - Remediated Pipeline with XBRL Cleaning

Integrates SecHtmlCleaner from Task 008 into the end-to-end pipeline.
Demonstrates score improvement through noise removal.

Protocol: SCA v13.8-MEA
Date: 2025-11-19
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))


def main():
    """
    Execute remediated ESG pipeline for Apple 2024 10-K.

    Pipeline Stages:
      [1] Load Raw HTML (Task 003 artifact)
      [2] Clean XBRL Noise (SecHtmlCleaner - Task 008)
      [3] Extract Text Chunks (EnhancedPDFExtractor)
      [4] Index & Retrieve Evidence (VectorStore)
      [5] Score Findings (RubricV3Scorer)
      [6] Generate Comparison Report

    Returns:
        0 on success, 1 on failure
    """
    print("=" * 70)
    print("REMEDIATED PIPELINE (V3): Apple 2024 10-K")
    print("=" * 70)
    print()

    # ==========================================
    # [1/6] LOAD RAW HTML FILE
    # ==========================================
    print("[1/6] Loading raw HTML file...")

    input_file = project_root / "data" / "raw" / "sec_edgar" / "AAPL_2024_10K.htm"

    if not input_file.exists():
        print(f"   FAIL - Raw input file not found: {input_file}")
        return 1

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            raw_html = f.read()

        file_size_mb = input_file.stat().st_size / (1024 * 1024)
        print(f"   PASS - Found file: {input_file.name}")
        print(f"   Size: {file_size_mb:.2f} MB ({len(raw_html):,} chars)")
        print()

    except Exception as e:
        print(f"   FAIL - Error loading file: {e}")
        return 1

    # ==========================================
    # [2/6] CLEAN XBRL NOISE
    # ==========================================
    print("[2/6] Cleaning XBRL/XML metadata with SecHtmlCleaner...")

    try:
        from agents.preprocessing.sec_cleaner import SecHtmlCleaner

        cleaner = SecHtmlCleaner()
        clean_text = cleaner.clean(raw_html)

        reduction_pct = 100 * (1 - len(clean_text) / len(raw_html))

        print(f"   PASS - Cleaned successfully")
        print(f"   Original: {len(raw_html):,} chars")
        print(f"   Cleaned:  {len(clean_text):,} chars")
        print(f"   Reduction: {reduction_pct:.1f}%")
        print()

    except Exception as e:
        print(f"   FAIL - Cleaning error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==========================================
    # [3/6] EXTRACT TEXT CHUNKS
    # ==========================================
    print("[3/6] Extracting text chunks from cleaned HTML...")

    try:
        from agents.extraction.enhanced_pdf_extractor import EnhancedPDFExtractor

        # Write cleaned text to temp file for extractor
        with tempfile.NamedTemporaryFile(mode='w', suffix='.htm', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(clean_text)
            tmp_path = tmp_file.name

        extractor = EnhancedPDFExtractor(
            source_url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm",
            provider="SECEdgarProvider"
        )

        # Extract chunks from cleaned file
        chunks = extractor.extract_from_file(
            file_path=tmp_path,
            doc_id="AAPL_2024_10K_CLEANED",
            chunk_size=2000
        )

        # Clean up temp file
        Path(tmp_path).unlink()

        print(f"   PASS - Extracted {len(chunks)} chunks")

        # Calculate total text size
        total_chars = sum(len(chunk.text) for chunk in chunks)
        print(f"   Total text: {total_chars:,} characters")
        print()

    except Exception as e:
        print(f"   FAIL - Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==========================================
    # [4/6] INDEX & RETRIEVE EVIDENCE
    # ==========================================
    print("[4/6] Indexing chunks and retrieving ESG evidence...")

    try:
        from apps.index.vector_store import VectorStore

        # Initialize vector store
        store = VectorStore()

        # Define vocabulary (same as Task 007)
        vocabulary = [
            "climate", "environmental", "carbon", "emissions", "greenhouse",
            "renewable", "energy", "sustainability", "esg", "pollution",
            "risk", "regulation", "compliance", "governance", "supply chain",
            "water", "waste", "recycling", "biodiversity", "social",
            "labor", "human rights", "diversity", "safety", "health",
            "apple", "company", "financial", "product", "technology"
        ]

        def create_text_vector(text: str, vocab: List[str]) -> List[float]:
            """Create TF-based vector."""
            text_lower = text.lower()
            vector = []
            for term in vocab:
                count = text_lower.count(term.lower())
                vector.append(float(count))
            return vector

        # Index first 50 chunks (same as Task 007 for fair comparison)
        sample_chunks = chunks[:50]
        print(f"   Indexing {len(sample_chunks)} chunks...")

        for i, chunk in enumerate(sample_chunks):
            chunk_id = f"chunk_{i:04d}"
            text = chunk.text

            # Create vector
            vector = create_text_vector(text, vocabulary)

            # Prepare metadata
            metadata = {
                "chunk_id": chunk_id,
                "text": text[:500],  # Truncate for storage
                "source_url": chunk.source_url,
                "provider": chunk.provider,
                "page": chunk.page if hasattr(chunk, 'page') else (i // 5),
                "doc_hash": chunk.doc_hash if hasattr(chunk, 'doc_hash') else "cleaned"
            }

            # Upsert to store
            store.upsert(_id=chunk_id, vector=vector, metadata=metadata)

        print(f"   PASS - Indexed {len(sample_chunks)} chunks")
        print()

        # Execute retrieval queries (same as Task 007)
        queries = [
            "climate risk",
            "environmental regulations",
            "carbon emissions"
        ]

        all_retrieval_results = {}

        for query in queries:
            print(f"   Querying: '{query}'")

            # Create query vector
            query_vector = create_text_vector(query, vocabulary)

            # Search
            results = store.knn(query=query_vector, k=3)

            # Format results
            formatted_results = []
            for rank, (chunk_id, score, metadata) in enumerate(results, 1):
                formatted_results.append({
                    "rank": rank,
                    "chunk_id": chunk_id,
                    "score": float(score),
                    "text_snippet": metadata.get("text", "")[:100],
                    "metadata": {
                        "page": metadata.get("page", 0),
                        "source_url": metadata.get("source_url", ""),
                        "provider": metadata.get("provider", ""),
                        "doc_hash": metadata.get("doc_hash", "")
                    }
                })

            all_retrieval_results[query] = formatted_results

            if formatted_results:
                top_score = formatted_results[0]["score"]
                print(f"      Top result: {formatted_results[0]['chunk_id']} (score: {top_score:.3f})")

        print(f"   PASS - Retrieved {sum(len(r) for r in all_retrieval_results.values())} total results")
        print()

    except Exception as e:
        print(f"   FAIL - Indexing/Retrieval error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==========================================
    # [5/6] SCORE FINDINGS
    # ==========================================
    print("[5/6] Scoring findings with RubricV3Scorer...")

    try:
        from agents.scoring.rubric_v3_scorer import RubricV3Scorer
        from agents.scoring.rubric_loader import RubricLoader

        # Initialize scorer
        loader = RubricLoader()
        scorer = RubricV3Scorer(loader=loader)

        print(f"   Rubric loaded: {len(scorer.rubric.themes)} themes")
        print()

        scored_findings = []

        # Score top result from each query
        for query, results in all_retrieval_results.items():
            if not results:
                continue

            top_result = results[0]

            # Format as scorer input
            finding = {
                "finding_text": top_result.get("text_snippet", ""),
                "framework": "SEC 10-K Item 1A",
                "query": query,
                "rank": top_result.get("rank", 0),
                "retrieval_score": top_result.get("score", 0.0),
                "source_metadata": top_result.get("metadata", {})
            }

            # Score the finding
            score_result = scorer.score_finding(finding)

            # Extract scores
            maturity_level = score_result["maturity_level"]
            maturity_label = score_result["maturity_label"]
            confidence = score_result["confidence"]
            dimension_breakdown = score_result["dimension_breakdown"]

            print(f"   Scored: '{query}'")
            print(f"      Maturity: {maturity_level} ({maturity_label})")
            print(f"      Confidence: {confidence:.3f}")

            # Store result
            scored_findings.append({
                "query": query,
                "finding_text": finding.get("finding_text", "")[:200],
                "retrieval_score": finding.get("retrieval_score", 0.0),
                "maturity_level": float(maturity_level),
                "maturity_label": maturity_label,
                "confidence": float(confidence),
                "dimension_breakdown": {k: int(v) for k, v in dimension_breakdown.items()},
                "source_metadata": finding.get("source_metadata", {})
            })

        print()
        print(f"   PASS - Scored {len(scored_findings)} findings")
        print()

    except Exception as e:
        print(f"   FAIL - Scoring error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==========================================
    # [6/6] AGGREGATE & COMPARE
    # ==========================================
    print("[6/6] Aggregating scores and generating comparison...")

    try:
        # Aggregate scores
        avg_maturity = sum(r["maturity_level"] for r in scored_findings) / len(scored_findings)
        avg_confidence = sum(r["confidence"] for r in scored_findings) / len(scored_findings)

        # Most common label
        label_counts = {}
        for r in scored_findings:
            label = r["maturity_label"]
            label_counts[label] = label_counts.get(label, 0) + 1
        most_common_label = max(label_counts, key=label_counts.get)

        # Aggregate dimension scores
        aggregated_dimensions = {}
        all_dim_codes = scored_findings[0]["dimension_breakdown"].keys()
        for dim_code in all_dim_codes:
            dim_scores = [r["dimension_breakdown"][dim_code] for r in scored_findings]
            aggregated_dimensions[dim_code] = sum(dim_scores) / len(dim_scores)

        # Create final output
        remediated_output = {
            "task_id": "009-integrated-remediation",
            "execution_timestamp": datetime.utcnow().isoformat() + "Z",
            "company": "Apple Inc.",
            "ticker": "AAPL",
            "year": 2024,
            "report_type": "10-K",
            "pipeline_method": "Remediated: Task 003 -> XBRL Cleaning (Task 008) -> 004 -> 005 -> 006",
            "findings_scored": len(scored_findings),
            "aggregate_score": {
                "maturity_level": round(avg_maturity, 2),
                "maturity_label": most_common_label,
                "confidence": round(avg_confidence, 3),
                "dimension_breakdown": {k: round(v, 2) for k, v in aggregated_dimensions.items()}
            },
            "individual_scores": scored_findings,
            "cleaning_stats": {
                "original_size": len(raw_html),
                "cleaned_size": len(clean_text),
                "reduction_percent": round(reduction_pct, 1)
            },
            "provenance": {
                "source_file": str(input_file),
                "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm",
                "chunks_extracted": len(chunks),
                "chunks_indexed": len(sample_chunks),
                "queries_executed": len(queries),
                "total_retrieval_results": sum(len(r) for r in all_retrieval_results.values())
            },
            "success": True
        }

        # Save output
        output_file = project_root / "tasks" / "009-integrated-remediation" / "artifacts" / "remediated_score.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(remediated_output, f, indent=2, ensure_ascii=False)

        print(f"   PASS - Output saved to: {output_file.name}")
        print()

        # Load Task 007 baseline for comparison
        baseline_file = project_root / "tasks" / "007-pipeline-orchestration" / "artifacts" / "pipeline_output.json"

        baseline_maturity = 0.29  # Default if file not found
        baseline_confidence = 0.487

        if baseline_file.exists():
            with open(baseline_file, 'r', encoding='utf-8') as f:
                baseline_data = json.load(f)
                baseline_maturity = baseline_data.get("aggregate_score", {}).get("maturity_level", 0.29)
                baseline_confidence = baseline_data.get("aggregate_score", {}).get("confidence", 0.487)

        # Calculate improvement
        maturity_improvement = avg_maturity - baseline_maturity
        confidence_improvement = avg_confidence - baseline_confidence
        improvement_factor = avg_maturity / baseline_maturity if baseline_maturity > 0 else 0

    except Exception as e:
        print(f"   FAIL - Aggregation error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==========================================
    # SUMMARY & COMPARISON
    # ==========================================
    print("=" * 70)
    print("REMEDIATION RESULTS")
    print("=" * 70)
    print()
    print("Status: SUCCESS - Remediated pipeline completed")
    print()
    print(f"Company: Apple Inc. (AAPL) - FY 2024")
    print(f"Report: 10-K (SEC EDGAR)")
    print()
    print("BEFORE (Task 007 - XBRL Contaminated):")
    print(f"  - Maturity: {baseline_maturity:.2f} / 5.0")
    print(f"  - Confidence: {baseline_confidence:.3f}")
    print()
    print("AFTER (Task 009 - XBRL Cleaned):")
    print(f"  - Maturity: {avg_maturity:.2f} / 5.0")
    print(f"  - Confidence: {avg_confidence:.3f}")
    print()
    print("IMPROVEMENT:")
    print(f"  - Maturity: +{maturity_improvement:.2f} ({improvement_factor:.1f}x)")
    print(f"  - Confidence: +{confidence_improvement:.3f}")
    print()
    print("Top 3 Dimensions (Remediated):")
    sorted_dims = sorted(aggregated_dimensions.items(), key=lambda x: x[1], reverse=True)
    for dim_code, dim_score in sorted_dims[:3]:
        print(f"  - {dim_code}: {dim_score:.2f}")
    print()
    print("Cleaning Stats:")
    print(f"  - Original HTML: {len(raw_html):,} chars")
    print(f"  - Cleaned Text: {len(clean_text):,} chars")
    print(f"  - Noise Removed: {reduction_pct:.1f}%")
    print()
    print(f"Output: {output_file}")
    print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"UNEXPECTED ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
