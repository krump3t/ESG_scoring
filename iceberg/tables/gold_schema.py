"""
Gold Layer Schema - Iceberg Table for ESG Maturity Scores
Critical Path: Scored findings with confidence and evidence links
"""
from typing import Dict, Any, List, Optional
import logging
import pyarrow as pa  # type: ignore
from datetime import datetime

logger = logging.getLogger(__name__)


class GoldSchema:
    """
    Gold layer Iceberg table schema for ESG maturity scores

    Features:
    - Maturity scores with confidence intervals
    - Evidence links to AstraDB manifests
    - Snapshot IDs for reproducibility
    - Historical tracking via time-travel
    """

    # Gold layer schema - esg_scores table
    SCHEMA = pa.schema([
        # Primary identifiers
        ('score_id', pa.string()),  # UUID for score record
        ('finding_id', pa.string()),  # Reference to silver layer finding

        # Organization and classification
        ('org_id', pa.string()),  # Organization identifier
        ('year', pa.int32()),  # Reporting year
        ('theme', pa.string()),  # ESG theme
        ('framework', pa.string()),  # Framework (SBTi/TCFD/GHG/etc)
        ('rubric_id', pa.string()),  # Rubric version used

        # Maturity scoring - 7 Dimensions per Rubric v3.0
        # TSP - Target Setting & Planning (0-4)
        ('tsp_score', pa.int32()),
        ('tsp_evidence', pa.large_string()),
        ('tsp_confidence', pa.float64()),
        ('tsp_stage_descriptor', pa.string()),

        # OSP - Operational Structure & Processes (0-4)
        ('osp_score', pa.int32()),
        ('osp_evidence', pa.large_string()),
        ('osp_confidence', pa.float64()),
        ('osp_stage_descriptor', pa.string()),

        # DM - Data Maturity (0-4)
        ('dm_score', pa.int32()),
        ('dm_evidence', pa.large_string()),
        ('dm_confidence', pa.float64()),
        ('dm_stage_descriptor', pa.string()),

        # GHG - GHG Accounting (0-4)
        ('ghg_score', pa.int32()),
        ('ghg_evidence', pa.large_string()),
        ('ghg_confidence', pa.float64()),
        ('ghg_stage_descriptor', pa.string()),

        # RD - Reporting & Disclosure (0-4)
        ('rd_score', pa.int32()),
        ('rd_evidence', pa.large_string()),
        ('rd_confidence', pa.float64()),
        ('rd_stage_descriptor', pa.string()),

        # EI - Energy Intelligence (0-4)
        ('ei_score', pa.int32()),
        ('ei_evidence', pa.large_string()),
        ('ei_confidence', pa.float64()),
        ('ei_stage_descriptor', pa.string()),

        # RMM - Risk Management & Mitigation (0-4)
        ('rmm_score', pa.int32()),
        ('rmm_evidence', pa.large_string()),
        ('rmm_confidence', pa.float64()),
        ('rmm_stage_descriptor', pa.string()),

        # Overall Maturity (average of 7 dimensions)
        ('overall_maturity', pa.float64()),  # 0.0-4.0 (average of 7 scores)
        ('maturity_label', pa.string()),  # Nascent/Emerging/Established/Advanced/Leading
        ('overall_confidence', pa.float64()),  # Average confidence across dimensions

        # Confidence intervals
        ('confidence_lower', pa.float64()),  # Lower bound (e.g., 95% CI)
        ('confidence_upper', pa.float64()),  # Upper bound

        # Evidence and reasoning
        ('evidence_summary', pa.large_string()),  # Key evidence points
        ('reasoning', pa.large_string()),  # LLM reasoning text
        ('evidence_manifest_id', pa.string()),  # AstraDB manifest UUID

        # Model metadata
        ('model_name', pa.string()),  # LLM model used
        ('model_temperature', pa.float64()),  # Temperature parameter
        ('model_tokens_used', pa.int32()),  # Token count

        # Scoring metadata
        ('scoring_timestamp', pa.timestamp('us')),
        ('scorer_version', pa.string()),  # Scoring agent version

        # Iceberg snapshot tracking
        ('silver_snapshot_id', pa.int64()),  # Silver layer snapshot used
        ('gold_snapshot_id', pa.int64()),  # Gold layer snapshot after insert

        # Iceberg metadata
        ('_inserted_at', pa.timestamp('us')),
        ('_updated_at', pa.timestamp('us')),
    ])

    # Overall Maturity mapping per Rubric v3.0
    MATURITY_LEVELS = {
        (0.0, 0.9): 'Nascent',
        (1.0, 1.9): 'Emerging',
        (2.0, 2.9): 'Established',
        (3.0, 3.5): 'Advanced',
        (3.6, 4.0): 'Leading'
    }

    @staticmethod
    def overall_maturity_to_label(overall_score: float) -> str:
        """
        Convert overall maturity score to label per rubric v3.0

        Args:
            overall_score: Average score across 7 dimensions (0.0-4.0)

        Returns:
            Maturity label string
        """
        if overall_score < 1.0:
            return 'Nascent'
        elif overall_score < 2.0:
            return 'Emerging'
        elif overall_score < 3.0:
            return 'Established'
        elif overall_score < 3.6:
            return 'Advanced'
        else:
            return 'Leading'

    @staticmethod
    def validate_score(score: Dict[str, Any]) -> bool:
        """
        Validate score record conforms to gold schema (7-dimensional rubric v3.0)

        Args:
            score: Score data dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'score_id', 'finding_id', 'org_id', 'year',
            'theme', 'rubric_id',
            # 7 dimension scores (0-4 each)
            'tsp_score', 'osp_score', 'dm_score', 'ghg_score',
            'rd_score', 'ei_score', 'rmm_score',
            # Overall maturity
            'overall_maturity', 'maturity_label'
        ]

        for field in required_fields:
            if field not in score:
                logger.error(f"Missing required field: {field}")
                return False

        # Type and range validation
        try:
            assert isinstance(score['org_id'], str)
            assert isinstance(score['year'], int)

            # Validate 7 dimension scores (0-4 range per rubric v3.0)
            for dim in ['tsp', 'osp', 'dm', 'ghg', 'rd', 'ei', 'rmm']:
                score_field = f'{dim}_score'
                assert isinstance(score[score_field], int), f"{score_field} must be int"
                assert 0 <= score[score_field] <= 4, f"{score_field} must be 0-4, got {score[score_field]}"

                # Validate confidence if present
                conf_field = f'{dim}_confidence'
                if conf_field in score:
                    assert isinstance(score[conf_field], (int, float))
                    assert 0.0 <= score[conf_field] <= 1.0

            # Validate overall maturity (0.0-4.0 range)
            assert isinstance(score['overall_maturity'], (int, float))
            assert 0.0 <= score['overall_maturity'] <= 4.0

            # Validate overall confidence if present
            if 'overall_confidence' in score:
                assert isinstance(score['overall_confidence'], (int, float))
                assert 0.0 <= score['overall_confidence'] <= 1.0

            # Confidence intervals if present
            if 'confidence_lower' in score:
                assert 0.0 <= score['confidence_lower'] <= 1.0
                assert score['confidence_lower'] <= score.get('overall_confidence', 1.0)
            if 'confidence_upper' in score:
                assert 0.0 <= score['confidence_upper'] <= 1.0
                assert score.get('overall_confidence', 0.0) <= score['confidence_upper']

            return True
        except (AssertionError, TypeError) as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    @staticmethod
    def maturity_level_to_label(level: int) -> str:
        """
        Convert maturity level to label (legacy 0-5 scale)

        Deprecated: Use overall_maturity_to_label for rubric v3.0 (0.0-4.0 scale)

        Args:
            level: Maturity level (0-5)

        Returns:
            Maturity label string
        """
        # Legacy mapping for 0-5 scale
        legacy_mapping = {
            0: 'Nascent',
            1: 'Emerging',
            2: 'Emerging',
            3: 'Established',
            4: 'Advanced',
            5: 'Leading'
        }
        return legacy_mapping.get(level, 'Unknown')

    @staticmethod
    def prepare_score_data(scores: List[Dict[str, Any]],
                           silver_snapshot_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Prepare score records for insertion

        Args:
            scores: List of score dictionaries
            silver_snapshot_id: Silver layer snapshot ID used

        Returns:
            Prepared scores with timestamps and validation
        """
        now = datetime.utcnow()
        prepared = []

        for score in scores:
            # Validate
            if not GoldSchema.validate_score(score):
                logger.warning(f"Skipping invalid score: {score.get('score_id', 'unknown')}")
                continue

            # Add maturity label if missing
            if 'maturity_label' not in score:
                score['maturity_label'] = GoldSchema.overall_maturity_to_label(
                    score['overall_maturity']
                )

            # Add Iceberg metadata
            score['_inserted_at'] = now
            score['_updated_at'] = now

            # Add scoring timestamp if missing
            if 'scoring_timestamp' not in score:
                score['scoring_timestamp'] = now

            # Add silver snapshot ID
            if silver_snapshot_id is not None:
                score['silver_snapshot_id'] = silver_snapshot_id

            prepared.append(score)

        logger.info(f"Prepared {len(prepared)}/{len(scores)} scores for insertion")
        return prepared

    @staticmethod
    def generate_partition_spec() -> Dict[str, str]:
        """
        Generate Iceberg partition specification for gold layer

        Returns:
            Partition spec for hidden partitioning
        """
        return {
            'org_id': 'identity',  # Partition by organization
            'year': 'identity',  # Partition by year
            'theme': 'identity',  # Partition by ESG theme
            'rubric_id': 'identity'  # Partition by rubric version
        }

    @staticmethod
    def get_table_properties() -> Dict[str, str]:
        """
        Get Iceberg table properties for gold layer

        Returns:
            Table properties dict
        """
        return {
            'format-version': '2',
            'write.parquet.compression-codec': 'zstd',
            'write.parquet.compression-level': '3',
            'write.metadata.compression-codec': 'gzip',
            'commit.manifest.min-count-to-merge': '3',
            'commit.manifest-merge.enabled': 'true',
            'history.expire.max-snapshot-age-ms': str(90 * 24 * 60 * 60 * 1000),  # 90 days
            'write.metadata.delete-after-commit.enabled': 'false',  # Keep for time-travel
        }

    @staticmethod
    def calculate_confidence_interval(confidence: float,
                                      sample_size: int = 1,
                                      alpha: float = 0.05) -> tuple[float, float]:
        """
        Calculate confidence interval for maturity score

        Args:
            confidence: Point estimate of confidence
            sample_size: Number of evidence samples
            alpha: Significance level (default 0.05 for 95% CI)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        import math

        # Simple approach: use Wilson score interval for proportions
        # For n=1, use conservative approach
        if sample_size <= 1:
            margin = 0.15  # Conservative ±15%
        else:
            # Standard error approximation
            se = math.sqrt(confidence * (1 - confidence) / sample_size)
            z = 1.96  # 95% CI
            margin = z * se

        lower = max(0.0, confidence - margin)
        upper = min(1.0, confidence + margin)

        return (lower, upper)
