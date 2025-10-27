# ESG Scoring — Naming Refactor & Deprecation Plan (Comprehensive Recommendations)

> Status: Proposed • Scope: repo‑wide • Audience: maintainers + contributors  
> Objective: ship a safe, auditable naming refactor that preserves API stability, enables graceful deprecation, and eliminates long‑tail drift.

---

## 0) Executive Summary

- **Phased plan (P1→P3)**: introduce canonical names + legacy aliases (**no behavior change**) → codemod internal usage → remove legacy names.
- **Key rule**: **prefer symbol aliases** over subclassing; warn once **at import** of legacy names.
- **Hardening**: golden import paths, CI/pre‑commit checks, targeted tests (deprecation, equivalence, serialization).
- **Docs**: canonical names **Day 1**; concise policy for timelines and how to silence warnings.
- **Artifacts**: preview diffs and import‑graph reports captured under `artifacts/naming_refactor/`.

---

## 1) Design Principles

1. **Stability first** — No behavioral changes during P1–P2; only symbol exposure and mechanical rewrites.
2. **Transparency** — Single deprecation warning per legacy symbol **on import**; documented policy and timeline.
3. **Determinism** — Codemods are deterministic, idempotent, and produce auditable diffs.
4. **Narrow surface** — One “golden” import path per public symbol, re‑exported at package boundaries.
5. **Reversibility** — Easy rollback: aliases + re‑exports + preview diffs before apply.

---

## 2) Phased Delivery Plan

### P1 — Introduce Canonical Names & Legacy Aliases (non‑breaking)

- Add canonical symbols and **assign legacy aliases** (assignment or `TypeAlias`), **do not subclass**.
- Emit one **`DeprecationWarning` at import** time for each legacy symbol, not in constructors.
- Re‑export public API from package `__init__.py` files, establishing **golden import paths**.
- Update **docs/examples** to canonical names only.
- Add minimal tests to validate deprecation behavior and API exposure.

**Checklist**
- [ ] Canonical symbols implemented
- [ ] Legacy aliases + import‑time warnings
- [ ] Re‑exports & `__all__` defined for public modules
- [ ] Docs and READMEs migrated
- [ ] Deprecation policy added (see §7)

---

### P2 — Internal Codemod & Guardrails (still non‑breaking)

- Run safe codemods to replace legacy names across **internal** code only (`src/`, `apps/`, `agents/`, `libs/`).  
- Exclude strings/comments; skip non‑code assets; produce **preview diff** before apply.
- Add **import‑graph check** to detect stragglers and non‑golden imports.
- CI gate fails on newly introduced legacy imports.

**Checklist**
- [ ] Dry‑run report at `artifacts/naming_refactor/preview.diff`
- [ ] Import‑graph snapshot at `artifacts/naming_refactor/import_graph.txt`
- [ ] CI gate to block new legacy imports
- [ ] All internal references migrated

---

### P3 — Remove Legacy Names (breaking, scheduled)

- Remove legacy aliases and warnings; bump minor or major version as appropriate.
- CHANGELOG: list removed symbols and their canonical replacements.
- Keep doc redirects for 1 release to reduce 404 churn.

**Checklist**
- [ ] Legacy symbols removed
- [ ] CI passes without deprecation allowances
- [ ] CHANGELOG + migration notes published

---

## 3) Implementation Details

### 3.1 Symbol Aliasing (Prefer over Subclassing)

**Why not subclass?** Subclassing alters MRO/`isinstance`, can break equality, dataclass patterns, and serializers.

**Recommended pattern (identical contract):**
```python
# libs/contracts/metrics_models.py
from typing import TypeAlias

class MetricsExtractionResult(...):
    ...

# Legacy alias
ExtractionResult: TypeAlias = MetricsExtractionResult
```

**If domains are distinct** (e.g., Evidence vs Metrics), keep separate classes but expose **shared Protocols** to avoid tight coupling:
```python
from typing import Protocol

class SupportsToRow(Protocol):
    def to_row(self) -> dict: ...
```

### 3.2 Deprecation Warning (Import-Time, Once)

Emit the warning when the legacy name is *imported*, not at object init.

```python
# agents/parser/models.py
import warnings as _w

class EvidenceExtractionResult(...):
    ...

# legacy export with one-time warning
_w.warn(
    "agents.parser.models.ExtractionResult is deprecated; use EvidenceExtractionResult",
    DeprecationWarning, stacklevel=2
)
ExtractionResult = EvidenceExtractionResult
```

Run tests with **`-W error::DeprecationWarning`** internally to ensure we don’t keep using legacy names; allowlist public entrypoints intended for external users.

### 3.3 Package Surface & Golden Import Paths

- Re‑export public API in `__init__.py` and define `__all__` explicitly.
- Add a test that imports each symbol **only** via the golden path and asserts presence in `dir(pkg)`.

```python
# agents/parser/__init__.py
from .models import EvidenceExtractionResult
__all__ = ["EvidenceExtractionResult"]
```

### 3.4 Module/File Renames for Coherence

When canonicalizing class names, align module names to avoid cognitive drift:
- `agents/parser/models.py` → `agents/parser/evidence_models.py`
- `libs/contracts/extraction_contracts.py` → `libs/contracts/metrics_contracts.py`

Provide interim re‑exports for old module paths until P3.

### 3.5 Retriever Naming (Prefer Namespacing over “App” Prefix)

- Keep `HybridRetriever` as a class name; **scope via module path** (`apps.index.retriever`).
- If two variants exist, suffix by capability: `HybridRetriever` (lib) vs `IndexedHybridRetriever` (app).  
- If you must keep `AppHybridRetriever`, document the rationale and avoid spreading the “App” prefix broadly.

---

## 4) Codemod Plan (LibCST/ruff‑assist)

**Goals**: deterministic, symbol‑level edits, no string/comment churn, conservative scope.

**Guardrails**
- Only edit within `src/`, `apps/`, `agents/`, `libs/`.
- Skip `tests/` on first pass; then run a second pass with visibility and captures.
- Refuse edits in triple‑quoted docs and string literals.
- Generate a diff preview and an **edit manifest** (old→new mapping).

**Outputs**
- `artifacts/naming_refactor/preview.diff`
- `artifacts/naming_refactor/edit_manifest.json`

**Post‑apply checks**
- `pytest --collect-only` to catch import errors.
- Import‑graph snapshot (e.g., `pipdeptree` or `snakeviz`-free script) to verify golden paths.

---

## 5) CI & Pre-Commit Hardening

- **Pre‑commit**: grep/ruff rule blocks legacy symbols in changed lines.
- **Ruff**: custom rule (or `RUF`-prefixed) to forbid non‑golden imports.
- **mypy**: `--strict --warn-redundant-casts --warn-unused-ignores` to flush stale suppressions.
- **Pytest**: `-W error::DeprecationWarning` (internal), allowlist for documented public entrypoints.
- **Telemetry (opt‑in)**: count legacy imports once when `ESG_DEBUG_DEPRECATIONS=1` to discover external use.

Example pre‑commit hook (grep variant):
```bash
#!/usr/bin/env bash
set -euo pipefail
LEGACY='ExtractionResult|HybridRetrieverOld'
git diff --cached -U0 | grep -E "^\+.*(${LEGACY})" && {
  echo "Found legacy symbols in staged changes. Use canonical names."; exit 1; } || true
```

---

## 6) Tests Tailored to This Refactor

1. **Deprecation import test**: importing legacy symbol raises a single `DeprecationWarning`.
2. **API exposure test**: public symbols are importable via **only** the golden path; deep paths are not documented.
3. **Equivalence/Protocol test**: canonical and legacy types satisfy shared Protocols; identity semantics are as intended.
4. **Serialization parity**: objects created via canonical vs legacy names round‑trip the same JSON/Parquet payloads.
5. **No‑spam test**: constructing many objects does **not** multiply warnings (import‑time only).

---

## 7) Deprecation Policy (User-Facing)

- Legacy names supported for **one minor release** or **4 weeks**, whichever is longer.
- During the window: importing legacy names emits `DeprecationWarning` once per process.
- After the window (P3): legacy names are **removed**; import fails with `ImportError`.
- **Silencing in CI** (external users): `PYTHONWARNINGS=ignore::DeprecationWarning` (not recommended for maintainers).
- **CHANGELOG** lists all removed symbols and the canonical replacements.

---

## 8) Documentation & Examples

- All README and examples use **canonical** names **immediately** (P1).
- Add a **Legacy → Canonical** mapping table to `ESG_SCORING_NAMING_CONVENTIONS_MAP.md`.
- Provide a one‑page “How to migrate” with mechanical replacements and common pitfalls.
- Keep old doc anchors alive (redirect or note) through one release after P3.

---

## 9) Rollback Strategy

- If CI fails post‑codemod: revert using the preview diff; keep P1 aliases in place.
- Maintain a feature branch (`feature/naming-refactor`) until P2 is green.
- Gate merges on artifact presence and green CI.

---

## 10) Timeline & Ownership

- **Week 1 (P1)**: land aliases, re‑exports, warnings, tests, and docs.
- **Week 2 (P2)**: codemod + CI gates + import‑graph checks.
- **Week 3 (P3)**: remove legacy names; publish release notes.

**Owners**
- Code: Platform team
- Docs: DevRel/Docs
- CI/Gates: Infra
- Approval: Tech Lead + Product

---

## 11) Appendices

### A. Minimal Deprecation Helper

```python
# utils/deprecation.py
import warnings, os, functools

_EMITTED = set()

def emit_once(symbol: str, replacement: str):
    if symbol in _EMITTED:
        return
    _EMITTED.add(symbol)
    warnings.warn(
        f"{symbol} is deprecated; use {replacement}",
        DeprecationWarning, stacklevel=2
    )
    # Optional telemetry
    if os.getenv("ESG_DEBUG_DEPRECATIONS") == "1":
        print(f"[deprecation] {symbol} -> {replacement}", flush=True)
```

Usage:
```python
from utils.deprecation import emit_once
emit_once("agents.parser.models.ExtractionResult", "EvidenceExtractionResult")
ExtractionResult = EvidenceExtractionResult
```

### B. Sample LibCST Codemod Sketch

```python
# tools/codemods/rename_symbols.py
import libcst as cst
from libcst import matchers as m

REPLACEMENTS = {
    "ExtractionResult": "EvidenceExtractionResult",
    "HybridRetrieverOld": "HybridRetriever",
}

class Renamer(cst.CSTTransformer):
    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name):
        if original_node.value in REPLACEMENTS:
            return updated_node.with_changes(value=REPLACEMENTS[original_node.value])
        return updated_node

# Driver script should walk target dirs, skip tests on first pass,
# and write an artifacts/preview.diff before apply.
```

### C. Golden Import Path Test

```python
# tests/public_api/test_public_imports.py
import importlib

GOLDEN = {
    "agents.parser": ["EvidenceExtractionResult"],
}

def test_public_symbols_exposed():
    for pkg, symbols in GOLDEN.items():
        mod = importlib.import_module(pkg)
        for s in symbols:
            assert hasattr(mod, s)
```

---

**End of document.**
