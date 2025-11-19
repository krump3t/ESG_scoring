"""
Task 006: Scoring Integration Verification

Tests that RubricV3Scorer can consume retrieval results from Task 005 and produce ESG maturity scores.

TDD Phase 2 (Red): Expected to FAIL if rubric not found or input format mismatch.

Author: SCA Protocol v13.8-MEA
Date: 2025-11-19
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any

# Add project root to path
project_root = Path(__file__).parents[3]
sys.path.insert(0, str(project_root))


def main():
    """
    Verify RubricV3Scorer can score retrieval results from Task 005.

    Returns:
        0 on success, 1 on failure
    """
    print("=" * 70)
    print("SCORING INTEGRATION VERIFICATION: Apple 2024 10-K")
    print("=" * 70)
    print()

    # [1/7] Load Task 005 retrieval results
    print("[1/7] Loading Task 005 retrieval results...")

    retrieval_path = project_root / "tasks" / "005-retrieval-integration" / "artifacts" / "retrieval_results.json"

    if not retrieval_path.exists():
        print(f"   FAIL - Retrieval results not found: {retrieval_path}")
        return 1

    try:
        with open(retrieval_path, 'r', encoding='utf-8') as f:
            retrieval_data = json.load(f)

        retrieval_results = retrieval_data.get("retrieval_results", {})
        print(f"   PASS - Loaded {len(retrieval_results)} query result sets")
        print(f"   Queries: {list(retrieval_results.keys())}")

        total_results = sum(len(results) for results in retrieval_results.values())
        print(f"   Total results: {total_results}")

        if total_results == 0:
            print("   FAIL - No retrieval results available")
            return 1

    except Exception as e:
        print(f"   FAIL - Error loading retrieval results: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [2/7] Import RubricV3Scorer
    print("[2/7] Importing RubricV3Scorer...")
    try:
        from agents.scoring.rubric_v3_scorer import RubricV3Scorer
        from agents.scoring.rubric_loader import RubricLoader
        print("   PASS - RubricV3Scorer imported successfully")
    except ImportError as e:
        print(f"   FAIL - Import error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [3/7] Initialize scorer
    print("[3/7] Initializing RubricV3Scorer...")
    try:
        # Check rubric file exists
        rubric_path = project_root / "rubrics" / "maturity_v3.json"
        if not rubric_path.exists():
            print(f"   WARN - Rubric not found at: {rubric_path}")
            print("   Attempting to use RubricLoader default...")

        loader = RubricLoader()
        scorer = RubricV3Scorer(loader=loader)
        print("   PASS - Scorer initialized")
        print(f"   Rubric path: {rubric_path}")

        # Get theme info
        theme_count = len(scorer.rubric.themes)
        theme_codes = [theme.code for theme in scorer.rubric.themes_in_order]
        print(f"   Themes loaded: {theme_count}")
        print(f"   Theme codes: {theme_codes[:5]}...")  # Show first 5

    except Exception as e:
        print(f"   FAIL - Scorer initialization error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [4/7] Format retrieval results as scorer input
    print("[4/7] Formatting retrieval results for scoring...")

    test_findings = []

    try:
        # Use first result from each query for testing
        for query, results in retrieval_results.items():
            if not results:
                continue

            # Get top result
            top_result = results[0]

            # Format as scorer input
            finding = {
                "finding_text": top_result.get("text_snippet", ""),
                "framework": "SEC 10-K Item 1A",  # Apple 10-K context
                "query": query,
                "rank": top_result.get("rank", 0),
                "retrieval_score": top_result.get("score", 0.0),
                "source_metadata": top_result.get("metadata", {})
            }

            test_findings.append(finding)

        print(f"   PASS - Formatted {len(test_findings)} findings for scoring")
        for i, finding in enumerate(test_findings, 1):
            query = finding.get("query", "unknown")
            text_len = len(finding.get("finding_text", ""))
            print(f"   [{i}] Query: '{query}' | Text length: {text_len} chars")

    except Exception as e:
        print(f"   FAIL - Formatting error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [5/7] Score findings
    print("[5/7] Scoring findings with RubricV3Scorer...")
    print()

    scored_results = []

    try:
        for i, finding in enumerate(test_findings, 1):
            query = finding.get("query", "unknown")
            print(f"   Scoring finding [{i}/{len(test_findings)}]: '{query}'")

            # Call scorer
            score_result = scorer.score_finding(finding)

            # Validate output structure
            required_fields = ["maturity_level", "maturity_label", "confidence", "dimension_breakdown"]
            missing_fields = [f for f in required_fields if f not in score_result]

            if missing_fields:
                print(f"      FAIL - Missing fields: {missing_fields}")
                return 1

            # Extract and validate
            maturity_level = score_result["maturity_level"]
            maturity_label = score_result["maturity_label"]
            confidence = score_result["confidence"]
            dimension_breakdown = score_result["dimension_breakdown"]

            # Type and range validation
            if not isinstance(maturity_level, (int, float)):
                print(f"      FAIL - maturity_level not numeric: {type(maturity_level)}")
                return 1

            if not (0.0 <= maturity_level <= 5.0):
                print(f"      FAIL - maturity_level out of range: {maturity_level}")
                return 1

            if not isinstance(confidence, (int, float)):
                print(f"      FAIL - confidence not numeric: {type(confidence)}")
                return 1

            if not (0.0 <= confidence <= 1.0):
                print(f"      FAIL - confidence out of range: {confidence}")
                return 1

            # Display results
            print(f"      PASS - Maturity Level: {maturity_level} ({maturity_label})")
            print(f"      Confidence: {confidence:.3f}")
            print(f"      Dimensions: {len(dimension_breakdown)} themes scored")

            # Show top 3 dimension scores
            sorted_dims = sorted(dimension_breakdown.items(), key=lambda x: x[1], reverse=True)
            for dim_code, dim_score in sorted_dims[:3]:
                print(f"        - {dim_code}: {dim_score}")

            # Store result
            scored_results.append({
                "query": query,
                "finding_text": finding.get("finding_text", "")[:200],  # Truncate for storage
                "retrieval_score": finding.get("retrieval_score", 0.0),
                "maturity_level": float(maturity_level),
                "maturity_label": maturity_label,
                "confidence": float(confidence),
                "dimension_breakdown": {k: int(v) for k, v in dimension_breakdown.items()},
                "source_metadata": finding.get("source_metadata", {})
            })

            print()

    except Exception as e:
        print(f"   FAIL - Scoring error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [6/7] Aggregate scores
    print("[6/7] Aggregating scores for Apple 2024...")

    try:
        # Compute average maturity across all findings
        avg_maturity = sum(r["maturity_level"] for r in scored_results) / len(scored_results)
        avg_confidence = sum(r["confidence"] for r in scored_results) / len(scored_results)

        # Most common maturity label
        label_counts = {}
        for r in scored_results:
            label = r["maturity_label"]
            label_counts[label] = label_counts.get(label, 0) + 1
        most_common_label = max(label_counts, key=label_counts.get)

        # Aggregate dimension scores (average across findings)
        aggregated_dimensions = {}
        all_dim_codes = scored_results[0]["dimension_breakdown"].keys()
        for dim_code in all_dim_codes:
            dim_scores = [r["dimension_breakdown"][dim_code] for r in scored_results]
            aggregated_dimensions[dim_code] = sum(dim_scores) / len(dim_scores)

        print(f"   PASS - Aggregation complete")
        print(f"   Average Maturity: {avg_maturity:.2f} ({most_common_label})")
        print(f"   Average Confidence: {avg_confidence:.3f}")
        print(f"   Findings scored: {len(scored_results)}")

    except Exception as e:
        print(f"   FAIL - Aggregation error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # [7/7] Save score results
    print("[7/7] Saving score results...")

    artifacts_dir = project_root / "tasks" / "006-scoring-integration" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    output_file = artifacts_dir / "apple_2024_score.json"

    score_manifest = {
        "task_id": "006-scoring-integration",
        "execution_timestamp": datetime.utcnow().isoformat() + "Z",
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "year": 2024,
        "report_type": "10-K",
        "scoring_method": "RubricV3Scorer",
        "rubric_version": "3.0",
        "findings_scored": len(scored_results),
        "aggregate_score": {
            "maturity_level": round(avg_maturity, 2),
            "maturity_label": most_common_label,
            "confidence": round(avg_confidence, 3),
            "dimension_breakdown": {k: round(v, 2) for k, v in aggregated_dimensions.items()}
        },
        "individual_scores": scored_results,
        "success": True
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(score_manifest, f, indent=2, ensure_ascii=False)

    print(f"   PASS - Results saved to: {output_file}")

    # Success summary
    print()
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print()
    print("Status: PASS - Scoring Integration Working")
    print()
    print(f"Company: Apple Inc. (AAPL) - FY 2024")
    print(f"Report: 10-K (SEC EDGAR)")
    print(f"Findings Scored: {len(scored_results)}")
    print(f"Aggregate Maturity: {avg_maturity:.2f} / 5.0 ({most_common_label})")
    print(f"Aggregate Confidence: {avg_confidence:.3f}")
    print()
    print("Top 3 Dimensions:")
    sorted_agg = sorted(aggregated_dimensions.items(), key=lambda x: x[1], reverse=True)
    for dim_code, dim_score in sorted_agg[:3]:
        print(f"  - {dim_code}: {dim_score:.2f}")
    print()
    print("Notes:")
    print("  - Scoring Method: RubricV3Scorer (keyword-based rubric v3.0)")
    print("  - Evidence Source: Task 005 retrieval results (Apple 10-K chunks)")
    print("  - Maturity Scale: 0 (Minimal) to 5 (Leading)")
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
