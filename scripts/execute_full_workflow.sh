#!/usr/bin/env bash
# SCA v13.8-MEA Complete Workflow Execution
# Runs all steps: 3× replay → determinism → authenticity → reports → release

set -euo pipefail

cd "$(dirname "$0")/.."
echo "Working directory: $(pwd)"

# Setup environment
export PYTHONPATH="."
export SEED=42
export PYTHONHASHSEED=0
export WX_OFFLINE_REPLAY=true
unset ALLOW_NETWORK 2>/dev/null || true

echo "=== SCA v13.8-MEA Full Workflow Execution ==="
echo "SEED=$SEED, PYTHONHASHSEED=$PYTHONHASHSEED, WX_OFFLINE_REPLAY=$WX_OFFLINE_REPLAY"
echo ""

# Step 1: Pre-flight checks
echo "Step 1: Pre-flight checks..."
.venv/Scripts/python.exe scripts/preflight_check.py || { echo "[BLOCKED] Pre-flight failed"; exit 1; }
echo ""

# Step 2: Create output directory
mkdir -p artifacts/matrix_determinism
echo "Step 2: Running 3× deterministic scoring..."

# Run 1
echo "  Run 1 of 3..."
.venv/Scripts/python.exe scripts/run_matrix.py --config configs/companies_local.yaml 2>&1 | tee artifacts/matrix_determinism/run1.txt
echo "  ✓ Run 1 complete"

# Run 2
echo "  Run 2 of 3..."
.venv/Scripts/python.exe scripts/run_matrix.py --config configs/companies_local.yaml 2>&1 | tee artifacts/matrix_determinism/run2.txt
echo "  ✓ Run 2 complete"

# Run 3
echo "  Run 3 of 3..."
.venv/Scripts/python.exe scripts/run_matrix.py --config configs/companies_local.yaml 2>&1 | tee artifacts/matrix_determinism/run3.txt
echo "  ✓ Run 3 complete"

echo ""

# Step 3: Determinism verification
echo "Step 3: Verifying determinism..."
.venv/Scripts/python.exe - <<'PYEOF'
import hashlib, pathlib, json, sys

p = pathlib.Path("artifacts/matrix_determinism")
files = ["run1.txt", "run2.txt", "run3.txt"]

hashes = []
for f in files:
    fpath = p / f
    if not fpath.exists():
        print(f"[BLOCKED] {f} not found")
        sys.exit(1)
    h = hashlib.sha256(fpath.read_bytes()).hexdigest()
    hashes.append(h)
    print(f"  {f}: {h[:16]}...")

identical = len(set(hashes)) == 1
report = {"hashes": hashes, "identical": identical}

(p / "determinism_report.json").write_text(json.dumps(report, indent=2))

if identical:
    print("  ✓ Determinism PASSED (all hashes identical)")
else:
    print("  ✗ Determinism FAILED (hashes differ)")
    sys.exit(1)
PYEOF

echo ""

# Step 4: Scoring authenticity verification
echo "Step 4: Running scoring authenticity verification..."
.venv/Scripts/python.exe scripts/verify_scoring_authenticity.py || { echo "[BLOCKED] Authenticity verification failed"; exit 1; }
echo ""

# Step 5: Generate NL reports
echo "Step 5: Generating grounded NL reports..."
.venv/Scripts/python.exe scripts/generate_nl_report.py --config configs/companies_local.yaml || { echo "[BLOCKED] Report generation failed"; exit 1; }
echo ""

# Step 6: Assemble release bundle
echo "Step 6: Assembling attested release bundle..."
.venv/Scripts/python.exe - <<'PYEOF'
import os, json, glob, shutil, pathlib, time

out = pathlib.Path("artifacts/release_authentic_scoring")
out.mkdir(parents=True, exist_ok=True)

patterns = [
    "artifacts/matrix/*/baseline/run_1/scoring_response.json",
    "artifacts/matrix/*/pipeline_validation/demo_topk_vs_evidence.json",
    "artifacts/matrix/*/pipeline_validation/evidence_audit.json",
    "artifacts/matrix_determinism/determinism_report.json",
    "artifacts/matrix/scoring_authenticity_report.json",
    "artifacts/reports/*_nl_report.md",
    "artifacts/reports/*_nl_report.json",
    "artifacts/wx_cache/ledger.jsonl",
    "configs/companies_local.yaml",
    "configs/extraction.json",
    "configs/integration_flags.json"
]

copied = 0
for pat in patterns:
    for p in glob.glob(pat):
        dest = out / pathlib.Path(p).name
        shutil.copy2(p, dest)
        copied += 1
        print(f"  Copied: {pathlib.Path(p).name}")

attestation = {
    "protocol": "SCA v13.8-MEA",
    "no_mocks": True,
    "offline_replay": True,
    "seeds": {
        "SEED": os.getenv("SEED"),
        "PYTHONHASHSEED": os.getenv("PYTHONHASHSEED")
    },
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "files_count": copied
}

(out / "ATTESTATION.json").write_text(json.dumps(attestation, indent=2))
print(f"\n✓ Release bundle: {out.resolve()}")
print(f"  {copied} files + ATTESTATION.json")
PYEOF

echo ""
echo "=== Workflow Complete ==="
echo "✓ All steps passed"
echo "✓ Determinism verified"
echo "✓ Authenticity validated"
echo "✓ Reports generated"
echo "✓ Release bundle assembled"
