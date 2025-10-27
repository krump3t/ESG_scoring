# ESG Authenticity Audit Report

**Protocol**: SCA v13.8-MEA
**Timestamp**: 2025-10-27T04:31:27.800149Z
**Git Commit**: unknown
**Status**: OK

## Summary

- **Total Violations**: 77
- **FATAL**: 0
- **WARN**: 77
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

- **scripts\qa\authenticity_audit.py:237** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `"""Flag to_json() where to_parquet() expected"""`

- **scripts\qa\authenticity_audit.py:248** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `if "to_json(" in line and ("artifacts" in content or "maturity" in content):`

- **scripts\qa\authenticity_audit.py:253** [WARN]
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


### Network Import (34)

- **agents\crawler\data_providers\cdp_provider.py:24** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\data_providers\gri_provider.py:11** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\data_providers\sasb_provider.py:15** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\data_providers\sec_edgar_provider.py:25** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\data_providers\ticker_lookup.py:20** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\sustainability_reports_crawler.py:41** [WARN]
  - Network library requests in production code
  - `import requests`

- **apps\ingestion\crawler.py:279** [WARN]
  - Network library requests in production code
  - `import requests`

- **apps\ingestion\parser.py:12** [WARN]
  - Network library requests in production code
  - `import requests`

- **apps\ingestion\report_fetcher.py:203** [WARN]
  - Network library requests in production code
  - `import requests`

- **infrastructure\health\check_all.py:6** [WARN]
  - Network library requests in production code
  - `import requests`

- **libs\utils\http_client.py:83** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\demo_mcp_server_e2e.py:13** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\ingest_real_companies.py:18** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\test_bronze_extraction.py:8** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\test_connections.py:59** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\test_connections.py:114** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\test_connections.py:163** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\test_differential_scoring.py:17** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\test_ghg_extraction.py:15** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\test_progressive_queries.py:6** [WARN]
  - Network library requests in production code
  - `import requests`

- **scripts\test_progressive_queries_sca.py:12** [WARN]
  - Network library requests in production code
  - `import requests`

- **tests\crawler\data_providers\test_gri_provider.py:16** [WARN]
  - Network library requests in production code
  - `import requests`

- **tests\crawler\data_providers\test_sasb_provider.py:16** [WARN]
  - Network library requests in production code
  - `import requests`

- **tests\crawler\data_providers\test_ticker_lookup.py:16** [WARN]
  - Network library requests in production code
  - `import requests`

- **tests\crawler\test_sec_edgar_provider_enhanced.py:358** [WARN]
  - Network library requests in production code
  - `import requests`

- **tests\infrastructure\test_cloud_connectivity.py:122** [WARN]
  - Network library requests in production code
  - `import requests`

- **tests\infrastructure\test_cloud_connectivity.py:364** [WARN]
  - Network library requests in production code
  - `import requests`

- **tests\infrastructure\test_docker_properties.py:17** [WARN]
  - Network library requests in production code
  - `import requests`

- **tests\infrastructure\test_docker_services.py:26** [WARN]
  - Network library requests in production code
  - `import requests`

- **tests\test_authenticity_audit.py:28** [WARN]
  - Network library requests in production code
  - `test_file.write_text("import requests\n")`

- **tests\test_authenticity_audit.py:40** [WARN]
  - Network library httpx in production code
  - `test_file.write_text("import httpx\n")`

- **tests\test_authenticity_audit.py:50** [WARN]
  - Network library urllib.request in production code
  - `test_file.write_text("from urllib.request import urlopen\n")`

- **tests\test_authenticity_audit.py:60** [WARN]
  - Network library boto3 in production code
  - `test_file.write_text("import boto3\n")`

- **tests\test_authenticity_audit.py:72** [WARN]
  - Network library requests in production code
  - `test_file.write_text("import requests\n")`


### Nondeterministic Time (12)

- **tasks\006-multi-source-ingestion\qa\phase1_integration_test.py:69** [WARN]
  - clock.now() breaks determinism - needs override
  - `self.start_time = datetime.now()`

- **tasks\006-multi-source-ingestion\qa\phase1_integration_test.py:94** [WARN]
  - clock.time() breaks determinism - needs override
  - `start_time = time.time()`

- **tasks\006-multi-source-ingestion\qa\phase1_integration_test.py:114** [WARN]
  - clock.time() breaks determinism - needs override
  - `response_time = time.time() - start_time`

- **tasks\006-multi-source-ingestion\qa\phase1_integration_test.py:132** [WARN]
  - clock.time() breaks determinism - needs override
  - `response_time = time.time() - start_time`

- **tasks\007-tier2-data-providers\qa\phase2_integration_test.py:137** [WARN]
  - clock.now() breaks determinism - needs override
  - `"test_date": datetime.now().isoformat(),`

- **tasks\007-tier2-data-providers\qa\phase2_integration_test.py:159** [WARN]
  - clock.time() breaks determinism - needs override
  - `start_time = time.time()`

- **tasks\007-tier2-data-providers\qa\phase2_integration_test.py:171** [WARN]
  - clock.time() breaks determinism - needs override
  - `elapsed_time = time.time() - start_time`

- **tasks\007-tier2-data-providers\qa\phase2_integration_test.py:221** [WARN]
  - clock.time() breaks determinism - needs override
  - `elapsed_time = time.time() - start_time`

- **tests\infrastructure\conftest.py:29** [WARN]
  - clock.time() breaks determinism - needs override
  - `self.start_time = time.time()`

- **tests\infrastructure\conftest.py:58** [WARN]
  - clock.time() breaks determinism - needs override
  - `"timestamp": time.time(),`

- **tests\infrastructure\conftest.py:80** [WARN]
  - clock.time() breaks determinism - needs override
  - `"end_time": time.time(),`

- **tests\infrastructure\conftest.py:81** [WARN]
  - clock.time() breaks determinism - needs override
  - `"duration_seconds": time.time() - self.start_time,`


### Silent Exception (15)

- **apps\api\main.py:259** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception:`

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


## Determinism Test

- **Status**: PENDING
- **Runs**: 2
