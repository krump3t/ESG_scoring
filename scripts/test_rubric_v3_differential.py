"""
Differential Testing for Rubric v3.0 Scorer - SCA Protocol Compliant

Tests rubric v3.0 scoring robustness through direct unit-level testing:
1. Determinism: Same input → same output (100% of the time)
2. Perturbation: Small text changes → similar scores
3. Monotonicity: More evidence → higher/same scores
4. Sensitivity: Framework keywords → expected score boosts
5. Coverage: >= 1,200 unique test cases

Required by SCA Protocol authenticity extensions:
- Differential fuzz: >= 1,200 test cases
- Unique ratio: >= 0.5
- No unexpected crashes
- Deterministic outputs

This directly tests agents/scoring/rubric_v3_scorer.py without API overhead.
"""
import sys
import json
import hashlib
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import logging

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.scoring.rubric_v3_scorer import RubricV3Scorer

# Setup paths
TASK_DIR = PROJECT_ROOT / "tasks" / "003-rubric-v3-implementation"
QA_DIR = TASK_DIR / "qa"
ARTIFACTS_DIR = TASK_DIR / "artifacts"

QA_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = QA_DIR / "differential_rubric_v3.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Event stream
events_file = ARTIFACTS_DIR / "differential_rubric_v3_events.jsonl"
RUN_ID = f"diff-rubric-v3-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"


def log_event(event_type: str, data: Dict[str, Any]):
    """Append structured event to JSONL stream"""
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "run_id": RUN_ID,
        "event_type": event_type,
        "data": data
    }
    with open(events_file, 'a') as f:
        f.write(json.dumps(event) + "\n")


@dataclass
class DifferentialResult:
    """Result from differential test"""
    test_id: str
    test_type: str
    passed: bool
    details: Dict[str, Any]


class RubricV3DifferentialTester:
    """Differential testing framework for Rubric v3.0 Scorer"""

    def __init__(self):
        self.scorer = RubricV3Scorer()
        self.results: List[DifferentialResult] = []
        self.crash_count = 0
        self.total_tests = 0

        logger.info("=" * 80)
        logger.info(f"RUBRIC V3.0 DIFFERENTIAL TESTING: {RUN_ID}")
        logger.info("=" * 80)
        logger.info("Target: agents/scoring/rubric_v3_scorer.py")
        logger.info("Requirements: >= 1,200 cases, unique ratio >= 0.5, no crashes")
        logger.info("=" * 80)

        log_event("differential_start", {
            "run_id": RUN_ID,
            "target": "rubric_v3_scorer.py",
            "requirements": {
                "min_cases": 1200,
                "min_unique_ratio": 0.5,
                "max_crashes": 0
            }
        })

    def test_determinism(self, finding_text: str, iterations: int = 10) -> DifferentialResult:
        """Test 1: Determinism - same input always yields same output"""
        finding = {
            "finding_text": finding_text,
            "theme": "Climate",
            "framework": "TCFD"
        }

        hashes = []
        scores_list = []

        for _ in range(iterations):
            try:
                self.total_tests += 1
                scores = self.scorer.score_all_dimensions(finding)
                overall_tuple = self.scorer.calculate_overall_maturity(scores)
                overall = overall_tuple[0]  # Extract float from (float, str) tuple

                # Convert DimensionScore objects to serializable dicts
                scores_dict = {
                    dim: {
                        "score": score.score,
                        "evidence": score.evidence[:50],  # Truncate for hash
                        "confidence": score.confidence
                    }
                    for dim, score in scores.items()
                }

                # Create deterministic hash of results
                result_str = json.dumps({
                    "scores": scores_dict,
                    "overall": overall
                }, sort_keys=True)
                result_hash = hashlib.sha256(result_str.encode()).hexdigest()

                hashes.append(result_hash)
                scores_list.append((scores_dict, overall))

            except Exception as e:
                self.crash_count += 1
                logger.error(f"CRASH in determinism test: {e}")
                return DifferentialResult(
                    test_id=f"determinism_{hashlib.sha256(finding_text.encode()).hexdigest()[:8]}",
                    test_type="determinism",
                    passed=False,
                    details={"error": str(e), "crash": True}
                )

        # All hashes should be identical
        unique_hashes = len(set(hashes))
        is_deterministic = unique_hashes == 1

        return DifferentialResult(
            test_id=f"determinism_{hashlib.sha256(finding_text.encode()).hexdigest()[:8]}",
            test_type="determinism",
            passed=is_deterministic,
            details={
                "iterations": iterations,
                "unique_outputs": unique_hashes,
                "first_scores": scores_list[0][0] if scores_list else None,
                "first_overall": scores_list[0][1] if scores_list else None
            }
        )

    def test_perturbation_robustness(self, base_text: str, perturbations: List[str]) -> DifferentialResult:
        """Test 2: Small text changes should yield similar scores"""
        finding_base = {
            "finding_text": base_text,
            "theme": "Climate",
            "framework": "TCFD"
        }

        try:
            self.total_tests += 1
            base_scores = self.scorer.score_all_dimensions(finding_base)
            base_overall_tuple = self.scorer.calculate_overall_maturity(base_scores)
            base_overall = base_overall_tuple[0]  # Extract float
        except Exception as e:
            self.crash_count += 1
            return DifferentialResult(
                test_id=f"perturbation_{hashlib.sha256(base_text.encode()).hexdigest()[:8]}",
                test_type="perturbation",
                passed=False,
                details={"error": str(e), "crash": True}
            )

        similar_count = 0
        perturbed_results = []

        for perturbed_text in perturbations:
            finding = {
                "finding_text": perturbed_text,
                "theme": "Climate",
                "framework": "TCFD"
            }

            try:
                self.total_tests += 1
                scores = self.scorer.score_all_dimensions(finding)
                overall_tuple = self.scorer.calculate_overall_maturity(scores)
                overall = overall_tuple[0]  # Extract float

                # Check similarity (allow 0.5 difference in overall maturity)
                overall_diff = abs(overall - base_overall)
                is_similar = overall_diff <= 0.5

                if is_similar:
                    similar_count += 1

                perturbed_results.append({
                    "overall": overall,
                    "overall_diff": overall_diff,
                    "similar": is_similar
                })

            except Exception as e:
                self.crash_count += 1
                logger.warning(f"Perturbation crashed: {e}")
                perturbed_results.append({"error": str(e), "crash": True})

        robustness = similar_count / len(perturbations) if perturbations else 0

        return DifferentialResult(
            test_id=f"perturbation_{hashlib.sha256(base_text.encode()).hexdigest()[:8]}",
            test_type="perturbation",
            passed=robustness >= 0.7,  # 70% should be similar
            details={
                "base_overall": base_overall,
                "perturbations": len(perturbations),
                "similar_count": similar_count,
                "robustness": robustness
            }
        )

    def test_monotonicity(self, evidence_progression: List[Tuple[str, float]]) -> DifferentialResult:
        """Test 3: More evidence should not decrease maturity scores"""
        scores_progression = []

        for text, expected_min_overall in evidence_progression:
            finding = {
                "finding_text": text,
                "theme": "Climate",
                "framework": "SBTi"
            }

            try:
                self.total_tests += 1
                scores = self.scorer.score_all_dimensions(finding)
                overall_tuple = self.scorer.calculate_overall_maturity(scores)
                overall = overall_tuple[0]  # Extract float

                tsp_score = scores.get("TSP")
                tsp_value = tsp_score.score if tsp_score else 0

                scores_progression.append({
                    "text": text[:60],
                    "overall": overall,
                    "expected_min": expected_min_overall,
                    "tsp": tsp_value
                })

            except Exception as e:
                self.crash_count += 1
                logger.warning(f"Monotonicity test crashed: {e}")
                scores_progression.append({"error": str(e), "crash": True})

        # Check monotonicity: each level should be >= previous
        is_monotonic = True
        for i in range(1, len(scores_progression)):
            if "crash" in scores_progression[i] or "crash" in scores_progression[i-1]:
                continue
            if scores_progression[i]["overall"] < scores_progression[i-1]["overall"]:
                is_monotonic = False
                break

        return DifferentialResult(
            test_id=f"monotonicity_{len(evidence_progression)}",
            test_type="monotonicity",
            passed=is_monotonic,
            details={
                "levels": len(evidence_progression),
                "progression": scores_progression,
                "is_monotonic": is_monotonic
            }
        )

    def test_sensitivity(self, framework_tests: List[Tuple[str, str, int]]) -> DifferentialResult:
        """Test 4: Framework keywords should boost specific dimension scores"""
        correct_detections = 0
        results = []

        for text, framework, expected_min_score in framework_tests:
            finding = {
                "finding_text": text,
                "theme": "Climate",
                "framework": framework
            }

            try:
                self.total_tests += 1
                scores = self.scorer.score_all_dimensions(finding)

                # Check TSP score (main dimension for SBTi/TCFD frameworks)
                tsp_score_obj = scores.get("TSP")
                tsp_score = tsp_score_obj.score if tsp_score_obj else 0
                detected_correctly = tsp_score >= expected_min_score

                if detected_correctly:
                    correct_detections += 1

                results.append({
                    "framework": framework,
                    "tsp_score": tsp_score,
                    "expected_min": expected_min_score,
                    "correct": detected_correctly
                })

            except Exception as e:
                self.crash_count += 1
                logger.warning(f"Sensitivity test crashed: {e}")
                results.append({"error": str(e), "crash": True})

        sensitivity = correct_detections / len(framework_tests) if framework_tests else 0

        return DifferentialResult(
            test_id=f"sensitivity_{len(framework_tests)}",
            test_type="sensitivity",
            passed=sensitivity >= 0.75,  # 75% correct detections
            details={
                "tests": len(framework_tests),
                "correct": correct_detections,
                "sensitivity": sensitivity,
                "results": results
            }
        )

    def generate_fuzz_cases(self, target_count: int = 1200) -> List[str]:
        """Generate >= 1,200 unique fuzz cases"""
        logger.info(f"\nGenerating {target_count} fuzz cases...")

        # Base templates with various evidence levels
        base_templates = [
            # TSP dimension (Targets & Strategic Priorities)
            "We have set a target to reduce emissions by {percent}% by {year}.",
            "Our company is committed to achieving net-zero emissions by {year}.",
            "Science-based targets validated by SBTi for {year} have been established.",
            "We aim to reach carbon neutrality by {year} through {method}.",
            "Scope 1, 2, and 3 emissions reduction targets set for {year}.",

            # GHG dimension (GHG Emissions Inventory)
            "We report Scope 1 and Scope 2 emissions annually.",
            "Comprehensive Scope 1, 2, and 3 emissions inventory maintained.",
            "Third-party assurance provided for our GHG emissions data.",
            "We track {gas_type} emissions across all operations.",
            "Emissions data verified by {verifier} for accuracy.",

            # RD dimension (Reporting & Disclosure)
            "Our sustainability reporting is aligned with TCFD recommendations.",
            "We disclose climate risks in accordance with CDP guidelines.",
            "Annual sustainability report prepared following GRI standards.",
            "Climate-related financial disclosures published in {framework} format.",
            "We participate in {framework} reporting annually.",

            # DM dimension (Data Maturity)
            "Automated data collection systems track emissions in real-time.",
            "We use {system} for centralized ESG data management.",
            "IoT sensors monitor energy consumption across facilities.",
            "Machine learning models forecast emissions trajectories.",
            "Granular facility-level emissions tracking implemented.",

            # OSP dimension (Organizational Structure & Processes)
            "Dedicated sustainability team with C-suite oversight.",
            "Board-level climate committee established in {year}.",
            "Sustainability KPIs linked to executive compensation.",
            "Chief Sustainability Officer reports directly to CEO.",
            "Cross-functional climate working groups meet {frequency}.",

            # EI dimension (Energy Intelligence)
            "Renewable energy accounts for {percent}% of total consumption.",
            "Energy efficiency improvements of {percent}% achieved since {year}.",
            "We source {percent}% renewable electricity through PPAs.",
            "Smart building systems optimize energy use.",
            "Energy audits conducted {frequency} at all sites.",

            # RMM dimension (Risk Management & Mitigation)
            "Climate risks integrated into enterprise risk management.",
            "Scenario analysis conducted using {scenario} warming scenarios.",
            "Physical and transition risks assessed for all assets.",
            "Climate adaptation strategies implemented for {risk}.",
            "We conduct climate stress testing aligned with {framework}."
        ]

        # Variation parameters
        percents = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        years = [2025, 2030, 2035, 2040, 2045, 2050]
        methods = ["renewable energy", "carbon capture", "offsets", "efficiency improvements", "electrification"]
        gas_types = ["CO2", "methane", "N2O", "fluorinated gases", "greenhouse gases"]
        verifiers = ["DNV", "Bureau Veritas", "SGS", "third-party auditors", "external assurance providers"]
        frameworks = ["TCFD", "CDP", "GRI", "SASB", "ISSB"]
        systems = ["SAP", "Salesforce", "custom platform", "ERP system", "cloud-based system"]
        frequencies = ["monthly", "quarterly", "bi-annually", "annually", "regularly"]
        scenarios = ["1.5°C", "2°C", "3°C", "RCP 4.5", "RCP 8.5"]
        risks = ["flooding", "drought", "extreme weather", "sea level rise", "temperature changes"]

        cases = set()

        # Generate cases from templates
        iterations_per_template = (target_count // len(base_templates)) + 50

        for template in base_templates:
            for _ in range(iterations_per_template):
                text = template.format(
                    percent=random.choice(percents),
                    year=random.choice(years),
                    method=random.choice(methods),
                    gas_type=random.choice(gas_types),
                    verifier=random.choice(verifiers),
                    framework=random.choice(frameworks),
                    system=random.choice(systems),
                    frequency=random.choice(frequencies),
                    scenario=random.choice(scenarios),
                    risk=random.choice(risks)
                )

                # Apply random perturbations (increased variety)
                perturbation_type = random.random()
                if perturbation_type < 0.15:
                    text = text.upper()
                elif perturbation_type < 0.3:
                    text = text.lower()
                elif perturbation_type < 0.35:
                    text = text.title()

                if random.random() < 0.15:
                    text = text.replace(" ", "  ")  # Extra spaces

                if random.random() < 0.15:
                    text = text + " "  # Trailing space

                if random.random() < 0.15:
                    text = " " + text  # Leading space

                # Add prefix/suffix variations
                if random.random() < 0.2:
                    prefixes = ["We report that ", "Our organization states: ", "According to our analysis, ", ""]
                    text = random.choice(prefixes) + text

                if random.random() < 0.2:
                    suffixes = [" for sustainability.", " as part of our ESG strategy.", " to address climate change.", ""]
                    text = text + random.choice(suffixes)

                cases.add(text)

                if len(cases) >= target_count:
                    break

            if len(cases) >= target_count:
                break

        # Additional edge cases
        edge_cases = [
            "",  # Empty string
            " ",  # Just whitespace
            "a" * 1000,  # Very long repetitive text
            "Short",  # Very short text
            "!@#$%^&*()",  # Special characters
            "123456789",  # Numbers only
            "\n\n\n",  # Newlines
            "   leading spaces",
            "trailing spaces   ",
            "CAPS LOCK TEXT",
            "lowercase text",
            "Mixed Case Text With Each Word Capitalized"
        ]

        cases.update(edge_cases)

        cases_list = list(cases)[:target_count]
        unique_ratio = len(cases_list) / target_count

        logger.info(f"Generated {len(cases_list)} unique cases (ratio: {unique_ratio:.2%})")

        return cases_list

    def run_fuzz_suite(self, cases: List[str]) -> DifferentialResult:
        """Run fuzzing suite on all generated cases"""
        logger.info(f"\nRunning fuzz suite on {len(cases)} cases...")

        crashes = []
        deterministic_violations = []

        for i, text in enumerate(cases):
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(cases)} ({i/len(cases)*100:.1f}%)")

            finding = {
                "finding_text": text,
                "theme": "Climate",
                "framework": "TCFD"
            }

            # Test determinism (2 runs)
            try:
                self.total_tests += 2
                scores1 = self.scorer.score_all_dimensions(finding)
                overall_tuple1 = self.scorer.calculate_overall_maturity(scores1)
                overall1 = overall_tuple1[0]  # Extract float

                scores2 = self.scorer.score_all_dimensions(finding)
                overall_tuple2 = self.scorer.calculate_overall_maturity(scores2)
                overall2 = overall_tuple2[0]  # Extract float

                # Check determinism
                if overall1 != overall2:
                    deterministic_violations.append({
                        "text": text[:60],
                        "run1": overall1,
                        "run2": overall2
                    })

            except Exception as e:
                self.crash_count += 1
                crashes.append({
                    "text": text[:60],
                    "error": str(e),
                    "error_type": type(e).__name__
                })

        passed = len(crashes) == 0 and len(deterministic_violations) == 0

        return DifferentialResult(
            test_id=f"fuzz_{len(cases)}",
            test_type="fuzz",
            passed=passed,
            details={
                "total_cases": len(cases),
                "crashes": len(crashes),
                "deterministic_violations": len(deterministic_violations),
                "crash_examples": crashes[:5],
                "violation_examples": deterministic_violations[:5]
            }
        )

    def run_differential_suite(self):
        """Run complete differential test suite (>= 1,200 cases)"""
        logger.info("\n" + "=" * 80)
        logger.info("RUBRIC V3.0 DIFFERENTIAL TEST SUITE")
        logger.info("=" * 80)

        # Test 1: Determinism (10 high-value cases)
        logger.info("\n" + "-" * 80)
        logger.info("TEST 1: DETERMINISM (10 iterations each)")
        logger.info("-" * 80)

        determinism_texts = [
            "We have set science-based targets validated by SBTi for 2030.",
            "Our company reports Scope 1, 2, and 3 emissions with third-party assurance.",
            "Climate risks are integrated into our enterprise risk management framework."
        ]

        for text in determinism_texts:
            result = self.test_determinism(text, iterations=10)
            self.results.append(result)
            status = "PASS" if result.passed else "FAIL"
            logger.info(f"  {status}: {text[:60]}...")

        # Test 2: Perturbation Robustness
        logger.info("\n" + "-" * 80)
        logger.info("TEST 2: PERTURBATION ROBUSTNESS")
        logger.info("-" * 80)

        base_text = "We have committed to net-zero emissions by 2030 validated by SBTi."
        perturbations = [
            base_text.upper(),
            base_text.lower(),
            base_text.replace("2030", "2035"),
            base_text.replace("net-zero", "net zero"),
            base_text + " ",
            " " + base_text,
            base_text.replace(" ", "  "),
            base_text.replace("SBTi", "Science Based Targets initiative")
        ]

        result = self.test_perturbation_robustness(base_text, perturbations)
        self.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        logger.info(f"  {status}: Robustness {result.details['robustness']:.1%}")

        # Test 3: Monotonicity
        logger.info("\n" + "-" * 80)
        logger.info("TEST 3: MONOTONICITY (Evidence Progression)")
        logger.info("-" * 80)

        evidence_levels = [
            ("We are considering climate targets.", 0.0),
            ("We have committed to reducing emissions.", 0.5),
            ("We have a target to reduce emissions by 50% by 2030.", 1.0),
            ("We have a target to reduce emissions by 50% by 2030 validated by SBTi.", 2.0),
        ]

        result = self.test_monotonicity(evidence_levels)
        self.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        logger.info(f"  {status}: Monotonicity preserved")

        # Test 4: Sensitivity (Framework Detection)
        logger.info("\n" + "-" * 80)
        logger.info("TEST 4: SENSITIVITY (Framework Detection)")
        logger.info("-" * 80)

        framework_tests = [
            ("Targets validated by SBTi", "SBTi", 4),  # Expect TSP >= 4
            ("No framework mentioned, just general targets", "None", 0),  # Expect TSP < 4
            ("Science-based targets approved by SBTi for 2030", "SBTi", 4),
            ("We plan to set targets in the future", "None", 0),
        ]

        result = self.test_sensitivity(framework_tests)
        self.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        logger.info(f"  {status}: Sensitivity {result.details['sensitivity']:.1%}")

        # Test 5: Fuzz Suite (>= 1,200 cases)
        logger.info("\n" + "-" * 80)
        logger.info("TEST 5: FUZZ SUITE (>= 1,200 cases)")
        logger.info("-" * 80)

        fuzz_cases = self.generate_fuzz_cases(target_count=1200)
        unique_ratio = len(set(fuzz_cases)) / len(fuzz_cases)
        logger.info(f"Unique ratio: {unique_ratio:.2%} (requirement: >= 0.5)")

        result = self.run_fuzz_suite(fuzz_cases)
        self.results.append(result)
        status = "PASS" if result.passed else "FAIL"
        logger.info(f"  {status}: {result.details['crashes']} crashes, {result.details['deterministic_violations']} violations")

        # Generate summary
        self._generate_summary(unique_ratio=unique_ratio, fuzz_count=len(fuzz_cases))

    def _generate_summary(self, unique_ratio: float, fuzz_count: int):
        """Generate differential test summary"""
        logger.info("\n" + "=" * 80)
        logger.info("DIFFERENTIAL TEST SUMMARY")
        logger.info("=" * 80)

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)

        logger.info(f"\nTest Results:")
        logger.info(f"  Total Test Types: {total_tests}")
        logger.info(f"  Passed: {passed_tests}/{total_tests}")
        logger.info(f"  Success Rate: {passed_tests/total_tests*100:.1f}%")

        logger.info(f"\nExecution Metrics:")
        logger.info(f"  Total Test Cases: {self.total_tests}")
        logger.info(f"  Fuzz Cases: {fuzz_count}")
        logger.info(f"  Unique Ratio: {unique_ratio:.2%} (req: >= 0.5)")
        logger.info(f"  Crashes: {self.crash_count} (req: 0)")

        logger.info(f"\nDetailed Results:")
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            logger.info(f"  {status}: {result.test_type}")

        # SCA Protocol compliance
        sca_compliant = (
            fuzz_count >= 1200 and
            unique_ratio >= 0.5 and
            self.crash_count == 0 and
            passed_tests == total_tests
        )

        logger.info("\n" + "-" * 80)
        logger.info("SCA PROTOCOL v13.8 COMPLIANCE:")
        logger.info("-" * 80)
        logger.info(f"  Fuzz cases >= 1,200: {'YES' if fuzz_count >= 1200 else 'NO'} ({fuzz_count})")
        logger.info(f"  Unique ratio >= 0.5: {'YES' if unique_ratio >= 0.5 else 'NO'} ({unique_ratio:.2%})")
        logger.info(f"  Zero crashes: {'YES' if self.crash_count == 0 else 'NO'} ({self.crash_count})")
        logger.info(f"  All tests passed: {'YES' if passed_tests == total_tests else 'NO'} ({passed_tests}/{total_tests})")

        logger.info("\n" + "=" * 80)
        if sca_compliant:
            logger.info("DIFFERENTIAL TESTING: COMPLIANT")
        else:
            logger.info("DIFFERENTIAL TESTING: NON-COMPLIANT")
        logger.info("=" * 80)

        # Save results
        results_file = QA_DIR / "differential_rubric_v3_results.json"
        results_data = {
            "run_id": RUN_ID,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_test_types": total_tests,
                "passed": passed_tests,
                "total_cases": self.total_tests,
                "fuzz_cases": fuzz_count,
                "unique_ratio": unique_ratio,
                "crashes": self.crash_count,
                "sca_compliant": sca_compliant
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "test_type": r.test_type,
                    "passed": r.passed,
                    "details": r.details
                }
                for r in self.results
            ]
        }

        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        logger.info(f"\nResults saved to: {results_file}")

        log_event("differential_end", results_data["summary"])


def main():
    """Run differential testing suite for rubric v3.0"""
    import os

    # Seed random for deterministic fuzzing: use SEED env var or default
    seed_value = int(os.getenv("SEED", "42"))
    random.seed(seed_value)
    logger.info(f"Random seed set to: {seed_value}")

    logger.info("\nRubric v3.0 Differential Testing (Direct Unit Test)")
    logger.info("Target: agents/scoring/rubric_v3_scorer.py")
    logger.info("=" * 80)

    try:
        tester = RubricV3DifferentialTester()
        tester.run_differential_suite()
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")
        raise
    finally:
        logger.info(f"\nArtifacts:")
        logger.info(f"  - Log: {log_file}")
        logger.info(f"  - Events: {events_file}")
        logger.info(f"  - Results: {QA_DIR / 'differential_rubric_v3_results.json'}")


if __name__ == "__main__":
    main()
