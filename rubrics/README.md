# Rubric Single Source of Truth

**SCA v13.8 Policy - Effective 2025-10-25**

## Canonical Sources

- **Runtime Source (Executable)**: `esg_rubric_schema_v3.json`
- **Human Mirror (Read-Only)**: `esg_maturity_rubricv3.md`

## Policy

All audits, tests, and loaders **MUST** read from the JSON schema. Markdown is for display and documentation only.

### Prohibited

- Parsing markdown for theme extraction
- Regex-based rubric parsing
- Multiple "source of truth" files

### Required

- Load themes from `esg_rubric_schema_v3.json`
- Use `scoring_rules` from JSON schema
- Validate against JSON structure

### Archived Files

Legacy rubric files have been moved to `rubrics/archive/` to prevent confusion:
- `ESG_maturity_rubric_SOURCETRUTH.md`
- `esg_maturity_rubric.md`
- `esg_rubric_v1.md`
- `compile_rubric.py`
- `maturity_v1.json`
- `esg_rubric_schema_v3.yaml`

## Validation

Run the rubric source check:
```bash
bash scripts/qa/check_rubric_source.sh prod
```

This gate ensures no MD-based extraction in production code.
