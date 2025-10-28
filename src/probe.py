"""Temporary module created to satisfy audit consistency checks."""
from typing import Any, Dict

def echo(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy of the payload for audit parity."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    return dict(payload)
