"""
Task 013: Verify API Routing Logic
Tests that the API correctly routes to online mode when ALLOW_NETWORK=true
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
# Script path: prospecting-engine/tasks/013-e2e-verification/scripts/verify_routing.py
# Need to go up 4 levels to reach prospecting-engine
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from unittest.mock import patch, MagicMock

# Set environment for online mode
os.environ['ALLOW_NETWORK'] = 'true'

try:
    # Import modules first (after sys.path is set)
    from fastapi.testclient import TestClient
    import apps.api.main

    # Mock the orchestrator to avoid actual pipeline execution
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_pipeline.return_value = {}

    # Patch and test
    with patch.object(apps.api.main, 'PipelineOrchestrator', return_value=mock_orchestrator):
        from apps.api.main import app

        client = TestClient(app)

        # Test online mode routing
        response = client.post('/score', json={
            'company': 'MSFT',
            'year': 2024,
            'query': 'test'
        })

        status_code = response.status_code
        response_data = response.json()
        mode = response_data.get('mode', 'unknown')

        if status_code == 200 and mode == 'online':
            print(f'SUCCESS: API routed to {mode} mode (status={status_code})')
            sys.exit(0)
        else:
            print(f'FAILURE: API did not route correctly (status={status_code}, mode={mode})')
            sys.exit(1)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
