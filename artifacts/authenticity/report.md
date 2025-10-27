# ESG Authenticity Audit Report

**Protocol**: SCA v13.8-MEA
**Timestamp**: 2025-10-27T06:38:08.781685Z
**Git Commit**: unknown
**Status**: OK

## Summary

- **Total Violations**: 34
- **FATAL**: 0
- **WARN**: 34
- **Detectors Run**: 8

## Violations by Type


### Json As Parquet (16)

- **agents\scoring\rubric_models.py:183** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `def to_json(self, output_path: Path) -> None:`

- **apps\mcp_server\server.py:30** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `ok = compile_md_to_json(md, out_json)`

- **rubrics\archive\compile_rubric.py:4** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `def compile_md_to_json(md_path: Path, out_json: Path):`

- **rubrics\archive\compile_rubric.py:20** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `if not compile_md_to_json(md, out_json):`

- **scripts\qa\authenticity_audit.py:255** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `"""Flag to_json() where to_parquet() expected"""`

- **scripts\qa\authenticity_audit.py:266** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `if "to_json(" in line and ("artifacts" in content or "maturity" in content):`

- **scripts\qa\authenticity_audit.py:271** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `description="to_json() used for data artifact - should use to_parquet()",`

- **tests\scoring\test_rubric_loader.py:206** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `def test_cache_rubric_to_json(`

- **tests\scoring\test_rubric_models.py:385** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `def test_maturity_rubric_to_json(self, tmp_path) -> None:`

- **tests\scoring\test_rubric_models.py:407** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `rubric.to_json(json_path)`

- **tests\scoring\test_rubric_models.py:435** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `original_rubric.to_json(json_path)`

- **tests\test_authenticity_audit.py:180** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `"""Should detect to_json() in artifact-related code"""`

- **tests\test_authenticity_audit.py:184** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `df.to_json("results.json")`

- **tests\test_authenticity_audit.py:194** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `"""Should allow to_json() in non-artifact contexts"""`

- **tests\test_authenticity_audit.py:196** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `test_file.write_text('response = df.to_json(orient="records")\n')`

- **tests\test_phase_5_7_remediation.py:40** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `"""Test pattern: replace to_json() with to_parquet()"""`


### Silent Exception (18)

- **apps\integration_validator.py:110** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception as e:`

- **apps\integration_validator.py:188** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception as e:`

- **apps\integration_validator.py:278** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception as e:`

- **apps\integration_validator.py:327** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception as e:`

- **libs\utils\determinism.py:89** [WARN]
  - Except block with pass - silently swallows errors
  - `except ImportError:`

- **scripts\load_embeddings_to_astradb.py:171** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception:`

- **tests\authenticity\test_clock_cp.py:139** [WARN]
  - Except block with pass - silently swallows errors
  - `except ValueError:`

- **tests\authenticity\test_http_cp.py:50** [WARN]
  - Except block with pass - silently swallows errors
  - `except KeyError:`

- **tests\authenticity\test_ingestion_authenticity_cp.py:168** [WARN]
  - Except block with pass - silently swallows errors
  - `except json.JSONDecodeError:`

- **tests\conftest.py:34** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception:`

- **tests\conftest.py:36** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception:`

- **tests\crawler\test_sec_edgar_provider_enhanced.py:488** [WARN]
  - Except block with pass - silently swallows errors
  - `except DocumentNotFoundError:`

- **tests\test_authenticity_audit.py:240** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception:`

- **tests\test_mcp_normalizer.py:113** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception:`

- **tests\test_naming_api_cp.py:230** [WARN]
  - Except block with pass - silently swallows errors
  - `except (ImportError, AssertionError):`

- **tests\test_naming_api_cp.py:237** [WARN]
  - Except block with pass - silently swallows errors
  - `except (ImportError, AssertionError):`

- **tests\test_naming_api_cp.py:244** [WARN]
  - Except block with pass - silently swallows errors
  - `except (ImportError, AssertionError):`

- **tests\test_naming_api_cp.py:251** [WARN]
  - Except block with pass - silently swallows errors
  - `except (ImportError, AssertionError):`


## Determinism Test

- **Status**: PENDING
- **Runs**: 2
