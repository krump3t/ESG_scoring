"""
Pytest configuration for Task 008 - ESG Evidence Extraction.

This file is automatically loaded by pytest and provides shared fixtures
and configuration for all tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_ghg_text() -> str:
    """Sample text with GHG evidence for testing."""
    return """
    Our greenhouse gas emissions for fiscal year 2024 were as follows:
    Scope 1 emissions: 15,000 mtCO2e
    Scope 2 emissions from purchased electricity: 8,000 tCO2e
    Scope 3 value chain emissions: 120,000 metric tons CO2 equivalent

    We calculate our emissions in accordance with the GHG Protocol Corporate Standard.
    Our Scope 1 and 2 emissions have received limited assurance from Deloitte.
    We use base year 2019 for our emissions reduction targets.
    """


@pytest.fixture
def sample_page_offsets() -> dict[int, int]:
    """Sample page offsets for testing."""
    return {
        1: 0,
        2: 3000,
        3: 6000,
        4: 9000,
        5: 12000
    }
