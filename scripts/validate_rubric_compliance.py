"""
Rubric Compliance Validation

Validates that rubric_v3_scorer.py correctly implements the official
esg_maturity_rubricv3.md specification by:

1. Testing each dimension's scoring against rubric stage criteria
2. Verifying evidence detection aligns with rubric examples
3. Checking Microsoft findings against expected rubric stages
4. Documenting any deviations from specification
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.scoring.rubric_v3_scorer import RubricV3Scorer

# Setup paths
TASK_DIR = PROJECT_ROOT / "tasks" / "003-rubric-v3-implementation"
QA_DIR = TASK_DIR / "qa"
QA_DIR.mkdir(parents=True, exist_ok=True)


# Test cases based on OFFICIAL rubric specification
RUBRIC_TEST_CASES = {
    "TSP": [
        # Stage 0: No targets or vague qualitative commitments
        {
            "text": "We care about the environment and corporate social responsibility.",
            "expected_stage": 0,
            "rationale": "Generic CSR statement - rubric stage 0"
        },
        # Stage 1: Short-term qualitative or partial quantitative targets
        {
            "text": "We aim to reduce our carbon footprint in the coming years.",
            "expected_stage": 1,
            "rationale": "Reduction claim without clear scope/baseline - rubric stage 1"
        },
        # Stage 2: Time-bound quantitative targets with baseline
        {
            "text": "We have set a target to reduce emissions by 30% by 2030 compared to our 2020 baseline.",
            "expected_stage": 2,
            "rationale": "Time-bound quantitative target with baseline year - rubric stage 2"
        },
        # Stage 3: Science-based methodology, SBTi submission
        {
            "text": "Our targets are aligned with science-based methodology and we have submitted to SBTi for validation. We conduct scenario modeling for 1.5C pathways.",
            "expected_stage": 3,
            "rationale": "SBTi submission pending, scenario modeling - rubric stage 3"
        },
        # Stage 4: Validated SBTi targets, financial integration
        {
            "text": "We have SBTi-validated science-based targets approved in 2022. Our CAPEX planning integrates carbon reduction with financial modeling under executive oversight.",
            "expected_stage": 4,
            "rationale": "SBTi validation, financial integration, executive oversight - rubric stage 4"
        }
    ],

    "GHG": [
        # Stage 0: No emissions accounting
        {
            "text": "We operate responsibly with environmental considerations.",
            "expected_stage": 0,
            "rationale": "No emissions accounting - rubric stage 0"
        },
        # Stage 1: Partial Scope 1/2 estimates
        {
            "text": "We estimate our facility emissions at approximately 50,000 tons CO2.",
            "expected_stage": 1,
            "rationale": "Partial estimate without methodology - rubric stage 1"
        },
        # Stage 2: Scope 1/2 complete, partial Scope 3
        {
            "text": "We report Scope 1 and Scope 2 emissions totaling 100,000 tons. We also calculate partial Scope 3 using standard emission factors with a recalculation policy.",
            "expected_stage": 2,
            "rationale": "Scope 1/2 complete, partial Scope 3 with methodology - rubric stage 2"
        },
        # Stage 3: Comprehensive Scope 1/2/3 with limited assurance
        {
            "text": "Our comprehensive Scope 1, 2, and 3 inventory undergoes limited assurance verification. We engage suppliers on emission data quality improvements.",
            "expected_stage": 3,
            "rationale": "Comprehensive Scope 1/2/3, supplier engagement, limited assurance - rubric stage 3"
        },
        # Stage 4: Full third-party reasonable assurance
        {
            "text": "We report Scope 1, 2, and 3 emissions with full third-party reasonable assurance by Bureau Veritas. Our GHG inventory is compliant with GHG Protocol including uncertainty analysis.",
            "expected_stage": 4,
            "rationale": "Third-party reasonable assurance, GHG Protocol compliance, audit - rubric stage 4"
        }
    ],

    "RD": [
        # Stage 0: No formal ESG reporting
        {
            "text": "See our company brochure for sustainability highlights.",
            "expected_stage": 0,
            "rationale": "Brochure text only - rubric stage 0"
        },
        # Stage 1: GRI index partial coverage
        {
            "text": "We publish an annual CSR report with GRI index mapping for selected indicators.",
            "expected_stage": 1,
            "rationale": "GRI mapping, partial coverage - rubric stage 1"
        },
        # Stage 2: TCFD-aligned narrative
        {
            "text": "Our sustainability disclosures are aligned with TCFD recommendations covering governance, strategy, risk management, and metrics.",
            "expected_stage": 2,
            "rationale": "TCFD-aligned narrative, annual updates - rubric stage 2"
        },
        # Stage 3: Cross-framework KPI alignment
        {
            "text": "We report using CSRD/ESRS framework with dual materiality assessment and consistent investor reporting across TCFD, GRI, and SASB.",
            "expected_stage": 3,
            "rationale": "Cross-framework alignment, dual materiality - rubric stage 3"
        },
        # Stage 4: External assurance, digital tagging
        {
            "text": "Our sustainability report undergoes external assurance and uses XBRL tagging for digital reporting integrated with our annual financial filing.",
            "expected_stage": 4,
            "rationale": "External assurance, XBRL tagging, integrated filing - rubric stage 4"
        }
    ]
}


# Microsoft 2023 findings with EXPECTED rubric stages
MICROSOFT_RUBRIC_VALIDATION = [
    {
        "finding_id": "msft_2023_001",
        "text": "We are committed to being carbon negative by 2030 and by 2050, we will remove from the environment all the carbon the company has emitted since it was founded in 1975. Our carbon negative commitment includes our Scope 1, Scope 2, and Scope 3 emissions. To achieve this, we have set an interim Science Based Targets initiative (SBTi) validated target to reduce our Scope 1 and Scope 2 emissions by more than half by 2030 compared to our 2020 baseline.",
        "expected_scores": {
            "TSP": {
                "stage": 4,
                "rationale": "SBTi validated targets (explicit) + baseline (2020) + quantitative (>50%) = Stage 4"
            },
            "GHG": {
                "stage": 2,
                "rationale": "Scope 1/2/3 mentioned, baseline disclosed, but no assurance mentioned = Stage 2"
            }
        }
    },
    {
        "finding_id": "msft_2023_002",
        "text": "We report our Scope 1, 2, and 3 emissions annually with third-party assurance from an independent verification body. Our GHG inventory follows the Greenhouse Gas Protocol and undergoes limited assurance by Bureau Veritas.",
        "expected_scores": {
            "GHG": {
                "stage": 3,
                "rationale": "Scope 1/2/3 comprehensive + third-party assurance + GHG Protocol = Stage 3 (limited assurance, not reasonable)"
            },
            "RD": {
                "stage": 1,
                "rationale": "Annual reporting mentioned but no framework alignment stated = Stage 1"
            }
        }
    },
    {
        "finding_id": "msft_2023_003",
        "text": "We publish our climate-related financial disclosures in alignment with the Task Force on Climate-related Financial Disclosures (TCFD) recommendations. Our disclosures cover governance, strategy, risk management, and metrics and targets across climate-related risks and opportunities. We also participate in CDP Climate Change reporting annually and received an A- score in 2023.",
        "expected_scores": {
            "RD": {
                "stage": 2,
                "rationale": "TCFD-aligned (explicit), covers all TCFD pillars, annual updates = Stage 2"
            },
            "RMM": {
                "stage": 2,
                "rationale": "Climate risks identified (governance, strategy, risk mgmt) but no scenario testing mentioned = Stage 2"
            }
        }
    },
    {
        "finding_id": "msft_2023_007",
        "text": "We conduct physical and transition risk assessments for all major facilities using climate scenario analysis aligned with RCP 4.5 and RCP 8.5 pathways. Our Enterprise Risk Management framework integrates climate risks into business planning, capital allocation, and strategic decision-making.",
        "expected_scores": {
            "RMM": {
                "stage": 3,
                "rationale": "Quantified risk (physical/transition), scenario testing (RCP paths), integrated into planning = Stage 3"
            },
            "TSP": {
                "stage": 3,
                "rationale": "Scenario modeling (RCP pathways) embedded in enterprise planning = Stage 3"
            }
        }
    }
]


class RubricComplianceValidator:
    """Validate scorer compliance with rubric specification"""

    def __init__(self) -> None:
        self.scorer = RubricV3Scorer()
        self.violations: List[str] = []
        self.warnings: List[str] = []
        self.passes: List[str] = []

    def validate_dimension(self, dimension: str, test_cases: List[Dict[str, Any]]) -> None:
        """Validate a single dimension against rubric test cases"""
        print(f"\n{'='*80}")
        print(f"VALIDATING DIMENSION: {dimension}")
        print(f"{'='*80}")

        for i, test_case in enumerate(test_cases, 1):
            text = test_case["text"]
            expected = test_case["expected_stage"]
            rationale = test_case["rationale"]

            # Score with rubric v3
            finding = {
                "finding_text": text,
                "theme": "Climate",
                "framework": "TCFD"
            }

            scores = self.scorer.score_all_dimensions(finding)
            actual_score_obj = scores.get(dimension)
            actual = actual_score_obj.score if actual_score_obj else 0

            # Check alignment
            passed = actual == expected
            symbol = "PASS" if passed else "FAIL"

            print(f"\nTest {i}: {rationale}")
            print(f"Text: {text[:80]}...")
            print(f"Expected: Stage {expected} | Actual: Stage {actual} | {symbol}")

            if passed:
                self.passes.append({
                    "dimension": dimension,
                    "test": i,
                    "expected": expected,
                    "actual": actual
                })
            elif abs(actual - expected) == 1:
                # Within 1 stage - warning
                self.warnings.append({
                    "dimension": dimension,
                    "test": i,
                    "expected": expected,
                    "actual": actual,
                    "rationale": rationale,
                    "text": text[:100]
                })
                print(f"  [WARN] WARNING: Off by 1 stage")
            else:
                # More than 1 stage off - violation
                self.violations.append({
                    "dimension": dimension,
                    "test": i,
                    "expected": expected,
                    "actual": actual,
                    "rationale": rationale,
                    "text": text[:100]
                })
                print(f"  [VIOLATION] Off by {abs(actual - expected)} stages")

    def validate_microsoft(self) -> None:
        """Validate Microsoft findings against expected rubric stages"""
        print(f"\n{'='*80}")
        print(f"VALIDATING MICROSOFT 2023 FINDINGS AGAINST RUBRIC")
        print(f"{'='*80}")

        for finding in MICROSOFT_RUBRIC_VALIDATION:
            finding_id = finding["finding_id"]
            text = finding["text"]
            expected_scores: Dict[str, Any] = finding["expected_scores"]

            print(f"\n{finding_id}:")
            print(f"Text: {text[:80]}...")

            # Score with rubric v3
            finding_obj = {
                "finding_text": text,
                "theme": "Climate",
                "framework": "TCFD"
            }

            scores = self.scorer.score_all_dimensions(finding_obj)

            for dimension, expected_info in expected_scores.items():
                expected = expected_info["stage"]
                rationale = expected_info["rationale"]

                actual_score_obj = scores.get(dimension)
                actual = actual_score_obj.score if actual_score_obj else 0

                passed = actual == expected
                symbol = "PASS" if passed else "FAIL"

                print(f"  {dimension}: Expected {expected} | Actual {actual} | {symbol}")
                print(f"    Rationale: {rationale}")

                if passed:
                    self.passes.append({
                        "dimension": dimension,
                        "finding": finding_id,
                        "expected": expected,
                        "actual": actual
                    })
                elif abs(actual - expected) == 1:
                    self.warnings.append({
                        "dimension": dimension,
                        "finding": finding_id,
                        "expected": expected,
                        "actual": actual,
                        "rationale": rationale
                    })
                else:
                    self.violations.append({
                        "dimension": dimension,
                        "finding": finding_id,
                        "expected": expected,
                        "actual": actual,
                        "rationale": rationale
                    })

    def generate_report(self) -> None:
        """Generate compliance report"""
        print(f"\n{'='*80}")
        print("RUBRIC COMPLIANCE REPORT")
        print(f"{'='*80}")

        total_tests = len(self.passes) + len(self.warnings) + len(self.violations)

        print(f"\nTotal Tests: {total_tests}")
        print(f"  Passes: {len(self.passes)} ({len(self.passes)/total_tests*100:.1f}%)")
        print(f"  Warnings (±1 stage): {len(self.warnings)} ({len(self.warnings)/total_tests*100:.1f}%)")
        print(f"  Violations (>1 stage): {len(self.violations)} ({len(self.violations)/total_tests*100:.1f}%)")

        if self.violations:
            print(f"\n{'-'*80}")
            print("VIOLATIONS (>1 stage off):")
            print(f"{'-'*80}")
            for v in self.violations:
                print(f"\n{v.get('dimension')} - {v.get('test', v.get('finding'))}")
                print(f"  Expected: {v['expected']} | Actual: {v['actual']}")
                print(f"  Rationale: {v['rationale']}")
                if 'text' in v:
                    print(f"  Text: {v['text']}...")

        if self.warnings:
            print(f"\n{'-'*80}")
            print("WARNINGS (±1 stage):")
            print(f"{'-'*80}")
            for w in self.warnings:
                print(f"\n{w.get('dimension')} - {w.get('test', w.get('finding'))}")
                print(f"  Expected: {w['expected']} | Actual: {w['actual']}")
                print(f"  Rationale: {w['rationale']}")

        # Overall compliance
        pass_rate = len(self.passes) / total_tests if total_tests > 0 else 0
        acceptable_rate = (len(self.passes) + len(self.warnings)) / total_tests if total_tests > 0 else 0

        print(f"\n{'='*80}")
        print("COMPLIANCE ASSESSMENT:")
        print(f"{'='*80}")
        print(f"Exact Match Rate: {pass_rate*100:.1f}% ({len(self.passes)}/{total_tests})")
        print(f"Acceptable (±1 stage): {acceptable_rate*100:.1f}% ({len(self.passes) + len(self.warnings)}/{total_tests})")

        if acceptable_rate >= 0.8:
            print("\n[OK] COMPLIANT: Scorer substantially aligns with rubric specification")
            compliance = "COMPLIANT"
        elif acceptable_rate >= 0.6:
            print("\n[WARN] PARTIAL: Scorer partially aligns, review warnings and violations")
            compliance = "PARTIAL"
        else:
            print("\n[FAIL] NON-COMPLIANT: Significant deviations from rubric specification")
            compliance = "NON_COMPLIANT"

        # Save report
        report_file = QA_DIR / "rubric_compliance_validation.txt"
        with open(report_file, 'w') as f:
            f.write(f"RUBRIC COMPLIANCE VALIDATION REPORT\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Total Tests: {total_tests}\n")
            f.write(f"Passes: {len(self.passes)} ({pass_rate*100:.1f}%)\n")
            f.write(f"Warnings: {len(self.warnings)}\n")
            f.write(f"Violations: {len(self.violations)}\n")
            f.write(f"Compliance: {compliance}\n")

        print(f"\n[OK] Report saved to: {report_file}")


def main():
    """Run rubric compliance validation"""
    print("="*80)
    print("RUBRIC V3.0 COMPLIANCE VALIDATION")
    print("="*80)
    print("\nValidating rubric_v3_scorer.py against esg_maturity_rubricv3.md specification")

    validator = RubricComplianceValidator()

    # Validate each dimension
    for dimension, test_cases in RUBRIC_TEST_CASES.items():
        validator.validate_dimension(dimension, test_cases)

    # Validate Microsoft findings
    validator.validate_microsoft()

    # Generate report
    validator.generate_report()


if __name__ == "__main__":
    main()
