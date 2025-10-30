"""
Pre-flight checks for SCA v13.8-MEA workflow
1. Verify PYTHONPATH resolves all imports
2. Run zero-mocks guard on production code
3. Validate no mock/stub/placeholder patterns in CP files
"""
import sys
import pathlib
import importlib
import os
import re

def check_imports():
    """Verify all critical imports can be resolved"""
    root = pathlib.Path(".").resolve()
    sys.path.insert(0, str(root))
    print(f"CWD: {root}")

    required_modules = [
        "apps.pipeline.demo_flow",
        "agents.extraction.enhanced_pdf_extractor",
        "libs.retrieval.semantic_wx",
        "libs.utils"
    ]

    for module_name in required_modules:
        try:
            importlib.import_module(module_name)
            print(f"[ok] import {module_name}")
        except Exception as e:
            print(f"[BLOCKER] cannot import {module_name}: {e}")
            raise

    print("[pass] pre-flight imports")
    return True

def check_no_mocks():
    """Zero-mocks guard: production code must not contain mocks/stubs"""
    ROOT = pathlib.Path(".").resolve()
    INCLUDE_DIRS = ("agents", "libs", "scripts", "apps", "src")
    EXCLUDE_DIRS = {"tests", ".git", ".venv", "venv", "node_modules", "artifacts", "data", "pdf_cache", "build", "dist"}

    BAD_PATTERNS = [
        r"\bmock\b",
        r"\bfake\b",
        r"\bstub\b",
        r"\bdummy\b",
        r"\bsimulat(e|ed|ion)\b",
        r"\bplaceholder\b",
        r"from\s+unittest\.mock\s+import",
        r"\bMagicMock\b",
        r"\bpatch\("
    ]

    violations = []

    for base_dir in INCLUDE_DIRS:
        base_path = ROOT / base_dir
        if not base_path.exists():
            continue

        for dirpath, dirnames, filenames in os.walk(base_path):
            # Exclude unwanted directories
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

            for filename in filenames:
                if not filename.endswith((".py", ".sh", ".json", ".yml", ".yaml", ".md")):
                    continue

                file_path = pathlib.Path(dirpath, filename)
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    if any(re.search(pattern, text, re.I) for pattern in BAD_PATTERNS):
                        violations.append(str(file_path))
                except Exception as e:
                    print(f"[warn] could not read {file_path}: {e}")

    if violations:
        print("NO-MOCKS VIOLATIONS:")
        for v in sorted(set(violations)):
            print(f"  {v}")
        sys.exit(2)

    print("[pass] zero-mocks guard")
    return True

def main():
    print("=== SCA v13.8-MEA Pre-flight Checks ===\n")

    # Check 1: Imports
    print("1. Checking critical imports...")
    check_imports()
    print()

    # Check 2: No mocks in production code
    print("2. Running zero-mocks guard...")
    check_no_mocks()
    print()

    print("=== All pre-flight checks PASSED ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
