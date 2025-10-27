"""Phase 5d test fixtures and configuration."""

import importlib
import pytest


@pytest.fixture(autouse=True, scope="session")
def _ensure_lexical_is_imported():
    """
    Guarantee coverage sees libs.ranking.lexical module.

    This fixture ensures the lexical module is imported at least once
    during test runs, eliminating "module-not-imported" coverage warnings.
    """
    importlib.import_module("libs.ranking.lexical")
