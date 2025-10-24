"""
Phase 5: Integration Validator

Validates data integrity, completeness, and correctness across phase boundaries.

Validation Checks:
- SHA256 hashes at phase boundaries (SC2)
- Field completeness ≥95% (SC3)
- Ground truth match ±1% tolerance (SC4)
- Performance <60 seconds (SC5)
"""

import hashlib
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

from agents.extraction.models import ESGMetrics


logger = logging.getLogger(__name__)


# ============================================================================
# Validation Result
# ============================================================================

@dataclass
class ValidationResult:
    """Result of validation check."""

    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """String representation."""
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.message}"


# ============================================================================
# Integration Validator
# ============================================================================

class IntegrationValidator:
    """Validates end-to-end pipeline output."""

    def __init__(self):
        """Initialize validator."""
        self.results: list[ValidationResult] = []
        self.logger = logger

    def validate_sha256(
        self,
        data: Any,
        expected_hash: str,
        phase_name: str,
    ) -> ValidationResult:
        """Validate SHA256 hash at phase boundary (SC2).

        Args:
            data: Data object to hash (dict, bytes, str, etc.)
            expected_hash: Expected SHA256 hash (hex string)
            phase_name: Phase name for logging

        Returns:
            ValidationResult with pass/fail status
        """
        try:
            # Compute SHA256 of data
            if isinstance(data, dict):
                # Hash JSON representation
                data_bytes = str(data).encode("utf-8")
            elif isinstance(data, str):
                data_bytes = data.encode("utf-8")
            elif isinstance(data, bytes):
                data_bytes = data
            else:
                return ValidationResult(
                    name=f"SHA256 Validation ({phase_name})",
                    passed=False,
                    message=f"Cannot hash type {type(data).__name__}",
                )

            computed_hash = hashlib.sha256(data_bytes).hexdigest()

            # Compare hashes
            passed = computed_hash.lower() == expected_hash.lower()

            result = ValidationResult(
                name=f"SHA256 Validation ({phase_name})",
                passed=passed,
                message=(
                    f"Hash match" if passed
                    else f"Hash mismatch: expected {expected_hash[:16]}..., got {computed_hash[:16]}..."
                ),
                details={
                    "phase": phase_name,
                    "expected": expected_hash,
                    "computed": computed_hash,
                },
            )

            self.results.append(result)
            self.logger.info(str(result))
            return result

        except Exception as e:
            result = ValidationResult(
                name=f"SHA256 Validation ({phase_name})",
                passed=False,
                message=f"Error computing hash: {str(e)}",
            )
            self.results.append(result)
            self.logger.error(str(result))
            return result

    def validate_completeness(
        self,
        metrics: ESGMetrics,
        min_completion: float = 0.95,
    ) -> ValidationResult:
        """Validate field completeness (SC3).

        Counts non-null fields and checks if ≥min_completion%.

        Args:
            metrics: ESGMetrics instance
            min_completion: Minimum completion percentage (default 0.95)

        Returns:
            ValidationResult with pass/fail status
        """
        try:
            if not isinstance(metrics, ESGMetrics):
                return ValidationResult(
                    name="Field Completeness (SC3)",
                    passed=False,
                    message=f"Expected ESGMetrics, got {type(metrics).__name__}",
                )

            # Get all fields from ESGMetrics
            fields = [
                metrics.company_name,
                metrics.cik,
                metrics.fiscal_year,
                metrics.assets,
                metrics.liabilities,
                metrics.net_income,
                getattr(metrics, "total_revenue", None),
                getattr(metrics, "operating_income", None),
                getattr(metrics, "cash_flow", None),
                getattr(metrics, "employees", None),
                getattr(metrics, "energy_consumption", None),
                getattr(metrics, "carbon_emissions", None),
                getattr(metrics, "waste_generated", None),
                getattr(metrics, "water_usage", None),
            ]

            total_fields = len(fields)
            populated_fields = sum(1 for f in fields if f is not None)
            completion_pct = populated_fields / total_fields

            passed = completion_pct >= min_completion

            result = ValidationResult(
                name="Field Completeness (SC3)",
                passed=passed,
                message=(
                    f"Completeness {completion_pct:.1%} >= {min_completion:.1%} ✓"
                    if passed else
                    f"Completeness {completion_pct:.1%} < {min_completion:.1%} ✗"
                ),
                details={
                    "total_fields": total_fields,
                    "populated_fields": populated_fields,
                    "completion_pct": completion_pct,
                    "min_completion": min_completion,
                },
            )

            self.results.append(result)
            self.logger.info(str(result))
            return result

        except Exception as e:
            result = ValidationResult(
                name="Field Completeness (SC3)",
                passed=False,
                message=f"Error validating completeness: {str(e)}",
            )
            self.results.append(result)
            self.logger.error(str(result))
            return result

    def validate_ground_truth(
        self,
        metrics: ESGMetrics,
        ground_truth: Dict[str, float],
        tolerance: float = 0.01,
    ) -> ValidationResult:
        """Validate metrics match ground truth (SC4).

        Checks each metric in ground_truth with ±tolerance%.

        Args:
            metrics: Extracted ESGMetrics
            ground_truth: Dict with expected values {field: value}
            tolerance: Tolerance as decimal (0.01 = ±1%)

        Returns:
            ValidationResult with pass/fail status
        """
        try:
            if not isinstance(metrics, ESGMetrics):
                return ValidationResult(
                    name="Ground Truth Validation (SC4)",
                    passed=False,
                    message=f"Expected ESGMetrics, got {type(metrics).__name__}",
                )

            if not ground_truth:
                return ValidationResult(
                    name="Ground Truth Validation (SC4)",
                    passed=False,
                    message="Ground truth dict is empty",
                )

            mismatches = []

            for field, expected_value in ground_truth.items():
                # Skip non-numeric fields
                if field in ["cik", "fiscal_year", "company_name", "source"]:
                    continue

                extracted_value = getattr(metrics, field, None)

                if extracted_value is None:
                    mismatches.append(f"{field}: expected {expected_value}, got None")
                    continue

                # Compute relative error
                if expected_value != 0:
                    relative_error = abs(extracted_value - expected_value) / expected_value
                else:
                    relative_error = abs(extracted_value - expected_value)

                # Check tolerance
                if relative_error > tolerance:
                    mismatches.append(
                        f"{field}: error {relative_error:.2%} exceeds ±{tolerance:.1%} "
                        f"(expected {expected_value}, got {extracted_value})"
                    )

            passed = len(mismatches) == 0

            result = ValidationResult(
                name="Ground Truth Validation (SC4)",
                passed=passed,
                message=(
                    f"All metrics within ±{tolerance:.1%} tolerance ✓"
                    if passed else
                    f"{len(mismatches)} metric(s) failed: {'; '.join(mismatches[:2])}"
                ),
                details={
                    "tolerance": tolerance,
                    "mismatches": mismatches,
                    "fields_validated": len([f for f in ground_truth if f not in ["cik", "fiscal_year", "company_name"]]),
                },
            )

            self.results.append(result)
            self.logger.info(str(result))
            return result

        except Exception as e:
            result = ValidationResult(
                name="Ground Truth Validation (SC4)",
                passed=False,
                message=f"Error validating ground truth: {str(e)}",
            )
            self.results.append(result)
            self.logger.error(str(result))
            return result

    def validate_performance(
        self,
        start_time: float,
        end_time: float,
        max_latency: float = 60.0,
    ) -> ValidationResult:
        """Validate latency is within target (SC5).

        Args:
            start_time: Pipeline start timestamp (seconds)
            end_time: Pipeline end timestamp (seconds)
            max_latency: Maximum allowed latency (default 60.0 seconds)

        Returns:
            ValidationResult with pass/fail status
        """
        try:
            latency = end_time - start_time

            passed = latency < max_latency

            result = ValidationResult(
                name="Performance Validation (SC5)",
                passed=passed,
                message=(
                    f"Latency {latency:.2f}s < {max_latency}s target ✓"
                    if passed else
                    f"Latency {latency:.2f}s >= {max_latency}s target ✗"
                ),
                details={
                    "latency_seconds": latency,
                    "max_latency_seconds": max_latency,
                },
            )

            self.results.append(result)
            self.logger.info(str(result))
            return result

        except Exception as e:
            result = ValidationResult(
                name="Performance Validation (SC5)",
                passed=False,
                message=f"Error validating performance: {str(e)}",
            )
            self.results.append(result)
            self.logger.error(str(result))
            return result

    def validate_all(
        self,
        metrics: ESGMetrics,
        ground_truth: Dict[str, float],
        start_time: float,
        end_time: float,
    ) -> bool:
        """Run all validations (SC2-SC5).

        Args:
            metrics: Extracted ESGMetrics
            ground_truth: Expected values
            start_time: Pipeline start timestamp
            end_time: Pipeline end timestamp

        Returns:
            True if all validations pass, False otherwise
        """
        results = [
            self.validate_completeness(metrics),
            self.validate_ground_truth(metrics, ground_truth),
            self.validate_performance(start_time, end_time),
        ]

        all_passed = all(r.passed for r in results)

        self.logger.info(
            f"\nValidation Summary:\n"
            f"  Passed: {sum(r.passed for r in results)}/{len(results)}"
        )

        return all_passed

    def get_results(self) -> list[ValidationResult]:
        """Get all validation results.

        Returns:
            List of ValidationResult objects
        """
        return self.results

    def clear_results(self) -> None:
        """Clear validation results."""
        self.results = []
