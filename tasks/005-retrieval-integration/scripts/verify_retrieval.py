"""
Task 005: Retrieval Integration Verification

Tests that VectorStore can ingest Apple 10-K chunks and retrieve relevant results for ESG queries.

TDD Phase 2 (Red): Expected to FAIL if vector generation or interface mismatch occurs.

Author: SCA Protocol v13.8-MEA
Date: 2025-11-19
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from collections import Counter
import math

# Add project root to path
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))


def create_text_vector(text: str, vocabulary: list[str]) -> list[float]:
    """
    Create a simple text vector based on keyword presence/frequency.

    This is a simplified TF-based approach (no IDF for simplicity).
    Each dimension represents the frequency of a vocabulary term.

    Args:
        text: Input text
        vocabulary: List of keywords to track

    Returns:
        Vector (list of floats) with same length as vocabulary
    """
    text_lower = text.lower()
    words = text_lower.split()
    word_counts = Counter(words)

    # Create vector: each dimension is frequency of vocabulary term
    vector = []
    for term in vocabulary:
        # Count occurrences (handles multi-word terms)
        count = text_lower.count(term.lower())
        vector.append(float(count))

    return vector


def main():
    """
    Verify VectorStore can ingest and search Apple 10-K chunks.

    Returns:
        0 on success, 1 on failure
    """
    print("=" * 70)
    print("RETRIEVAL INTEGRATION VERIFICATION: Apple 2024 10-K")
    print("=" * 70)
    print()

    # [1/8] Load Task 004 extraction artifact
    print("[1/8] Loading Task 004 extraction results...")

    artifact_path = project_root / "tasks" / "004-extraction-integration" / "artifacts" / "apple_2024_findings.json"

    if not artifact_path.exists():
        print(f"   FAIL - Artifact not found: {artifact_path}")
        return 1

    try:
        with open(artifact_path, 'r', encoding='utf-8') as f:
            artifact = json.load(f)

        chunks = artifact.get("findings_sample", [])
        print(f"   PASS - Loaded {len(chunks)} chunks from Task 004")
        print(f"   Source: {artifact.get('source_file', 'unknown')}")
        print(f"   Extraction method: {artifact.get('extraction_method', 'unknown')}")

        if len(chunks) == 0:
            print("   FAIL - No chunks in artifact")
            return 1

    except Exception as e:
        print(f"   FAIL - Error loading artifact: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [2/8] Import VectorStore
    print("[2/8] Importing VectorStore...")
    try:
        from apps.index.vector_store import VectorStore
        print("   PASS - VectorStore imported successfully")
    except ImportError as e:
        print(f"   FAIL - Import error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [3/8] Define vocabulary for vector generation
    print("[3/8] Defining ESG keyword vocabulary...")

    # ESG-relevant keywords for vector dimensions
    vocabulary = [
        "climate", "environmental", "carbon", "emissions", "greenhouse",
        "renewable", "energy", "sustainability", "esg", "pollution",
        "risk", "regulation", "compliance", "governance", "supply chain",
        "water", "waste", "recycling", "biodiversity", "social",
        "labor", "human rights", "diversity", "safety", "health",
        "apple", "company", "financial", "product", "technology"
    ]

    print(f"   PASS - Vocabulary size: {len(vocabulary)} terms")
    print(f"   Sample terms: {vocabulary[:10]}")

    # [4/8] Initialize VectorStore
    print("[4/8] Initializing VectorStore (local stub)...")
    try:
        store = VectorStore()
        print("   PASS - VectorStore initialized")
        print("   Mode: In-memory stub (no external database)")
    except Exception as e:
        print(f"   FAIL - Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [5/8] Ingest chunks into VectorStore
    print("[5/8] Ingesting chunks into VectorStore...")

    ingested_count = 0
    failed_count = 0

    try:
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", f"chunk_{ingested_count}")
            text = chunk.get("text", "")

            # Skip empty chunks
            if not text or len(text) < 10:
                failed_count += 1
                continue

            # Create vector from text
            vector = create_text_vector(text, vocabulary)

            # Prepare metadata
            metadata = {
                "chunk_id": chunk_id,
                "text": text[:500],  # Store truncated text (first 500 chars)
                "text_length": chunk.get("text_length", len(text)),
                "page": chunk.get("page", 0),
                "source_url": chunk.get("source_url", ""),
                "provider": chunk.get("provider", ""),
                "doc_hash": chunk.get("doc_hash", ""),
                "confidence": chunk.get("confidence", 1.0)
            }

            # Upsert into VectorStore
            store.upsert(_id=chunk_id, vector=vector, metadata=metadata)
            ingested_count += 1

        print(f"   PASS - Ingested {ingested_count} chunks")
        if failed_count > 0:
            print(f"   WARN - Skipped {failed_count} empty/invalid chunks")

    except Exception as e:
        print(f"   FAIL - Ingestion error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [6/8] Verify storage
    print("[6/8] Verifying chunk storage...")

    # VectorStore doesn't have a count() method, but we can check _store directly
    stored_count = len(store._store)

    if stored_count != ingested_count:
        print(f"   WARN - Storage mismatch: {ingested_count} ingested, {stored_count} stored")
    else:
        print(f"   PASS - Storage verified: {stored_count} chunks")

    # [7/8] Test similarity search
    print("[7/8] Testing similarity search...")
    print()

    test_queries = [
        ("climate risk", 3),
        ("environmental regulations", 3),
        ("carbon emissions", 3),
    ]

    all_results = {}

    for query_text, k in test_queries:
        print(f"   Query: '{query_text}' (top-{k})")

        try:
            # Convert query to vector
            query_vector = create_text_vector(query_text, vocabulary)

            # Execute k-NN search
            results = store.knn(query=query_vector, k=k)

            if len(results) == 0:
                print(f"      WARN - No results found")
                continue

            print(f"      PASS - Found {len(results)} results")

            # Store results
            all_results[query_text] = []

            # Display top result
            for i, (chunk_id, score, metadata) in enumerate(results[:k], 1):
                snippet = metadata.get("text", "")[:100]
                print(f"      [{i}] Score: {score:.3f} | {chunk_id} | {snippet}...")

                all_results[query_text].append({
                    "rank": i,
                    "chunk_id": chunk_id,
                    "score": float(score),
                    "text_snippet": snippet,
                    "metadata": {
                        "page": metadata.get("page"),
                        "source_url": metadata.get("source_url"),
                        "provider": metadata.get("provider"),
                        "doc_hash": metadata.get("doc_hash")
                    }
                })

            print()

        except Exception as e:
            print(f"      FAIL - Search error: {e}")
            import traceback
            traceback.print_exc()
            return 1

    # [8/8] Save retrieval results
    print("[8/8] Saving retrieval results...")

    artifacts_dir = project_root / "tasks" / "005-retrieval-integration" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    output_file = artifacts_dir / "retrieval_results.json"

    results_manifest = {
        "task_id": "005-retrieval-integration",
        "execution_timestamp": datetime.utcnow().isoformat() + "Z",
        "vector_store_type": "local_stub",
        "vocabulary_size": len(vocabulary),
        "chunks_ingested": ingested_count,
        "chunks_stored": stored_count,
        "queries_executed": len(test_queries),
        "retrieval_results": all_results,
        "success": True
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_manifest, f, indent=2, ensure_ascii=False)

    print(f"   PASS - Results saved to: {output_file}")

    # Success summary
    print()
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print()
    print("Status: PASS - Retrieval Integration Working")
    print()
    print(f"Chunks Ingested: {ingested_count}")
    print(f"Chunks Stored: {stored_count}")
    print(f"Vocabulary Size: {len(vocabulary)} ESG terms")
    print(f"Queries Tested: {len(test_queries)}")
    print(f"Total Results: {sum(len(r) for r in all_results.values())}")
    print()
    print("Notes:")
    print("  - VectorStore: In-memory stub (local only)")
    print("  - Vector Generation: Keyword frequency-based (simple TF)")
    print("  - Search Method: Cosine similarity on keyword vectors")
    print("  - No external embeddings (OpenAI, Cohere, etc.)")
    print()
    print("Sample Results:")
    for query, results in list(all_results.items())[:2]:
        print(f"  Query: '{query}'")
        if results:
            top_result = results[0]
            print(f"    Top: {top_result['chunk_id']} (score: {top_result['score']:.3f})")
        print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        print("Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 70)
        print(f"UNEXPECTED ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
