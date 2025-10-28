"""Watsonx embeddings adapter (guarded behind feature flags)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests  # @allow-network: integration tests may call watsonx embeddings

from libs.utils import env

logger = logging.getLogger(__name__)

_EMBED_URL = "https://us-south.ml.cloud.ibm.com/ml/v1/text/embeddings"
_EMBED_VERSION = "2023-05-29"
_MAX_RETRIES = 3


def embed_text_batch(
    texts: Sequence[str],
    *,
    use_live: Optional[bool] = None,
) -> List[List[float]]:
    """Return watsonx embeddings for ``texts`` when live mode is enabled.

    Deterministic behaviour:
    - Stable ordering matching the input sequence.
    - Guarded by LIVE_EMBEDDINGS flag (defaults to False).
    - Retries (backoff) honour IBM rate limits while preserving ordering.
    """
    if not texts:
        return []

    live = env.bool_flag("LIVE_EMBEDDINGS") if use_live is None else use_live
    if not live:
        raise NotImplementedError(
            "Set LIVE_EMBEDDINGS=true (env or feature flag) and provide watsonx "
            "credentials to enable real embeddings."
        )

    api_key = env.get("WX_API_KEY")
    project = env.get("WX_PROJECT")
    model = env.get("WX_MODEL_ID")

    missing = [name for name, value in [("WX_API_KEY", api_key), ("WX_PROJECT", project), ("WX_MODEL_ID", model)] if not value]
    if missing:
        raise RuntimeError(f"Missing watsonx credentials: {', '.join(missing)}")

    payload = {
        "input": list(texts),
        "project_id": project,
        "model_id": model,
        "parameters": {"truncate_input_tokens": True},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    params = {"version": _EMBED_VERSION}

    for attempt in range(_MAX_RETRIES):
        try:
            response = requests.post(
                _EMBED_URL,
                headers=headers,
                params=params,
                json=payload,
                timeout=60,
            )
        except requests.RequestException as exc:
            logger.warning("watsonx embed request failed (%s/%s): %s", attempt + 1, _MAX_RETRIES, exc)
            _sleep_backoff(attempt)
            continue

        if response.status_code == 429:
            logger.warning("watsonx rate limited (%s/%s)", attempt + 1, _MAX_RETRIES)
            _sleep_backoff(attempt)
            continue

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.error("watsonx embed request error: %s", exc)
            _sleep_backoff(attempt)
            continue

        data = response.json()
        vectors = _extract_vectors(data)
        if len(vectors) != len(texts):
            raise ValueError(
                f"Received {len(vectors)} embeddings for {len(texts)} inputs from watsonx."
            )
        return [list(map(float, vector)) for vector in vectors]

    raise RuntimeError("Failed to fetch watsonx embeddings after retries. Check credentials and rate limits.")


def _sleep_backoff(attempt: int) -> None:
    delay = min(2 ** attempt, 8)
    time.sleep(delay)


def _extract_vectors(payload: Dict[str, Any]) -> List[Iterable[float]]:
    """Normalise possible watsonx embedding payloads."""
    candidates = payload.get("results") or payload.get("embeddings") or payload.get("data")
    if not isinstance(candidates, list):
        raise ValueError("Unexpected watsonx embedding payload format.")

    vectors: List[Iterable[float]] = []
    for item in candidates:
        if isinstance(item, dict):
            vector = item.get("embedding") or item.get("values") or item.get("vector")
        else:
            vector = item
        if vector is None:
            raise ValueError("Embedding item missing vector values.")
        vectors.append(vector)
    return vectors


def extract_findings(chunks: List[Dict], theme: str, rubric: Dict) -> List[Dict]:
    """Block placeholder extraction logic on the critical path."""
    raise AssertionError("Replace placeholder finding extraction with authentic implementation")


def classify_theme(findings: List[Dict], theme: str, rubric: Dict) -> Dict:
    """Prevent fabricated theme classification results."""
    raise AssertionError("Replace placeholder theme classification with authentic implementation")
