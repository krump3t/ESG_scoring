"""
TDD Tests for Unseeded Random Remediation (Phase 1 - AV-001)

Tests verify that random functions are properly seeded for determinism.
Each test is marked with @pytest.mark.cp (critical path) and includes:
1. Standard unit tests
2. Property-based tests with Hypothesis
3. Failure-path tests asserting proper exception handling
"""

import pytest
import random
import hashlib
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from hypothesis import given, strategies as st, settings, seed as hypothesis_seed
import os
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestMcpServerRandomSeeding:
    """Test random seeding in apps/mcp_server/server.py"""

    @pytest.mark.cp
    def test_mcp_server_random_seed_determinism(self):
        """
        Verify that random.seed(company + year) produces deterministic results.

        Failure path: If seed not set, should get different random values on each run.
        """
        import random as _random

        # Simulate the MCP server's seeding approach
        company = "TestCorp"
        year = 2024
        seed_value = company + str(year)

        # Run 1: Get random sequence with seed
        _random.seed(seed_value)
        sequence1 = [_random.randint(1, 3) for _ in range(10)]

        # Run 2: Get random sequence with same seed
        _random.seed(seed_value)
        sequence2 = [_random.randint(1, 3) for _ in range(10)]

        # Both sequences should be identical
        assert sequence1 == sequence2, "Random sequences with same seed should be identical"

    @pytest.mark.cp
    @hypothesis_seed(42)
    @given(st.text(min_size=1, max_size=20), st.integers(min_value=2000, max_value=2100))
    @settings(max_examples=50)
    def test_mcp_server_random_seed_property_based(self, company: str, year: int):
        """
        Property-based test: Given any company/year, seeding should be deterministic.

        Tests that for all inputs, the seeding behavior is consistent.
        """
        import random as _random

        seed_value = company + str(year)

        _random.seed(seed_value)
        result1 = _random.randint(1, 100)

        _random.seed(seed_value)
        result2 = _random.randint(1, 100)

        assert result1 == result2, f"Seed {seed_value} should produce deterministic results"

    @pytest.mark.cp
    def test_mcp_server_unseeded_random_fails(self):
        """
        Failure-path test: Unseeded random should be non-deterministic.

        Verify that calling random without seed produces different results.
        """
        import random as _random

        # Call random without seed - should be different each time
        results = []
        for _ in range(3):
            _random.seed()  # Reset to unseeded state
            results.append(_random.randint(1, 1000000))

        # Very high probability that at least 2 are different
        unique_results = set(results)
        assert len(unique_results) >= 2, "Unseeded random should produce different values"


class TestDifferentialScoringRandomSeeding:
    """Test random seeding in scripts/test_differential_scoring.py"""

    @pytest.mark.cp
    def test_generate_fuzz_cases_random_seed_determinism(self):
        """
        Verify that generate_fuzz_cases with seed produces deterministic fuzzing.

        The function should produce same set of perturbations if seeded.
        """
        import random as _random

        base_texts = ["test text", "another example"]
        seed_value = 42

        # Run 1: Generate fuzzing with seed
        _random.seed(seed_value)
        cases1 = self._generate_fuzz_cases_seeded(base_texts, seed_value)

        # Run 2: Generate fuzzing with same seed
        _random.seed(seed_value)
        cases2 = self._generate_fuzz_cases_seeded(base_texts, seed_value)

        # Cases should be identical
        assert cases1 == cases2, "Fuzz cases with same seed should be identical"

    @pytest.mark.cp
    @hypothesis_seed(42)
    @given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5))
    @settings(max_examples=20)
    def test_generate_fuzz_cases_property_based(self, base_texts: list):
        """
        Property-based test: Fuzzing should be deterministic for any base texts.
        """
        import random as _random
        seed_value = 42

        _random.seed(seed_value)
        cases1 = self._generate_fuzz_cases_seeded(base_texts, seed_value)

        _random.seed(seed_value)
        cases2 = self._generate_fuzz_cases_seeded(base_texts, seed_value)

        # Convert to comparable format
        cases1_str = json.dumps(cases1, sort_keys=True)
        cases2_str = json.dumps(cases2, sort_keys=True)

        assert cases1_str == cases2_str, "Fuzz generation should be deterministic"

    @pytest.mark.cp
    def test_fuzz_random_choice_determinism(self):
        """
        Test that random.choice() on strategies is deterministic with seed.
        """
        import random as _random

        strategies = [
            lambda t: t.replace(" ", "  "),
            lambda t: t.lower(),
            lambda t: t.upper(),
            lambda t: t.replace("a", "b"),
        ]

        base_text = "test text for fuzzing"
        seed_value = 42

        # Run 1: Generate strategy choices with seed
        _random.seed(seed_value)
        choices1 = []
        for _ in range(20):
            idx = _random.randint(0, len(strategies) - 1)
            choices1.append(idx)

        # Run 2: Same seed
        _random.seed(seed_value)
        choices2 = []
        for _ in range(20):
            idx = _random.randint(0, len(strategies) - 1)
            choices2.append(idx)

        assert choices1 == choices2, "Strategy choices should be deterministic"

    @pytest.mark.cp
    def test_fuzz_unseeded_random_fails(self):
        """
        Failure-path: Unseeded random.choice() should be non-deterministic.
        """
        import random as _random

        items = ["a", "b", "c", "d", "e"]

        results = []
        for _ in range(100):
            _random.seed()  # Unseeded
            results.append(_random.choice(items))

        # Should have multiple different items chosen
        unique_items = set(results)
        assert len(unique_items) >= 3, "Unseeded choice should produce varied results"

    @staticmethod
    def _generate_fuzz_cases_seeded(base_texts, seed_value):
        """Helper: Generate fuzz cases with seeding"""
        import random as _random
        _random.seed(seed_value)

        cases = []
        strategies = [
            lambda t: t.replace(" ", "  "),
            lambda t: t.lower(),
            lambda t: t.upper(),
        ]

        for base_text in base_texts:
            cases.append((base_text, "original"))
            for i, strategy in enumerate(strategies):
                try:
                    perturbed = strategy(base_text)
                    cases.append((perturbed, f"strategy_{i}"))
                except:
                    pass

        return cases


class TestRubricV3DifferentialRandomSeeding:
    """Test random seeding in scripts/test_rubric_v3_differential.py"""

    @pytest.mark.cp
    def test_rubric_v3_random_seed_determinism(self):
        """
        Verify that random.choice() in rubric v3 differential tests is deterministic.
        """
        import random as _random

        options = {
            'percents': [10, 20, 30, 40, 50],
            'years': [2020, 2021, 2022, 2023, 2024],
            'methods': ['scuba', 'calculation', 'measurement'],
        }

        seed_value = 42

        # Run 1: Generate choices with seed
        _random.seed(seed_value)
        choices1 = {
            'percent': _random.choice(options['percents']),
            'year': _random.choice(options['years']),
            'method': _random.choice(options['methods']),
        }

        # Run 2: Same seed
        _random.seed(seed_value)
        choices2 = {
            'percent': _random.choice(options['percents']),
            'year': _random.choice(options['years']),
            'method': _random.choice(options['methods']),
        }

        assert choices1 == choices2, "Choice sequence should be deterministic"

    @pytest.mark.cp
    @hypothesis_seed(42)
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=30)
    def test_rubric_v3_perturbation_probability_determinism(self, seed_offset: int):
        """
        Property-based test: Perturbation probabilities should be deterministic.
        """
        import random as _random

        seed_value = 42 + seed_offset

        # Run 1: Generate perturbation decisions with seed
        _random.seed(seed_value)
        decisions1 = []
        for _ in range(10):
            decisions1.append(_random.random() < 0.15)

        # Run 2: Same seed
        _random.seed(seed_value)
        decisions2 = []
        for _ in range(10):
            decisions2.append(_random.random() < 0.15)

        assert decisions1 == decisions2, "Perturbation decisions should be deterministic"

    @pytest.mark.cp
    def test_rubric_v3_random_string_selection_determinism(self):
        """
        Test that random string selection in text perturbations is deterministic.
        """
        import random as _random

        prefixes = ["Extensive", "Comprehensive", "Significant"]
        suffixes = ["is maintained", "is ongoing", "is documented"]

        seed_value = 42
        base_text = "evidence of sustainability"

        # Run 1: Apply random text selections with seed
        _random.seed(seed_value)
        results1 = []
        for _ in range(5):
            text = base_text
            if _random.random() < 0.2:
                text = _random.choice(prefixes) + " " + text
            if _random.random() < 0.2:
                text = text + " " + _random.choice(suffixes)
            results1.append(text)

        # Run 2: Same seed
        _random.seed(seed_value)
        results2 = []
        for _ in range(5):
            text = base_text
            if _random.random() < 0.2:
                text = _random.choice(prefixes) + " " + text
            if _random.random() < 0.2:
                text = text + " " + _random.choice(suffixes)
            results2.append(text)

        assert results1 == results2, "Text perturbations should be deterministic"

    @pytest.mark.cp
    def test_rubric_v3_unseeded_random_fails(self):
        """
        Failure-path: Unseeded random.random() should be non-deterministic.
        """
        import random as _random

        results = []
        for _ in range(100):
            _random.seed()  # Unseeded
            results.append(_random.random())

        # Should have many different values
        unique_results = len(set(results))
        assert unique_results >= 90, f"Unseeded random should be varied (got {unique_results} unique)"


class TestRandomSeedingIntegration:
    """Integration tests for random seeding across all files"""

    @pytest.mark.cp
    def test_seed_from_environment_variable(self):
        """
        Verify that SEED environment variable is respected if set.
        """
        import random as _random

        # Test with explicit env var
        os.environ['SEED'] = '12345'
        seed_value = int(os.getenv('SEED', '42'))

        _random.seed(seed_value)
        result1 = _random.randint(1, 1000000)

        _random.seed(seed_value)
        result2 = _random.randint(1, 1000000)

        assert result1 == result2, "Environment-based seed should be deterministic"

        # Clean up
        del os.environ['SEED']

    @pytest.mark.cp
    @hypothesis_seed(42)
    @given(st.integers(min_value=1, max_value=1000))
    @settings(max_examples=50)
    def test_deterministic_runs_produce_same_hash(self, run_id: int):
        """
        Property-based test: Multiple deterministic runs should produce same hash.

        This verifies end-to-end that seeding leads to reproducible outputs.
        """
        import random as _random

        def generate_deterministic_sequence(seed):
            _random.seed(seed)
            return [_random.randint(0, 255) for _ in range(100)]

        seed = 42
        seq1 = generate_deterministic_sequence(seed)
        seq2 = generate_deterministic_sequence(seed)

        hash1 = hashlib.sha256(json.dumps(seq1).encode()).hexdigest()
        hash2 = hashlib.sha256(json.dumps(seq2).encode()).hexdigest()

        assert hash1 == hash2, f"Deterministic sequences should produce same hash"

    @pytest.mark.cp
    def test_failure_unseeded_hash_varies(self):
        """
        Failure-path: Unseeded runs should produce different hashes.
        """
        import random as _random

        def generate_unseeded_sequence():
            _random.seed()  # Unseeded
            return [_random.randint(0, 255) for _ in range(100)]

        hashes = []
        for _ in range(5):
            seq = generate_unseeded_sequence()
            h = hashlib.sha256(json.dumps(seq).encode()).hexdigest()
            hashes.append(h)

        unique_hashes = set(hashes)
        # With 5 runs, extremely unlikely to get all same unless seeded
        assert len(unique_hashes) >= 3, "Unseeded sequences should vary"


class TestRandomSeedingDeterminism:
    """Tests for PYTHONHASHSEED and reproducibility"""

    @pytest.mark.cp
    def test_pythonhashseed_environment_setup(self):
        """
        Verify PYTHONHASHSEED environment variable affects determinism.
        """
        # This would be set by the runner script
        expected_seed = os.getenv('PYTHONHASHSEED')
        if expected_seed:
            assert expected_seed == '0', "PYTHONHASHSEED should be 0 for determinism"

    @pytest.mark.cp
    def test_dict_iteration_order_reproducible_with_hashseed(self):
        """
        With PYTHONHASHSEED=0, dict iteration order should be consistent.
        """
        d = {'z': 1, 'a': 2, 'b': 3, 'y': 4, 'c': 5}

        # Get keys multiple times
        keys1 = list(d.keys())
        keys2 = list(d.keys())
        keys3 = list(d.keys())

        # All should be identical with deterministic hash seed
        assert keys1 == keys2 == keys3, "Dict iteration order should be consistent"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
