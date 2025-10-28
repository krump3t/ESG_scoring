"""Lightweight environment and feature flag helpers.

Designed for deterministic CP usage: offline defaults, opt-in for
integration/service calls.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}

_FLAG_ALIASES: Mapping[str, Iterable[str]] = {
    "LIVE_EMBEDDINGS": ("embeddings", "live"),
    "ALLOW_NETWORK": ("ingestion", "allow_network"),
}


def _parse_bool(value: str, default: Optional[bool] = None) -> Optional[bool]:
    lowered = value.strip().lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    if lowered == "":
        return default
    return default


def _parse_flags(text: str) -> Dict[str, Any]:
    """Parse a minimal subset of YAML (two-level key/value)."""
    result: Dict[str, Any] = {}
    current_section: Optional[str] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.endswith(":") and ":" not in line[:-1]:
            current_section = line[:-1].strip()
            result.setdefault(current_section, {})
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            parsed_value: Any
            bool_value = _parse_bool(value)
            if bool_value is not None:
                parsed_value = bool_value
            elif value.startswith("{") and value.endswith("}"):
                # Support inline dicts such as {live: false}
                inner = value.strip("{} ").split(",")
                inline_dict: Dict[str, Any] = {}
                for entry in inner:
                    if not entry.strip():
                        continue
                    if ":" not in entry:
                        continue
                    k, v = entry.split(":", 1)
                    inline_dict[k.strip()] = _parse_bool(v, default=v.strip())
                parsed_value = inline_dict
            else:
                parsed_value = value

            if current_section and isinstance(result.get(current_section), MutableMapping):
                section = result[current_section]
                if isinstance(section, MutableMapping):
                    section[key] = parsed_value
                else:
                    result[current_section] = {key: parsed_value}
            else:
                result[key] = parsed_value

    return result


@lru_cache(maxsize=1)
def _feature_flags() -> Dict[str, Any]:
    path = Path("configs/feature_flags.yaml")
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    parsed = _parse_flags(text)
    return parsed


def _lookup_alias(name: str) -> Any:
    keys = _FLAG_ALIASES.get(name.upper())
    if not keys:
        return None
    data: Any = _feature_flags()
    for key in keys:
        if not isinstance(data, Mapping):
            return None
        data = data.get(key)
    return data


def load_env() -> Dict[str, str]:
    """Return a copy of process environment variables."""
    return dict(os.environ)


def get(name: str, default: Optional[str] = None) -> Optional[str]:
    """Fetch string environment variable with feature flag fallback."""
    value = os.environ.get(name)
    if value is not None:
        return value
    aliased = _lookup_alias(name)
    if isinstance(aliased, bool):
        return "true" if aliased else "false"
    if isinstance(aliased, str):
        return aliased
    return default


def bool_flag(name: str, default: bool = False) -> bool:
    """Return boolean flag from env or feature flag file."""
    value = os.environ.get(name)
    if value is not None:
        maybe_bool = _parse_bool(value, default=None)
        if maybe_bool is not None:
            return maybe_bool
    aliased = _lookup_alias(name)
    if isinstance(aliased, bool):
        return aliased
    if isinstance(aliased, str):
        maybe_bool = _parse_bool(aliased, default=default)
        if maybe_bool is not None:
            return maybe_bool
    return default
