#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="esg-scoring:ci"
CONTAINER_NAME="esg-scoring-ci"
HOST_PORT="8000"
HEALTH_ENDPOINT="http://localhost:${HOST_PORT}/health"
SCORE_ENDPOINT="http://localhost:${HOST_PORT}/score?semantic=0"

cleanup() {
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}

trap cleanup EXIT

docker build --cache-from "${IMAGE_NAME}" -t "${IMAGE_NAME}" .

docker run -d \
  --name "${CONTAINER_NAME}" \
  -p "${HOST_PORT}:8000" \
  -e PYTHONHASHSEED=0 \
  -e SEED=42 \
  -e LIVE_EMBEDDINGS=false \
  -e ALLOW_NETWORK=false \
  -v "$(pwd)/artifacts:/app/artifacts" \
  "${IMAGE_NAME}" >/dev/null

for attempt in $(seq 1 30); do
  status="$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_ENDPOINT}" || true)"
  if [ "${status}" = "200" ]; then
    break
  fi
  if [ "${attempt}" = "30" ]; then
    echo "Health endpoint did not become ready in time." >&2
    exit 1
  fi
  sleep 2
done

score_response_file="$(mktemp)"
score_status="$(curl -s -w "%{http_code}" -o "${score_response_file}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"company":"TestCo","year":2024,"query":"climate strategy"}' \
  "${SCORE_ENDPOINT}")"

if [ "${score_status}" != "200" ]; then
  echo "Score endpoint returned status ${score_status}" >&2
  cat "${score_response_file}" >&2
  exit 1
fi

python3 - <<PY
import json, sys
from pathlib import Path

payload = json.loads(Path("${score_response_file}").read_text())
scores = payload.get("scores") or []
if len(scores) != 7:
    sys.stderr.write(f"Expected 7 scores, received {len(scores)}\\n")
    sys.exit(1)
for idx, item in enumerate(scores, start=1):
    evidence = (item.get("evidence") or "").strip()
    if evidence and len(evidence.split()) > 30:
        sys.stderr.write(f"Score {idx} evidence exceeds 30 words\\n")
        sys.exit(1)
PY

docker exec "${CONTAINER_NAME}" test -f /app/artifacts/pipeline_validation/demo_topk_vs_evidence.json

rm -f "${score_response_file}"
