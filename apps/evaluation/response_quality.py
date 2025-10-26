"""
Response Quality Evaluation System
Comprehensive framework for assessing the quality of LLM responses in ESG evaluation
"""

import json
import logging
import os
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from pathlib import Path
import hashlib
from collections import defaultdict
import re

# Configure logging
logger = logging.getLogger(__name__)

# Deterministic timestamp support for reproducible audits
def get_audit_timestamp() -> str:
    """Get timestamp with AUDIT_TIME override support for determinism"""
    audit_time = os.getenv("AUDIT_TIME")
    if audit_time:
        return audit_time
    return datetime.now().isoformat()


@dataclass
class QualityMetrics:
    """Quality metrics for response evaluation"""
    # Completeness metrics
    completeness_score: float  # 0-1, how complete is the response
    missing_elements: List[str]  # What required elements are missing
    coverage_ratio: float  # Ratio of themes/topics covered

    # Accuracy metrics
    factual_accuracy: float  # 0-1, based on fact checking
    citation_quality: float  # 0-1, quality of evidence citations
    claim_verification: float  # 0-1, verifiability of claims

    # Consistency metrics
    internal_consistency: float  # 0-1, consistency within response
    cross_response_consistency: float  # 0-1, consistency across responses
    temporal_consistency: float  # 0-1, consistency over time

    # Relevance metrics
    query_relevance: float  # 0-1, relevance to original query
    theme_alignment: float  # 0-1, alignment with ESG themes
    context_appropriateness: float  # 0-1, appropriate for context

    # Confidence calibration
    confidence_calibration: float  # 0-1, how well calibrated is confidence
    uncertainty_handling: float  # 0-1, how well uncertainty is handled

    # Format and structure
    json_validity: bool  # Is the JSON valid
    schema_compliance: float  # 0-1, compliance with expected schema

    # Overall scores
    overall_quality: float  # 0-1, weighted overall score
    reliability_score: float  # 0-1, can we trust this response

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResponseEvaluation:
    """Complete evaluation of a response"""
    response_id: str
    timestamp: datetime
    input_query: str
    response_text: str
    expected_format: str
    metrics: QualityMetrics
    issues_found: List[str]
    recommendations: List[str]
    pass_fail: bool

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class ResponseQualityEvaluator:
    """
    Evaluates the quality of LLM responses for ESG evaluation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.evaluation_history = []
        self.ground_truth = {}
        self.quality_thresholds = self.config.get('thresholds', {})

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for quality evaluation"""
        return {
            'thresholds': {
                'min_completeness': 0.7,
                'min_accuracy': 0.6,
                'min_consistency': 0.7,
                'min_relevance': 0.7,
                'min_overall': 0.65
            },
            'weights': {
                'completeness': 0.2,
                'accuracy': 0.3,
                'consistency': 0.2,
                'relevance': 0.2,
                'format': 0.1
            },
            'strict_mode': False  # If True, all thresholds must be met
        }

    def evaluate_response(
        self,
        response: str,
        query: str,
        expected_format: str = 'json',
        expected_schema: Optional[Dict] = None,
        ground_truth: Optional[Dict] = None,
        previous_responses: Optional[List[str]] = None
    ) -> ResponseEvaluation:
        """
        Evaluate a single response
        """
        # Generate response ID
        response_id = hashlib.md5(f"{query}{response}{datetime.now()}".encode()).hexdigest()[:12]

        # Initialize metrics
        metrics = self._calculate_metrics(
            response, query, expected_format, expected_schema,
            ground_truth, previous_responses
        )

        # Identify issues
        issues = self._identify_issues(metrics)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, issues)

        # Determine pass/fail
        pass_fail = self._determine_pass_fail(metrics)

        # Create evaluation
        evaluation = ResponseEvaluation(
            response_id=response_id,
            timestamp=datetime.fromisoformat(get_audit_timestamp()),
            input_query=query,
            response_text=response,
            expected_format=expected_format,
            metrics=metrics,
            issues_found=issues,
            recommendations=recommendations,
            pass_fail=pass_fail
        )

        # Store in history
        self.evaluation_history.append(evaluation)

        return evaluation

    def _calculate_metrics(
        self,
        response: str,
        query: str,
        expected_format: str,
        expected_schema: Optional[Dict],
        ground_truth: Optional[Dict],
        previous_responses: Optional[List[str]]
    ) -> QualityMetrics:
        """Calculate all quality metrics"""

        # Completeness metrics
        completeness, missing = self._evaluate_completeness(response, expected_schema)
        coverage = self._evaluate_coverage(response, query)

        # Accuracy metrics
        factual_acc = self._evaluate_factual_accuracy(response, ground_truth)
        citation_qual = self._evaluate_citations(response)
        claim_verif = self._evaluate_claim_verification(response)

        # Consistency metrics
        internal_cons = self._evaluate_internal_consistency(response)
        cross_cons = self._evaluate_cross_consistency(response, previous_responses)
        temporal_cons = self._evaluate_temporal_consistency(response, previous_responses)

        # Relevance metrics
        query_rel = self._evaluate_query_relevance(response, query)
        theme_align = self._evaluate_theme_alignment(response)
        context_approp = self._evaluate_context_appropriateness(response, query)

        # Confidence calibration
        conf_calib = self._evaluate_confidence_calibration(response)
        uncert_hand = self._evaluate_uncertainty_handling(response)

        # Format and structure
        json_valid, schema_comp = self._evaluate_format(response, expected_format, expected_schema)

        # Calculate overall scores
        weights = self.config['weights']
        overall = (
            completeness * weights['completeness'] +
            factual_acc * weights['accuracy'] +
            internal_cons * weights['consistency'] +
            query_rel * weights['relevance'] +
            schema_comp * weights['format']
        )

        reliability = (factual_acc + internal_cons + conf_calib) / 3

        return QualityMetrics(
            completeness_score=completeness,
            missing_elements=missing,
            coverage_ratio=coverage,
            factual_accuracy=factual_acc,
            citation_quality=citation_qual,
            claim_verification=claim_verif,
            internal_consistency=internal_cons,
            cross_response_consistency=cross_cons,
            temporal_consistency=temporal_cons,
            query_relevance=query_rel,
            theme_alignment=theme_align,
            context_appropriateness=context_approp,
            confidence_calibration=conf_calib,
            uncertainty_handling=uncert_hand,
            json_validity=json_valid,
            schema_compliance=schema_comp,
            overall_quality=overall,
            reliability_score=reliability
        )

    def _evaluate_completeness(
        self,
        response: str,
        expected_schema: Optional[Dict]
    ) -> Tuple[float, List[str]]:
        """Evaluate response completeness"""
        if not expected_schema:
            # Basic completeness check
            if len(response) < 50:
                return 0.3, ["Response too short"]
            elif len(response) < 200:
                return 0.6, ["Response could be more detailed"]
            else:
                return 0.9, []

        # Check against schema
        missing = []
        try:
            if response.strip().startswith('{'):
                data = json.loads(response)
                for key in expected_schema.keys():
                    if key not in data:
                        missing.append(f"Missing field: {key}")

                completeness = 1.0 - (len(missing) / len(expected_schema))
            else:
                completeness = 0.5  # Not JSON but has content
                missing.append("Response not in expected JSON format")
        except:
            completeness = 0.3
            missing.append("Could not parse response")

        return completeness, missing

    def _evaluate_coverage(self, response: str, query: str) -> float:
        """Evaluate topic coverage"""
        # Extract key terms from query
        query_terms = set(re.findall(r'\b\w+\b', query.lower()))
        response_terms = set(re.findall(r'\b\w+\b', response.lower()))

        if not query_terms:
            return 1.0

        coverage = len(query_terms.intersection(response_terms)) / len(query_terms)
        return min(coverage * 1.5, 1.0)  # Boost slightly but cap at 1.0

    def _evaluate_factual_accuracy(
        self,
        response: str,
        ground_truth: Optional[Dict]
    ) -> float:
        """Evaluate factual accuracy against ground truth"""
        if not ground_truth:
            # Can't verify without ground truth
            return 0.5  # Neutral score

        correct_facts = 0
        total_facts = 0

        # Extract claims from response
        try:
            if response.strip().startswith('{'):
                data = json.loads(response)

                # Check stage values
                if 'stage' in data and 'stage' in ground_truth:
                    total_facts += 1
                    if abs(data['stage'] - ground_truth['stage']) <= 1:
                        correct_facts += 1

                # Check findings
                if 'findings' in data and 'findings' in ground_truth:
                    total_facts += 1
                    if len(data['findings']) > 0:
                        correct_facts += 0.5  # Partial credit for having findings
        except:
            pass

        if total_facts == 0:
            return 0.5

        return correct_facts / total_facts

    def _evaluate_citations(self, response: str) -> float:
        """Evaluate quality of citations/evidence"""
        # Look for quotes, specific numbers, or references
        quote_pattern = r'"[^"]{20,}"'  # Quotes longer than 20 chars
        number_pattern = r'\b\d+\.?\d*%?\b'  # Numbers/percentages

        quotes = len(re.findall(quote_pattern, response))
        numbers = len(re.findall(number_pattern, response))

        # Score based on evidence density
        evidence_score = min((quotes * 0.3 + numbers * 0.1), 1.0)
        return evidence_score

    def _evaluate_claim_verification(self, response: str) -> float:
        """Evaluate verifiability of claims"""
        # Check for specific, verifiable statements
        verifiable_patterns = [
            r'\b\d{4}\b',  # Years
            r'\b\d+%\b',  # Percentages
            r'\$\d+',  # Dollar amounts
            r'\b(increased|decreased|reduced|improved) by \d+',  # Specific changes
        ]

        verifiable_count = sum(
            len(re.findall(pattern, response))
            for pattern in verifiable_patterns
        )

        # Normalize by response length
        words = len(response.split())
        if words == 0:
            return 0.0

        verifiability = min(verifiable_count / (words / 50), 1.0)
        return verifiability

    def _evaluate_internal_consistency(self, response: str) -> float:
        """Evaluate internal consistency of response"""
        try:
            if response.strip().startswith('{'):
                data = json.loads(response)

                # Check consistency between different fields
                consistency_score = 1.0

                # Check stage vs confidence alignment
                if 'stage' in data and 'confidence' in data:
                    stage = data['stage']
                    confidence = data['confidence']

                    # High stage should have reasonable confidence
                    if stage >= 3 and confidence < 0.3:
                        consistency_score -= 0.3
                    # Low stage with very high confidence is suspicious
                    elif stage <= 1 and confidence > 0.9:
                        consistency_score -= 0.2

                # Check findings vs summary alignment
                if 'findings' in data and 'summary' in data:
                    if len(data['findings']) == 0 and 'significant' in str(data['summary']).lower():
                        consistency_score -= 0.3

                return max(consistency_score, 0.0)
        except:
            return 0.5  # Can't parse, neutral score

    def _evaluate_cross_consistency(
        self,
        response: str,
        previous_responses: Optional[List[str]]
    ) -> float:
        """Evaluate consistency across responses"""
        if not previous_responses:
            return 1.0  # No comparison possible

        # Compare key metrics across responses
        try:
            current_data = json.loads(response) if response.strip().startswith('{') else {}

            consistency_scores = []
            for prev in previous_responses:
                try:
                    prev_data = json.loads(prev) if prev.strip().startswith('{') else {}

                    # Compare stages if present
                    if 'stage' in current_data and 'stage' in prev_data:
                        diff = abs(current_data['stage'] - prev_data['stage'])
                        consistency_scores.append(1.0 - (diff / 4))
                except:
                    pass

            if consistency_scores:
                return sum(consistency_scores) / len(consistency_scores)
        except:
            pass

        return 0.7  # Default moderate consistency

    def _evaluate_temporal_consistency(
        self,
        response: str,
        previous_responses: Optional[List[str]]
    ) -> float:
        """Evaluate temporal consistency"""
        # Similar to cross_consistency but with time consideration
        # For now, use same logic
        return self._evaluate_cross_consistency(response, previous_responses)

    def _evaluate_query_relevance(self, response: str, query: str) -> float:
        """Evaluate relevance to query"""
        # Check if response addresses the query
        query_lower = query.lower()
        response_lower = response.lower()

        # Extract key terms from query
        key_terms = ['esg', 'sustainability', 'climate', 'emissions', 'social',
                     'governance', 'environmental', 'carbon', 'diversity', 'water']

        relevant_terms = [term for term in key_terms if term in query_lower]

        if not relevant_terms:
            relevant_terms = query_lower.split()[:5]  # Use first 5 words

        # Check how many relevant terms appear in response
        found_terms = sum(1 for term in relevant_terms if term in response_lower)

        relevance = found_terms / len(relevant_terms) if relevant_terms else 0.5
        return min(relevance * 1.2, 1.0)  # Slight boost but cap at 1.0

    def _evaluate_theme_alignment(self, response: str) -> float:
        """Evaluate alignment with ESG themes"""
        esg_themes = [
            'climate action', 'emissions management', 'energy transition',
            'water stewardship', 'circular economy', 'social equity',
            'governance excellence'
        ]

        response_lower = response.lower()
        themes_mentioned = sum(1 for theme in esg_themes if theme in response_lower)

        # Also check for related terms
        related_terms = [
            'carbon', 'renewable', 'diversity', 'inclusion', 'waste',
            'recycling', 'ethics', 'transparency', 'accountability'
        ]

        related_mentioned = sum(1 for term in related_terms if term in response_lower)

        alignment = min((themes_mentioned * 0.3 + related_mentioned * 0.1), 1.0)
        return alignment

    def _evaluate_context_appropriateness(self, response: str, query: str) -> float:
        """Evaluate if response is appropriate for context"""
        # Check for appropriate formality and structure

        # ESG responses should be professional
        informal_terms = ['lol', 'btw', 'omg', 'gonna', 'wanna']
        informality_count = sum(1 for term in informal_terms if term in response.lower())

        if informality_count > 0:
            return max(0.5 - (informality_count * 0.1), 0.0)

        # Check for appropriate detail level
        word_count = len(response.split())
        if word_count < 20:
            return 0.4  # Too brief
        elif word_count > 2000:
            return 0.7  # Possibly too verbose
        else:
            return 0.9  # Good length

    def _evaluate_confidence_calibration(self, response: str) -> float:
        """Evaluate confidence calibration"""
        try:
            if response.strip().startswith('{'):
                data = json.loads(response)

                if 'confidence' in data:
                    confidence = data['confidence']

                    # Check if confidence is reasonable
                    if 0.0 <= confidence <= 1.0:
                        # Check calibration based on evidence
                        if 'findings' in data:
                            findings_count = len(data.get('findings', []))

                            # More findings should mean higher confidence
                            expected_conf = min(0.3 + (findings_count * 0.15), 0.95)

                            # Calculate calibration error
                            calibration_error = abs(confidence - expected_conf)

                            return 1.0 - calibration_error
                        return 0.7  # Has confidence but can't verify calibration
                    else:
                        return 0.0  # Invalid confidence value
        except:
            pass

        return 0.5  # No confidence info

    def _evaluate_uncertainty_handling(self, response: str) -> float:
        """Evaluate how well uncertainty is handled"""
        uncertainty_terms = [
            'may', 'might', 'could', 'possibly', 'potentially',
            'likely', 'probably', 'uncertain', 'estimated', 'approximately'
        ]

        response_lower = response.lower()
        uncertainty_count = sum(1 for term in uncertainty_terms if term in response_lower)

        # Some uncertainty is good (shows nuance)
        if uncertainty_count == 0:
            return 0.6  # Too certain
        elif uncertainty_count <= 3:
            return 0.9  # Good balance
        elif uncertainty_count <= 6:
            return 0.7  # Maybe too uncertain
        else:
            return 0.4  # Too much uncertainty

    def _evaluate_format(
        self,
        response: str,
        expected_format: str,
        expected_schema: Optional[Dict]
    ) -> Tuple[bool, float]:
        """Evaluate format and structure"""
        if expected_format == 'json':
            try:
                data = json.loads(response)
                json_valid = True

                # Check schema compliance
                if expected_schema:
                    required_keys = set(expected_schema.keys())
                    actual_keys = set(data.keys())

                    missing_keys = required_keys - actual_keys
                    extra_keys = actual_keys - required_keys

                    # Calculate compliance score
                    compliance = 1.0
                    compliance -= (len(missing_keys) * 0.2)  # Penalty for missing
                    compliance -= (len(extra_keys) * 0.05)  # Smaller penalty for extra

                    schema_compliance = max(compliance, 0.0)
                else:
                    schema_compliance = 1.0 if json_valid else 0.0

                return json_valid, schema_compliance

            except json.JSONDecodeError:
                return False, 0.0
        else:
            # Text format
            return True, 0.8  # Default good score for text

    def _identify_issues(self, metrics: QualityMetrics) -> List[str]:
        """Identify specific issues based on metrics"""
        issues = []

        thresholds = self.config['thresholds']

        if metrics.completeness_score < thresholds['min_completeness']:
            issues.append(f"Incomplete response (score: {metrics.completeness_score:.2f})")

        if metrics.factual_accuracy < thresholds['min_accuracy']:
            issues.append(f"Low factual accuracy (score: {metrics.factual_accuracy:.2f})")

        if metrics.internal_consistency < thresholds['min_consistency']:
            issues.append(f"Internal inconsistencies detected (score: {metrics.internal_consistency:.2f})")

        if metrics.query_relevance < thresholds['min_relevance']:
            issues.append(f"Low relevance to query (score: {metrics.query_relevance:.2f})")

        if not metrics.json_validity and metrics.schema_compliance < 0.5:
            issues.append("Invalid format or schema non-compliance")

        if metrics.confidence_calibration < 0.5:
            issues.append("Poor confidence calibration")

        if metrics.missing_elements:
            issues.append(f"Missing elements: {', '.join(metrics.missing_elements[:3])}")

        return issues

    def _generate_recommendations(
        self,
        metrics: QualityMetrics,
        issues: List[str]
    ) -> List[str]:
        """Generate recommendations for improvement"""
        recommendations = []

        if metrics.completeness_score < 0.7:
            recommendations.append("Provide more comprehensive responses with all required fields")

        if metrics.factual_accuracy < 0.6:
            recommendations.append("Verify facts and provide accurate information")

        if metrics.citation_quality < 0.5:
            recommendations.append("Include more specific evidence and citations")

        if metrics.internal_consistency < 0.7:
            recommendations.append("Ensure consistency between different parts of the response")

        if metrics.query_relevance < 0.7:
            recommendations.append("Focus more directly on addressing the specific query")

        if metrics.confidence_calibration < 0.6:
            recommendations.append("Better calibrate confidence scores with available evidence")

        if not metrics.json_validity:
            recommendations.append("Ensure responses are in valid JSON format")

        if metrics.uncertainty_handling < 0.5:
            recommendations.append("Better express uncertainty where appropriate")

        return recommendations

    def _determine_pass_fail(self, metrics: QualityMetrics) -> bool:
        """Determine if response passes quality thresholds"""
        thresholds = self.config['thresholds']

        if self.config.get('strict_mode', False):
            # All thresholds must be met
            return all([
                metrics.completeness_score >= thresholds['min_completeness'],
                metrics.factual_accuracy >= thresholds['min_accuracy'],
                metrics.internal_consistency >= thresholds['min_consistency'],
                metrics.query_relevance >= thresholds['min_relevance'],
                metrics.overall_quality >= thresholds['min_overall']
            ])
        else:
            # Overall quality must meet threshold
            return metrics.overall_quality >= thresholds['min_overall']

    def batch_evaluate(
        self,
        responses: List[Dict[str, Any]],
        save_report: bool = True
    ) -> Dict[str, Any]:
        """Evaluate multiple responses and generate report"""
        evaluations = []

        for response_data in responses:
            evaluation = self.evaluate_response(
                response=response_data.get('response', ''),
                query=response_data.get('query', ''),
                expected_format=response_data.get('format', 'json'),
                expected_schema=response_data.get('schema'),
                ground_truth=response_data.get('ground_truth'),
                previous_responses=response_data.get('previous_responses')
            )
            evaluations.append(evaluation)

        # Generate summary statistics
        summary = self._generate_summary(evaluations)

        # Save report if requested
        if save_report:
            self._save_report(evaluations, summary)

        return {
            'evaluations': [e.to_dict() for e in evaluations],
            'summary': summary
        }

    def _generate_summary(self, evaluations: List[ResponseEvaluation]) -> Dict[str, Any]:
        """Generate summary statistics from evaluations"""
        if not evaluations:
            return {}

        # Calculate averages
        metrics_sum = defaultdict(float)
        metrics_count = defaultdict(int)

        for eval in evaluations:
            for key, value in eval.metrics.to_dict().items():
                if isinstance(value, (int, float)):
                    metrics_sum[key] += value
                    metrics_count[key] += 1

        averages = {
            key: metrics_sum[key] / metrics_count[key]
            for key in metrics_sum
        }

        # Count pass/fail
        passed = sum(1 for e in evaluations if e.pass_fail)
        failed = len(evaluations) - passed

        # Identify common issues
        all_issues = []
        for eval in evaluations:
            all_issues.extend(eval.issues_found)

        issue_counts = defaultdict(int)
        for issue in all_issues:
            issue_counts[issue] += 1

        common_issues = sorted(
            issue_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            'total_evaluations': len(evaluations),
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / len(evaluations) if evaluations else 0,
            'average_metrics': averages,
            'common_issues': common_issues,
            'overall_quality': averages.get('overall_quality', 0),
            'reliability_score': averages.get('reliability_score', 0)
        }

    def _save_report(
        self,
        evaluations: List[ResponseEvaluation],
        summary: Dict[str, Any]
    ):
        """Save evaluation report to file"""
        report_dir = Path("reports/quality_evaluation")
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.fromisoformat(get_audit_timestamp()).strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"quality_report_{timestamp}.json"

        report = {
            'timestamp': get_audit_timestamp(),
            'summary': summary,
            'evaluations': [e.to_dict() for e in evaluations]
        }

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Quality report saved to {report_file}")

    def set_ground_truth(self, ground_truth_data: Dict[str, Any]):
        """Set ground truth for evaluation"""
        self.ground_truth.update(ground_truth_data)

    def get_historical_performance(self) -> Dict[str, Any]:
        """Get historical performance metrics"""
        if not self.evaluation_history:
            return {}

        # Group by time periods
        recent = self.evaluation_history[-10:]
        all_time = self.evaluation_history

        return {
            'recent_performance': self._generate_summary(recent),
            'all_time_performance': self._generate_summary(all_time),
            'total_evaluations': len(all_time),
            'improvement_trend': self._calculate_trend(all_time)
        }

    def _calculate_trend(self, evaluations: List[ResponseEvaluation]) -> str:
        """Calculate performance trend"""
        if len(evaluations) < 2:
            return "insufficient_data"

        # Compare first half to second half
        mid = len(evaluations) // 2
        first_half = evaluations[:mid]
        second_half = evaluations[mid:]

        first_avg = sum(e.metrics.overall_quality for e in first_half) / len(first_half)
        second_avg = sum(e.metrics.overall_quality for e in second_half) / len(second_half)

        improvement = second_avg - first_avg

        if improvement > 0.1:
            return "improving"
        elif improvement < -0.1:
            return "declining"
        else:
            return "stable"


# Export classes
__all__ = ['ResponseQualityEvaluator', 'QualityMetrics', 'ResponseEvaluation']