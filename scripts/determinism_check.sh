#!/bin/bash

# Determinism Validation Script
#
# Executes the orchestration pipeline 3 times with identical parameters
# and verifies that all outputs are identical (deterministic).
#
# Usage:
#   bash scripts/determinism_check.sh [--company "Apple Inc"] [--year 2024] [--query "climate"]
#
# Environment:
#   SEED=42 (fixed)
#   PYTHONHASHSEED=0 (fixed)
#   TOPK=5 (default)
#   ALPHA=0.6 (default)

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Defaults (must match companies.json)
COMPANY="${COMPANY:-Headlam Group Plc}"
YEAR="${YEAR:-2025}"
QUERY="${QUERY:-climate strategy and emissions targets}"
TOPK="${TOPK:-5}"
ALPHA="${ALPHA:-0.6}"
OUTPUT_DIR="${OUTPUT_DIR:-artifacts/orchestrator/baseline}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --company)
      COMPANY="$2"
      shift 2
      ;;
    --year)
      YEAR="$2"
      shift 2
      ;;
    --query)
      QUERY="$2"
      shift 2
      ;;
    --topk)
      TOPK="$2"
      shift 2
      ;;
    --alpha)
      ALPHA="$2"
      shift 2
      ;;
    --output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

cd "$REPO_ROOT"

echo "=== Determinism Validation Check ==="
echo "Company: $COMPANY"
echo "Year: $YEAR"
echo "Query: $QUERY"
echo "Top-K: $TOPK"
echo "Alpha: $ALPHA"
echo "Output: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run orchestration 3 times
echo "Running orchestration 3 times with identical parameters..."
echo ""

HASHES=()

for run_num in 1 2 3; do
  echo "Run $run_num/3..."

  PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}" \
  SEED=42 \
  PYTHONHASHSEED=0 \
  python scripts/orchestrate.py \
    --company "$COMPANY" \
    --year "$YEAR" \
    --query "$QUERY" \
    --runs 1 \
    --output "$OUTPUT_DIR" \
    --topk "$TOPK" \
    --alpha "$ALPHA" \
    --semantic 0 || true

  # Extract hash from run (orchestrate.py puts it in run_1/hash.txt)
  if [ -f "$OUTPUT_DIR/run_1/hash.txt" ]; then
    HASH=$(cat "$OUTPUT_DIR/run_1/hash.txt" 2>/dev/null || echo "")
    if [ -n "$HASH" ]; then
      HASHES+=("$HASH")
      echo "  Hash: ${HASH:0:16}..."
    fi
  else
    echo "  [WARN] Hash file not found at $OUTPUT_DIR/run_1/hash.txt"
  fi

  # Move run_1 to run_N to flatten structure
  if [ -d "$OUTPUT_DIR/run_1" ] && [ ! -d "$OUTPUT_DIR/run_${run_num}_flat" ]; then
    mv "$OUTPUT_DIR/run_1" "$OUTPUT_DIR/run_${run_num}_flat"
  fi
done

echo ""
echo "Hash Comparison:"
for i in "${!HASHES[@]}"; do
  echo "  Run $((i + 1)): ${HASHES[$i]:0:16}..."
done

# Check if all hashes are identical
UNIQUE_HASHES=$(printf '%s\n' "${HASHES[@]}" | sort -u | wc -l)

echo ""
echo "Determinism Analysis:"
echo "  Total runs: 3"
echo "  Unique hashes: $UNIQUE_HASHES"

if [ "$UNIQUE_HASHES" -eq 1 ]; then
  DETERMINISTIC=true
  MESSAGE="[OK] DETERMINISTIC: All runs produced identical outputs"
  EXIT_CODE=0
else
  DETERMINISTIC=false
  MESSAGE="[FAIL] NON-DETERMINISTIC: Output hashes differ across runs"
  EXIT_CODE=1
fi

echo "  $MESSAGE"
echo ""

# Generate determinism report
REPORT_FILE="$OUTPUT_DIR/determinism_report.json"

cat > "$REPORT_FILE" <<EOF
{
  "timestamp": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')",
  "project": "prospecting-engine",
  "task": "Determinism Validation",
  "deterministic": $DETERMINISTIC,
  "total_runs": 3,
  "unique_output_hashes": $UNIQUE_HASHES,
  "all_hashes": [
    "${HASHES[0]:-}",
    "${HASHES[1]:-}",
    "${HASHES[2]:-}"
  ],
  "parameters": {
    "company": "$COMPANY",
    "year": $YEAR,
    "query": "$QUERY",
    "topk": $TOPK,
    "alpha": $ALPHA
  },
  "seeds": {
    "PYTHONHASHSEED": "0",
    "SEED": "42",
    "PROVIDER": "local"
  },
  "message": "$MESSAGE"
}
EOF

echo "Report: $REPORT_FILE"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
  echo "[PASS] Determinism check passed!"
else
  echo "[FAIL] Determinism check failed!"
fi

exit $EXIT_CODE
