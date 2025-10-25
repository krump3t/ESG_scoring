#!/usr/bin/env python3
"""Export OpenAPI schema from FastAPI app.

Generates OpenAPI 3.0 JSON schema for the ESG Scoring API.
Output: artifacts/api/openapi.json

SCA v13.8-MEA Phase 9
"""

import json
import sys
from pathlib import Path
from fastapi.openapi.utils import get_openapi

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def export_openapi() -> None:
    """Export OpenAPI schema from FastAPI app."""
    from apps.api.main import app

    # Generate OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Ensure output directory exists
    output_dir = Path("artifacts/api")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "openapi.json"

    # Write schema to file
    with open(output_file, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI schema exported to {output_file}")
    print(f"Version: {openapi_schema.get('info', {}).get('version', 'unknown')}")


if __name__ == "__main__":
    export_openapi()
