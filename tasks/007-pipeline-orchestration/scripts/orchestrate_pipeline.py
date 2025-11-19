"""
Task 007: Pipeline Orchestration - Unified ESG Evaluation Pipeline

Chains Tasks 003-006 into single executable workflow:
  Ingestion → Extraction → Retrieval → Scoring

Protocol: SCA v13.8-MEA
Author: Scientific Coding Agent
Date: 2025-11-19
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))


def main():
    """
    Execute end-to-end ESG pipeline for Apple 2024 10-K.

    Pipeline Stages:
      [1] Load Raw HTML (Task 003 artifact)
      [2] Extract Text Chunks (Task 004 - EnhancedPDFExtractor)
      [3] Index & Retrieve Evidence (Task 005 - VectorStore)
      [4] Score Findings (Task 006 - RubricV3Scorer)
      [5] Generate Final Output

    Returns:
        0 on success, 1 on failure
    """
    print("=" * 70)
    print("ESG PIPELINE ORCHESTRATION: Apple 2024 10-K")
    print("=" * 70)
    print()

    # ==========================================
    # [1/5] LOAD RAW HTML FILE
    # ==========================================
    print("[1/5] Loading raw HTML file from Task 003...")

    # Path verified in Task 003
    input_file = project_root / "data" / "raw" / "sec_edgar" / "AAPL_2024_10K.htm"

    if not input_file.exists():
        print(f"   FAIL - Raw input file not found: {input_file}")
        return 1

    file_size_mb = input_file.stat().st_size / (1024 * 1024)
    print(f"   PASS - Found file: {input_file.name}")
    print(f"   Size: {file_size_mb:.2f} MB")
    print()

    # ==========================================
    # [2/5] EXTRACT TEXT CHUNKS
    # ==========================================
    print("[2/5] Extracting text chunks with EnhancedPDFExtractor...")

    try:
        from agents.extraction.enhanced_pdf_extractor import EnhancedPDFExtractor

        extractor = EnhancedPDFExtractor(
            source_url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm",
            provider="SECEdgarProvider"
        )

        # Extract chunks (API verified in Task 004)
        chunks = extractor.extract_from_file(
            file_path=str(input_file),
            doc_id="AAPL_2024_10K",
            chunk_size=2000  # Same as Task 004
        )

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
    # [3/5] INDEX & RETRIEVE EVIDENCE
    # ==========================================
    print("[3/5] Indexing chunks and retrieving ESG evidence...")

    try:
        from apps.index.vector_store import VectorStore

        # Initialize vector store (same as Task 005)
        store = VectorStore()

        # Define vocabulary for keyword-based vectorization (Task 005 method)
        vocabulary = [
            "climate", "environmental", "carbon", "emissions", "greenhouse",
            "renewable", "energy", "sustainability", "esg", "pollution",
            "risk", "regulation", "compliance", "governance", "supply chain",
            "water", "waste", "recycling", "biodiversity", "social",
            "labor", "human rights", "diversity", "safety", "health",
            "apple", "company", "financial", "product", "technology"
        ]

        def create_text_vector(text: str, vocab: List[str]) -> List[float]:
            """Create TF-based vector (Task 005 algorithm)."""
            text_lower = text.lower()
            vector = []
            for term in vocab:
                count = text_lower.count(term.lower())
                vector.append(float(count))
            return vector

        # Index first 50 chunks (same sample size as Task 005)
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
                "doc_hash": chunk.doc_hash if hasattr(chunk, 'doc_hash') else "unknown"
            }

            # Upsert to store
            store.upsert(_id=chunk_id, vector=vector, metadata=metadata)

        print(f"   PASS - Indexed {len(sample_chunks)} chunks")
        print()

        # Execute retrieval queries (Task 005 queries)
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

            # Search (k=3, same as Task 005)
            results = store.knn(query=query_vector, k=3)

            # Format results
            formatted_results = []
            for rank, (chunk_id, score, metadata) in enumerate(results, 1):
                formatted_results.append({
                    "rank": rank,
                    "chunk_id": chunk_id,
                    "score": float(score),
                    "text_snippet": metadata.get("text", "")[:100],  # First 100 chars
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
    # [4/5] SCORE FINDINGS
    # ==========================================
    print("[4/5] Scoring findings with RubricV3Scorer...")

    try:
        from agents.scoring.rubric_v3_scorer import RubricV3Scorer
        from agents.scoring.rubric_loader import RubricLoader

        # Initialize scorer (Task 006 method)
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

            # Format as scorer input (Task 006 format)
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

            # Validate output
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
    # [5/5] AGGREGATE & OUTPUT
    # ==========================================
    print("[5/5] Aggregating scores and generating output...")

    try:
        # Aggregate scores (Task 006 method)
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
        final_output = {
            "task_id": "007-pipeline-orchestration",
            "execution_timestamp": datetime.utcnow().isoformat() + "Z",
            "company": "Apple Inc.",
            "ticker": "AAPL",
            "year": 2024,
            "report_type": "10-K",
            "pipeline_method": "Orchestrated: Task 003 → 004 → 005 → 006",
            "findings_scored": len(scored_findings),
            "aggregate_score": {
                "maturity_level": round(avg_maturity, 2),
                "maturity_label": most_common_label,
                "confidence": round(avg_confidence, 3),
                "dimension_breakdown": {k: round(v, 2) for k, v in aggregated_dimensions.items()}
            },
            "individual_scores": scored_findings,
            "provenance": {
                "source_file": str(input_file),
                "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm",
                "doc_hash": "24a830a0f1256e37",
                "chunks_extracted": len(chunks),
                "chunks_indexed": len(sample_chunks),
                "queries_executed": len(queries),
                "total_retrieval_results": sum(len(r) for r in all_retrieval_results.values())
            },
            "success": True
        }

        # Save output
        output_file = project_root / "tasks" / "007-pipeline-orchestration" / "artifacts" / "pipeline_output.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)

        print(f"   PASS - Output saved to: {output_file.name}")
        print()

    except Exception as e:
        print(f"   FAIL - Aggregation error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # ==========================================
    # SUMMARY
    # ==========================================
    print("=" * 70)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 70)
    print()
    print("Status: SUCCESS - All stages completed")
    print()
    print(f"Company: Apple Inc. (AAPL) - FY 2024")
    print(f"Report: 10-K (SEC EDGAR)")
    print(f"Findings Scored: {len(scored_findings)}")
    print(f"Aggregate Maturity: {avg_maturity:.2f} / 5.0 ({most_common_label})")
    print(f"Aggregate Confidence: {avg_confidence:.3f}")
    print()
    print("Top 3 Dimensions:")
    sorted_dims = sorted(aggregated_dimensions.items(), key=lambda x: x[1], reverse=True)
    for dim_code, dim_score in sorted_dims[:3]:
        print(f"  - {dim_code}: {dim_score:.2f}")
    print()
    print("Pipeline Stages:")
    print(f"  [1] Ingestion:  Task 003 artifact ({file_size_mb:.2f} MB)")
    print(f"  [2] Extraction: {len(chunks)} chunks")
    print(f"  [3] Indexing:   {len(sample_chunks)} vectors")
    print(f"  [4] Retrieval:  {sum(len(r) for r in all_retrieval_results.values())} results")
    print(f"  [5] Scoring:    {len(scored_findings)} findings -> 1 aggregate score")
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
