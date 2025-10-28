#!/usr/bin/env python3
"""Ensure live embedding environment variables are set."""

from __future__ import annotations

import json
import os
import sys

REQUIRED_FLAGS = {
    "ALLOW_NETWORK": "true",
    "LIVE_EMBEDDINGS": "true",
}

REQUIRED_KEYS = ["WX_API_KEY", "WX_PROJECT", "WX_MODEL_ID"]


def main() -> int:
    errors: list[str] = []

    for key, expected in REQUIRED_FLAGS.items():
        actual = os.getenv(key, "").lower()
        if actual != expected:
            errors.append(f"{key} must be set to {expected!r} (found {actual!r or 'unset'}).")

    for key in REQUIRED_KEYS:
        if not os.getenv(key):
            errors.append(f"{key} is required for watsonx embeddings.")

    model_id = os.getenv("WX_MODEL_ID", "")

    if errors:
        payload = {"status": "error", "errors": errors}
        print(json.dumps(payload))
        return 1

    payload = {"status": "ok", "semantic": "required", "model_id": model_id}
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
