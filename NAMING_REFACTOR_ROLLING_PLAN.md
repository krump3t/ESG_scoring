# Naming Refactor Rolling Plan (Three Phases)

Owner: ESG Scoring Team  
Scope: Class/function rename alignment across agents/apps/libs with minimal churn  
Status: Draft plan for review

---

## Goals
- Eliminate ambiguous names and ensure consistent imports across the codebase.
- Provide a safe migration path for internal and external users with deprecation notices.
- Keep behavior unchanged; only rename symbols and update imports.

Key collisions and targets:
- libs/contracts/extraction_contracts.py: ExtractionResult → MetricsExtractionResult
- agents/parser/models.py: ExtractionResult → EvidenceExtractionResult
- apps/index/retriever.py: prefer golden path; if distinct variant needed, use IndexedHybridRetriever (not App*)
- apps/scoring/rubric_v3_loader.py: ThemeRubric → ThemeRubricV3

---

## Phase 1 — Introduce Canonical Names + Aliases (Non‑Breaking)

Objective: Add canonical names alongside existing ones using assignment aliases and import‑time deprecations; update re‑exports. No call‑site changes yet.

Steps
1) libs/contracts/extraction_contracts.py
- Define canonical class: `class MetricsExtractionResult(...): ...`
- Add legacy assignment alias (no subclassing) and import‑time warning:
  - `from typing import TypeAlias`
  - `import warnings as _w; _w.warn("ExtractionResult is deprecated; use MetricsExtractionResult", DeprecationWarning, stacklevel=2)`
  - `ExtractionResult: TypeAlias = MetricsExtractionResult`
- Update `__all__` to include both names.

2) agents/parser/models.py
- Define canonical class: `class EvidenceExtractionResult(...): ...`
- Add legacy assignment alias and import‑time warning (warn once):
  - `import warnings as _w; _w.warn("agents.parser.models.ExtractionResult is deprecated; use EvidenceExtractionResult", DeprecationWarning, stacklevel=2)`
  - `ExtractionResult = EvidenceExtractionResult`
- Update `__all__` to include both names.

3) apps/index/retriever.py
- Prefer module namespacing (golden import path) over adding the "App" prefix. Keep class name `HybridRetriever` scoped by module path for public API.
- If a distinct app‑layer variant is necessary, use a capability‑based name: `IndexedHybridRetriever` and alias `HybridRetriever = IndexedHybridRetriever` with an import‑time DeprecationWarning. Avoid constructor warnings.

4) apps/scoring/rubric_v3_loader.py
- Rename implementation class to `ThemeRubricV3`.
- Provide legacy assignment alias with import‑time warning:
  - `import warnings as _w; _w.warn("ThemeRubric is deprecated; use ThemeRubricV3", DeprecationWarning, stacklevel=2)`
  - `ThemeRubric = ThemeRubricV3`

5) Package exports
- Ensure __init__.py files re‑export canonical and legacy names:
  - agents/parser/__init__.py
  - libs/contracts/__init__.py
  - apps/index/__init__.py
  - apps/scoring/__init__.py

6) Documentation
- Update ESG_SCORING_NAMING_CONVENTIONS_MAP.md with canonical names, Deprecation Policy, and Golden Import Paths.

Validation checklist
- Run unit/integration tests; no import errors.
- Ensure DeprecationWarnings are visible in CI logs but do not fail CI.
- Confirm API surface (e.g., FastAPI schemas) unchanged.

Rollback
- Revert specific file changes; no data migrations required.

---

## Phase 2 — Codemod Internal Call Sites (Adopt Canonical Names)

Objective: Replace internal imports/usages with canonical names. Keep legacy aliases for external users.

Mapping
- from libs.contracts.extraction_contracts import ExtractionResult
  → from libs.contracts.extraction_contracts import MetricsExtractionResult
- from agents.parser.models import ExtractionResult
  → from agents.parser.models import EvidenceExtractionResult
- If adopting a capability name for app‑layer retriever:
  - from apps.index.retriever import HybridRetriever
    → from apps.index.retriever import IndexedHybridRetriever
- from apps.scoring.rubric_v3_loader import ThemeRubric
  → from apps.scoring.rubric_v3_loader import ThemeRubricV3

Steps
1) Inventory references (AST preferred; grep fallback)
- libcst/bowler preferred for safety.
- Grep fallbacks (if ripgrep unavailable):
  - find . -type f -name "*.py" | xargs grep -n "from libs.contracts.extraction_contracts import ExtractionResult"
  - find . -type f -name "*.py" | xargs grep -n "from agents.parser.models import ExtractionResult"
  - find . -type f -name "*.py" | xargs grep -n "from apps.index.retriever import HybridRetriever"
  - find . -type f -name "*.py" | xargs grep -n "from apps.scoring.rubric_v3_loader import ThemeRubric"

2) Apply codemod (libcst outline) with guardrails
- Replace ImportFrom nodes per mapping above.
- Replace Name nodes for constructor/type references accordingly.
- Reject replacements in strings and comments.
- Restrict edits to: `agents/`, `apps/`, `libs/`, `src/`.
- Produce a dry‑run diff report and commit as artifact: `artifacts/naming_refactor/preview.diff`.

3) Update tests and docs in-repo
- Mirror import changes in tests and documentation/snippets.

4) Module/file name coherence (optional, staged)
- Align module filenames with canonical class names to reduce confusion:
  - `agents/parser/models.py` → `agents/parser/evidence_models.py` (provide interim re‑export from old path)
  - `libs/contracts/extraction_contracts.py` → `libs/contracts/metrics_contracts.py` (interim re‑export)
- Keep old module paths re‑exporting the canonical symbols during Phase 1–2 window.

5) CI and static checks
- Run tests; ensure no DeprecationWarnings remain in internal paths.
- Add CI rule: treat DeprecationWarning as error for internal paths (e.g., `-W error::DeprecationWarning`) while whitelisting public entrypoints.
- If mypy configured, re-run type check.
- Import graph sanity: `pytest --collect-only` and/or `pipdeptree` to surface straggler imports.

Validation checklist
- Zero internal imports of deprecated names remain.
- Behavior identical; API responses and schemas unchanged.
- Coverage stable.

Rollback
- Revert codemod commit; Phase 1 aliases continue to support legacy imports.

---

## Phase 3 — Remove Deprecated Aliases (Breaking for external users relying on old names)

Objective: Delete legacy names after a compatibility window once downstream code has migrated.

Preconditions
- No internal references to legacy names.
- Announced in CHANGELOG and release notes; external teams acknowledged.

Steps
1) Remove legacy symbols
- libs/contracts/extraction_contracts.py: remove alias `ExtractionResult`, keep `MetricsExtractionResult`.
- agents/parser/models.py: remove alias `ExtractionResult`, keep `EvidenceExtractionResult`.
- apps/index/retriever.py: if alias was added, remove `HybridRetriever` alias; keep `IndexedHybridRetriever` (or keep module‑scoped `HybridRetriever` as golden path).
- apps/scoring/rubric_v3_loader.py: remove alias `ThemeRubric`, keep `ThemeRubricV3`.

2) Enforce hard failures on legacy imports
- After P3 merges, legacy imports raise ImportError (aliases removed). Document this behavior in CHANGELOG and in the naming map.

2) Update __all__ and re‑exports in package __init__.py files.

3) Documentation
- Update ESG_SCORING_NAMING_CONVENTIONS_MAP.md to reference only canonical names.
- CHANGELOG.md: document removal under Breaking Changes.

4) CI and release
- Run full tests and artifact generation (e.g., OpenAPI export).
- Tag release; communicate to stakeholders.

Validation checklist
- No remaining imports of removed names anywhere in repo.
- All pipelines build and pass.

Rollback
- Re-introduce aliases temporarily if an external integration fails unexpectedly.

---

## Tooling: pre‑commit and CI checks

- Pre‑commit
  - Add a grep job (or Ruff custom rule) that fails on importing legacy names in internal code (agents/, apps/, libs/, src/). Maintain a central legacy symbol list.
  - Example grep pattern: `\bfrom\s+libs\.contracts\.extraction_contracts\s+import\s+ExtractionResult\b` and `\bfrom\s+agents\.parser\.models\s+import\s+ExtractionResult\b`.
- Ruff
  - If using Ruff, configure a rule (or extend TID) to forbid the legacy imports in internal paths.
- mypy
  - Enable `--warn-redundant-casts` and `--warn-unused-ignores` to catch leftover type: ignore around renamed imports.
- CI deprecations
  - Run tests with `-W error::DeprecationWarning` for internal code paths (whitelist public entrypoints if necessary) to ensure no new deprecated imports creep in.
- Optional runtime telemetry
  - During P1 only, when `ESG_DEBUG_DEPRECATIONS=1`, log once per process the set of legacy imports encountered to identify downstream usage.

---

## Documentation & Examples

- From Day 1 (P1), all README snippets and examples must use canonical import paths only.
- Provide a Legacy → Canonical mapping table (also in the naming map) so integrators can update mechanically.

---

## Tests Specific to This Refactor

- Contract test: importing legacy names succeeds (until P3) and emits a single DeprecationWarning per process.
- Equivalence test: `MetricsExtractionResult is EvidenceExtractionResult` is False; both can satisfy shared Protocols (if defined) to ensure they’re treated as distinct domain types.
- Serialization test: constructing objects via canonical vs legacy names yields identical JSON/Parquet payloads (round‑trip) where applicable.

## Risk, Timeline, and Communication

Risk
- Low to medium. Main risk is confusion between two distinct ExtractionResult types.
- Mitigation: explicit aliasing, AST codemods, and clear deprecation messaging.

Timeline
- Phase 1: 0.5–1 day (review + CI)
- Phase 2: 1–2 days (codemod + validation)
- Phase 3: 0.5 day post-compatibility window (2–4 weeks suggested)

Communication
- Announce in CHANGELOG.md with examples for new imports.
- Pin a task in tracking board; link to this plan and to updated naming map.

---

## Acceptance Criteria (All Phases)
- Behavior unchanged; only symbol names/imports differ.
- Tests pass consistently across phases.
- Naming map kept in sync with code after each phase.

---

## Appendix: Sample Code Snippets

Phase 1 aliasing example (contracts)
```python
# libs/contracts/extraction_contracts.py
from typing import TypeAlias
import warnings as _w

class MetricsExtractionResult(...):
    ...

_w.warn(
    "libs.contracts.extraction_contracts.ExtractionResult is deprecated; use MetricsExtractionResult",
    DeprecationWarning,
    stacklevel=2,
)

ExtractionResult: TypeAlias = MetricsExtractionResult  # legacy alias

__all__ = ["MetricsExtractionResult", "ExtractionResult"]
```

Phase 2 import update example
```python
# before
from libs.contracts.extraction_contracts import ExtractionResult

# after
from libs.contracts.extraction_contracts import MetricsExtractionResult
```

AST codemod guardrails
- Exclude '.venv', '.git', '.benchmarks', '.mypy_cache', '.pytest_cache', '.hypothesis', and 'tests' if staged separately.
- Only replace exact ImportFrom + Name nodes; avoid touching strings and comments.
- Restrict paths to 'agents/', 'apps/', 'libs/', 'src/'.
- Produce a dry‑run diff artifact for review before apply.

---
