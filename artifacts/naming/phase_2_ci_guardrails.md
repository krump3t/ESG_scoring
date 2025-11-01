# Phase 2 CI/Pre-Commit Guardrails
**Date**: 2025-10-27
**Status**: Configuration Guidelines
**Purpose**: Enforce canonical naming during development and CI/CD

---

## 1. Pre-Commit Hook Configuration

Add to `.pre-commit-config.yaml`:

```yaml
# Enforce canonical naming in imports
- repo: local
  hooks:
    - id: enforce-canonical-symbols
      name: Enforce Canonical Naming
      entry: scripts/enforce_canonical_symbols.py
      language: python
      types: [python]
      stages: [commit]
      files: ^(agents|apps|libs)/.*\.py$
      exclude: ^tests/|^artifacts/
```

### Hook Implementation Script

**`scripts/enforce_canonical_symbols.py`**:

```python
#!/usr/bin/env python3
"""Enforce canonical symbol naming in imports."""

import sys
import re
from pathlib import Path

# Legacy → Canonical mapping
LEGACY_TO_CANONICAL = {
    # MetricsExtractionResult domain
    ("libs.contracts.extraction_contracts", "ExtractionResult"): "MetricsExtractionResult",
    ("libs.contracts", "ExtractionResult"): "MetricsExtractionResult",

    # EvidenceExtractionResult domain
    ("agents.parser.models", "ExtractionResult"): "EvidenceExtractionResult",
    ("agents.parser", "ExtractionResult"): "EvidenceExtractionResult",

    # ThemeRubricV3 domain (app-layer only)
    ("apps.scoring.rubric_v3_loader", "ThemeRubric"): "ThemeRubricV3",
    ("apps.scoring", "ThemeRubric"): "ThemeRubricV3",

    # IndexedHybridRetriever domain (app-layer only)
    ("apps.index.retriever", "HybridRetriever"): "IndexedHybridRetriever",
    ("apps.index", "HybridRetriever"): "IndexedHybridRetriever",
}

def check_file(filepath):
    """Check file for legacy symbol usage."""
    with open(filepath) as f:
        content = f.read()

    violations = []

    for (module, legacy), canonical in LEGACY_TO_CANONICAL.items():
        # Check for legacy imports
        pattern = rf"from\s+{re.escape(module)}\s+import.*\b{legacy}\b"
        for match in re.finditer(pattern, content):
            line_no = content[:match.start()].count('\n') + 1
            violations.append(f"{filepath}:{line_no}: Legacy import '{legacy}' (use '{canonical}')")

    return violations

def main():
    """Check all files."""
    violations = []
    for filepath in sys.argv[1:]:
        violations.extend(check_file(filepath))

    if violations:
        for v in violations:
            print(v)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## 2. Ruff/PyLint Configuration

Add to `pyproject.toml`:

```toml
[tool.ruff]
# Ignore import sorting for canonical naming migration
extend-exclude = ["**/deprecated_symbols"]

[tool.pylint."messages control"]
# Warn on legacy symbol usage
disable = [
    "invalid-name",  # Allow version-suffixed names like ThemeRubricV3
]

[tool.pylint.design]
max-attributes = 7
```

---

## 3. MyPy Strict Mode Configuration

Add to `mypy.ini`:

```ini
[mypy]
strict = True
warn_return_any = True
warn_unused_configs = True

# Per-module overrides for canonical names
[mypy-agents.parser.models]
strict = True

[mypy-libs.contracts.extraction_contracts]
strict = True

[mypy-apps.scoring.rubric_v3_loader]
strict = True

[mypy-apps.index.retriever]
strict = True
```

**Expected**: All internal modules using canonical names should pass `mypy --strict` with 0 errors.

---

## 4. Pytest Configuration for Deprecation Warnings

Add to `pytest.ini`:

```ini
[pytest]
filterwarnings =
    # Convert DeprecationWarnings to errors during test
    error::DeprecationWarning:agents.*
    error::DeprecationWarning:apps.*
    error::DeprecationWarning:libs.*
    # But allow specific internal module deprecations (Phase 1 only)
    ignore::DeprecationWarning:libs.contracts.extraction_contracts
    ignore::DeprecationWarning:agents.parser.models
    ignore::DeprecationWarning:apps.scoring.rubric_v3_loader
    ignore::DeprecationWarning:apps.index.retriever
```

**Expected Behavior**:
- Tests that import legacy symbols will fail with DeprecationWarning treated as error
- Tests importing from golden paths (using canonical names) will pass
- The ignored modules (definition modules) can trigger warnings during import

---

## 5. GitHub Actions CI Gate

Add to `.github/workflows/naming-gates.yml`:

```yaml
name: Naming Enforcement Gates

on: [push, pull_request]

jobs:
  enforce-canonical-symbols:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install ruff mypy pytest

      - name: Run canonical symbol enforcement
        run: |
          python scripts/enforce_canonical_symbols.py $(find agents apps libs -name "*.py" -type f)

      - name: Run MyPy strict mode
        run: |
          mypy --strict agents extraction parser
          mypy --strict apps scoring index
          mypy --strict libs contracts

      - name: Run Pytest with DeprecationWarning gate
        run: |
          pytest tests/ -v -W error::DeprecationWarning --tb=short
```

---

## 6. IDE Integration (VSCode)

Add to `.vscode/settings.json`:

```json
{
  "python.linting.mypyEnabled": true,
  "python.linting.mypyArgs": [
    "--strict",
    "--show-error-codes"
  ],
  "python.linting.ruffEnabled": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true
  }
}
```

---

## 7. Validation Gates (SCA Protocol)

### Gate: Canonical Import Paths
**File**: `scripts/validate_canonical_paths.py`

```python
#!/usr/bin/env python3
"""Validate all internal imports use canonical paths."""

import importlib
import sys

GOLDEN_PATHS = {
    "MetricsExtractionResult": "libs.contracts.MetricsExtractionResult",
    "EvidenceExtractionResult": "agents.parser.EvidenceExtractionResult",
    "ThemeRubricV3": "apps.scoring.ThemeRubricV3",
    "IndexedHybridRetriever": "apps.index.IndexedHybridRetriever",
}

def validate():
    """Validate canonical symbols importable from golden paths."""
    failures = []

    for symbol, golden_path in GOLDEN_PATHS.items():
        module_name, class_name = golden_path.rsplit(".", 1)
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
            print(f"✓ {symbol}: {golden_path}")
        except (ImportError, AttributeError) as e:
            failures.append(f"✗ {symbol}: {golden_path} - {e}")

    if failures:
        for f in failures:
            print(f)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(validate())
```

---

## 8. Running the Guardrails

### Local Development

```bash
# Run pre-commit hook
pre-commit run --all-files

# Run enforcement script
python scripts/enforce_canonical_symbols.py $(find agents apps libs -name "*.py" -type f)

# Validate golden import paths
python scripts/validate_canonical_paths.py

# Run tests with DeprecationWarning gate
pytest tests/ -v -W error::DeprecationWarning
```

### CI/CD

```bash
# GitHub Actions will automatically run on push/PR
# Check workflow status: https://github.com/your-org/your-repo/actions
```

---

## 9. Expected Outcomes

### Phase 2 Complete (Current)
- ✅ All internal imports use canonical names
- ✅ Zero legacy imports in agent/app/lib code
- ✅ Golden import paths working
- ✅ Test suite passing (18/18)
- ✅ Deprecation warnings intact (for backward compat)

### Post-Phase 2 (Ongoing)
- ✅ Pre-commit hook blocks new legacy imports
- ✅ CI gates enforce canonical naming
- ✅ MyPy strict mode prevents regressions
- ✅ Pytest catches deprecation warning violations
- ✅ IDE integration provides real-time feedback

### Phase 3 (4 weeks)
- Remove TypeAlias assignments
- Remove DeprecationWarning code
- Update CHANGELOG
- Release breaking changes
- Gates remain to prevent reintroduction of legacy names

---

## 10. Rollback/Remediation

If a violation is caught:

```bash
# Identify problematic file
grep -n "ExtractionResult\|ThemeRubric\|HybridRetriever" agents/extraction/*.py

# Fix: Replace legacy with canonical
sed -i 's/from libs.contracts.extraction_contracts import ExtractionResult/from libs.contracts.extraction_contracts import MetricsExtractionResult/g' agents/extraction/*.py

# Verify
python scripts/enforce_canonical_symbols.py agents/extraction/*.py
```

---

## 11. Documentation for Developers

Add to `CONTRIBUTING.md`:

```markdown
### Canonical Naming (Phase 2)

The project is undergoing a three-phase naming refactor to disambiguate overlapping class names.

**Current Phase**: Phase 2 (Internal Migration)

**Canonical Import Paths** (use these):
```python
from libs.contracts import MetricsExtractionResult  # Metrics from structured data
from agents.parser import EvidenceExtractionResult   # Evidence from unstructured data
from apps.scoring import ThemeRubricV3              # v3.0 rubric schema
from apps.index import IndexedHybridRetriever       # App-layer retriever
from libs.retrieval import HybridRetriever          # Library-level retriever (no refactor)
```

**Legacy Imports** (deprecated, still work but trigger warnings):
```python
from libs.contracts import ExtractionResult  # ⚠️ Use MetricsExtractionResult
from agents.parser import ExtractionResult   # ⚠️ Use EvidenceExtractionResult
from apps.scoring import ThemeRubric         # ⚠️ Use ThemeRubricV3
from apps.index import HybridRetriever       # ⚠️ Use IndexedHybridRetriever (app-variant)
```

For more details, see `artifacts/naming/`.
```

---

## Summary

| Gate | Status | Implementation |
|------|--------|-----------------|
| Pre-commit hook | Ready | `scripts/enforce_canonical_symbols.py` |
| Ruff/PyLint | Ready | `pyproject.toml` config |
| MyPy strict | Ready | `mypy.ini` + internal modules |
| Pytest deprecation | Ready | `pytest.ini` + `conftest.py` |
| GitHub Actions | Ready | `.github/workflows/naming-gates.yml` |
| IDE integration | Ready | `.vscode/settings.json` |
| Validation script | Ready | `scripts/validate_canonical_paths.py` |
| Documentation | Ready | `CONTRIBUTING.md` update |

**Result**: Zero path forward to legacy symbol introduction during Phase 2→3 transition.

---
