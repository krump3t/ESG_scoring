#!/bin/bash
# ESG Authenticity Audit Runner (Bash)
# Sets up environment and runs audit with determinism test

set -e

# Defaults
ESG_ROOT="${ESG_ROOT:-.}"
RUNS="${RUNS:-2}"
OUTPUT_DIR="${OUTPUT_DIR:-artifacts/authenticity}"

# Validate ESG_ROOT
if [ ! -d "$ESG_ROOT" ]; then
    echo "ERROR: ESG_ROOT path does not exist: $ESG_ROOT"
    exit 1
fi

# Change to ESG_ROOT
cd "$ESG_ROOT"
echo "Working directory: $(pwd)"

# Set environment variables for determinism
export PYTHONHASHSEED=0
export SEED=42
export ESG_ROOT
export GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

echo "Environment:"
echo "  PYTHONHASHSEED: $PYTHONHASHSEED"
echo "  SEED: $SEED"
echo "  ESG_ROOT: $ESG_ROOT"
echo "  GIT_COMMIT: $GIT_COMMIT"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"
echo "Output directory: $(cd $OUTPUT_DIR && pwd)"

# Run tests first
echo ""
echo "Running test suite..."
pytest -q tests/test_authenticity_audit.py -v || {
    echo "WARNING: Some tests failed, but continuing audit..."
}

# Run audit
echo ""
echo "Running authenticity audit..."
python scripts/qa/authenticity_audit.py \
    --root "$ESG_ROOT" \
    --runs "$RUNS" \
    --out "$OUTPUT_DIR"

AUDIT_EXIT_CODE=$?

# Check outputs
echo ""
echo "Audit outputs:"
if [ -f "$OUTPUT_DIR/report.json" ]; then
    echo "  ✓ report.json"
else
    echo "  ✗ report.json (NOT FOUND)"
fi

if [ -f "$OUTPUT_DIR/report.md" ]; then
    echo "  ✓ report.md"
    head -30 "$OUTPUT_DIR/report.md"
else
    echo "  ✗ report.md (NOT FOUND)"
fi

# Exit with audit status
echo ""
if [ $AUDIT_EXIT_CODE -eq 0 ]; then
    echo "Audit PASSED"
else
    echo "Audit FAILED"
fi

exit $AUDIT_EXIT_CODE
