"""
Score Silver Evidence → Gold Maturity Scores
Uses real RubricV3Scorer with actual evidence from Silver layer
NO MOCKS - Authentic computation only
"""
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import duckdb

# Add project root to path
PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agents.scoring.rubric_v3_scorer import RubricV3Scorer, DimensionScore
from libs.utils.clock import get_clock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

clock = get_clock()


class SilverToGoldScorer:
    """
    Score Silver evidence to produce Gold maturity assessments

    Pipeline: Silver Evidence → RubricV3Scorer → Gold Scores
    """

    def __init__(
        self,
        silver_path: Path = None,
        gold_path: Path = None
    ):
        """Initialize scorer with paths"""
        self.silver_path = silver_path or (PROJECT_ROOT / "data" / "silver")
        self.gold_path = gold_path or (PROJECT_ROOT / "data" / "gold")

        self.scorer = RubricV3Scorer()
        self.run_id = f"scoring-{clock.now().strftime('%Y%m%d-%H%M%S')}"

        logger.info(f"Initialized SilverToGoldScorer (run_id: {self.run_id})")
        logger.info(f"  Silver: {self.silver_path}")
        logger.info(f"  Gold: {self.gold_path}")

    def read_silver_evidence(
        self,
        org_id: str,
        year: int,
        theme: str = None
    ) -> List[Dict[str, Any]]:
        """
        Read Silver evidence from Parquet files

        Args:
            org_id: Organization (e.g., "MSFT")
            year: Fiscal year
            theme: Optional theme filter

        Returns:
            List of evidence dictionaries
        """
        theme_pattern = f"theme={theme}" if theme else "theme=*"
        pattern = f"org_id={org_id}/year={year}/{theme_pattern}/*.parquet"
        full_pattern = self.silver_path / pattern

        logger.info(f"Reading Silver evidence: {full_pattern}")

        try:
            con = duckdb.connect(":memory:")
            query = f"SELECT * FROM read_parquet('{self.silver_path}/{pattern}')"
            result = con.execute(query).fetchall()
            columns = [desc[0] for desc in con.description]

            evidence_list = []
            for row in result:
                evidence = dict(zip(columns, row))
                evidence_list.append(evidence)

            con.close()

            logger.info(f"Found {len(evidence_list)} evidence items")
            return evidence_list

        except Exception as e:
            logger.error(f"Error reading Silver evidence: {e}")
            return []

    def score_evidence_batch(
        self,
        evidence_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Score batch of evidence using RubricV3Scorer

        Args:
            evidence_list: List of evidence dictionaries

        Returns:
            List of score dictionaries
        """
        if not evidence_list:
            logger.warning("No evidence to score")
            return []

        scores = []

        for evidence in evidence_list:
            # Prepare finding dict for scorer
            # Evidence model: evidence_id, org_id, year, theme, extract_30w, confidence, etc.
            # Scorer expects: finding_text, theme, framework
            finding = {
                'finding_text': evidence.get('extract_30w', ''),
                'theme': evidence.get('theme', ''),
                'framework': '',  # Not available in evidence
                'evidence_id': evidence.get('evidence_id', ''),
                'org_id': evidence.get('org_id', ''),
                'year': evidence.get('year', 0),
                'doc_id': evidence.get('doc_id', ''),
                'page_no': evidence.get('page_no', 0),
                'confidence': evidence.get('confidence', 0.0)
            }

            # Score all dimensions
            dimension_scores = self.scorer.score_all_dimensions(finding)

            # Create score record
            # Note: RubricV3Scorer returns scores per dimension (TSP, OSP, DM, GHG, RD, EI, RMM)
            # For simplicity, use the theme-specific dimension as primary score
            theme_code = evidence.get('theme', '')

            # Map theme to primary dimension
            # GHG → GHG, TSP → TSP, OSP → OSP, etc.
            primary_dimension = dimension_scores.get(theme_code)

            if not primary_dimension:
                # Fallback: use first non-zero score
                for dim_score in dimension_scores.values():
                    if dim_score.score > 0:
                        primary_dimension = dim_score
                        break

            if not primary_dimension:
                # No scores found - create default
                primary_dimension = DimensionScore(
                    score=0,
                    evidence="No evidence matched scoring patterns",
                    confidence=0.0,
                    stage_descriptor="No evidence found"
                )

            score_record = {
                'score_id': f"score-{evidence.get('evidence_id', 'unknown')}",
                'org_id': evidence.get('org_id', ''),
                'year': evidence.get('year', 0),
                'theme': evidence.get('theme', ''),
                'maturity_level': primary_dimension.score,
                'maturity_label': primary_dimension.stage_descriptor,
                'confidence': primary_dimension.confidence,
                'evidence_text': primary_dimension.evidence[:500],  # Truncate
                'evidence_id': evidence.get('evidence_id', ''),
                'doc_id': evidence.get('doc_id', ''),
                'snapshot_id': evidence.get('snapshot_id', ''),
                'run_id': self.run_id,
                'scored_at': clock.now().isoformat(),
                # Store all dimension scores as JSON-compatible dict
                'all_dimensions': {
                    dim: {
                        'score': dim_score.score,
                        'confidence': dim_score.confidence,
                        'stage': dim_score.stage_descriptor
                    }
                    for dim, dim_score in dimension_scores.items()
                }
            }

            scores.append(score_record)

            logger.debug(f"Scored evidence {evidence.get('evidence_id')[:8]}: "
                        f"theme={score_record['theme']}, "
                        f"maturity={score_record['maturity_level']}, "
                        f"conf={score_record['confidence']:.2f}")

        logger.info(f"Scored {len(scores)} evidence items")
        return scores

    def write_gold_scores(
        self,
        org_id: str,
        year: int,
        theme: str,
        scores: List[Dict[str, Any]]
    ) -> bool:
        """
        Write scores to Gold Parquet files

        Args:
            org_id: Organization
            year: Fiscal year
            theme: Theme
            scores: List of score dictionaries

        Returns:
            True if successful
        """
        import pyarrow as pa
        import pyarrow.parquet as pq

        if not scores:
            logger.warning("No scores to write")
            return False

        # Create partition path
        partition_path = self.gold_path / f"org_id={org_id}" / f"year={year}" / f"theme={theme}"
        partition_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = clock.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scores-{timestamp}.parquet"
        file_path = partition_path / filename

        logger.info(f"Writing {len(scores)} scores to {file_path}")

        try:
            # Convert all_dimensions to JSON string (PyArrow doesn't support nested structs well)
            for score in scores:
                import json
                if 'all_dimensions' in score:
                    score['all_dimensions_json'] = json.dumps(score['all_dimensions'])
                    del score['all_dimensions']

            # Convert to PyArrow table
            table = pa.Table.from_pylist(scores)

            # Write Parquet
            pq.write_table(table, file_path)

            logger.info(f"Successfully wrote Gold scores: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error writing Gold scores: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_scoring_pipeline(
        self,
        org_id: str,
        year: int
    ) -> Dict[str, Any]:
        """
        Run complete scoring pipeline for org/year

        Args:
            org_id: Organization (e.g., "MSFT")
            year: Fiscal year

        Returns:
            Results dictionary
        """
        logger.info("="*80)
        logger.info(f"SCORING PIPELINE: {org_id} {year}")
        logger.info("="*80)

        results = {
            'run_id': self.run_id,
            'org_id': org_id,
            'year': year,
            'themes_scored': [],
            'total_scores': 0,
            'status': 'UNKNOWN'
        }

        # Read all Silver evidence (all themes)
        all_evidence = self.read_silver_evidence(org_id, year)

        if not all_evidence:
            logger.error(f"No Silver evidence found for {org_id}/{year}")
            results['status'] = 'NO_DATA'
            return results

        # Group by theme
        evidence_by_theme = {}
        for evidence in all_evidence:
            theme = evidence.get('theme', 'Unknown')
            if theme not in evidence_by_theme:
                evidence_by_theme[theme] = []
            evidence_by_theme[theme].append(evidence)

        logger.info(f"Evidence grouped into {len(evidence_by_theme)} themes: {list(evidence_by_theme.keys())}")

        # Score each theme
        for theme, evidence_list in evidence_by_theme.items():
            logger.info(f"\nScoring theme: {theme} ({len(evidence_list)} evidence items)")

            scores = self.score_evidence_batch(evidence_list)

            if scores:
                # Write to Gold
                success = self.write_gold_scores(org_id, year, theme, scores)

                if success:
                    results['themes_scored'].append(theme)
                    results['total_scores'] += len(scores)

                    logger.info(f"  [OK] Wrote {len(scores)} scores for {theme}")

        if results['total_scores'] > 0:
            results['status'] = 'SUCCESS'
            logger.info(f"\n[SUCCESS] Scored {results['total_scores']} items across {len(results['themes_scored'])} themes")
        else:
            results['status'] = 'FAILED'
            logger.error("\n[FAILED] No scores generated")

        return results


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Score Silver evidence to Gold maturity scores")
    parser.add_argument("--org-id", required=True, help="Organization ID (e.g., MSFT)")
    parser.add_argument("--year", type=int, required=True, help="Fiscal year (e.g., 2023)")

    args = parser.parse_args()

    scorer = SilverToGoldScorer()
    results = scorer.run_scoring_pipeline(args.org_id, args.year)

    print("\n" + "="*80)
    print("SCORING RESULTS")
    print("="*80)
    print(f"Status: {results['status']}")
    print(f"Run ID: {results['run_id']}")
    print(f"Organization: {results['org_id']} ({results['year']})")
    print(f"Themes Scored: {', '.join(results['themes_scored']) if results['themes_scored'] else 'None'}")
    print(f"Total Scores: {results['total_scores']}")

    if results['status'] == 'SUCCESS':
        print("\n[SUCCESS] Gold scores written successfully!")
        sys.exit(0)
    else:
        print("\n[FAILED] Scoring pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
