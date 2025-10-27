"""Root conftest for all tests - provides shared fixtures."""

import os
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure project root is in path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def fresh_client():
    """Fresh app instance per test to avoid manifest/state caching bleed.

    This fixture:
    - Sets determinism environment variables (PYTHONHASHSEED=0)
    - Clears prometheus metrics registry to avoid duplicate timeseries
    - Reloads the app module to get a fresh app instance
    - Resets COMPANIES_MANIFEST
    - Reloads companies from manifest file
    """
    os.environ["PYTHONHASHSEED"] = "0"

    # Clear prometheus registry to avoid duplicate metrics
    try:
        from prometheus_client import REGISTRY
        for collector in list(REGISTRY._collector_to_names.keys()):
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass
    except Exception:
        pass

    # Remove app module from sys.modules to force fresh import
    modules_to_remove = [m for m in sys.modules if m.startswith("apps.api")]
    for mod in modules_to_remove:
        del sys.modules[mod]

    # Fresh import of app
    from apps.api.main import app, load_companies

    # Reset manifest and reload
    app.COMPANIES_MANIFEST = []
    load_companies()

    return TestClient(app)
