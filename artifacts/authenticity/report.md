# ESG Authenticity Audit Report

**Protocol**: SCA v13.8-MEA
**Timestamp**: 2025-10-26T23:12:40.467805Z
**Git Commit**: unknown
**Status**: BLOCKED

## Summary

- **Total Violations**: 149
- **FATAL**: 9
- **WARN**: 140
- **Detectors Run**: 8

## Violations by Type


### Eval Exec (6)

- **scripts\qa\authenticity_audit.py:306** [FATAL]
  - eval() or exec() usage - major security/determinism risk
  - `"""Flag eval() and exec() usage"""`

- **scripts\qa\authenticity_audit.py:322** [FATAL]
  - eval() or exec() usage - major security/determinism risk
  - `description="eval() or exec() usage - major security/determinism risk",`

- **tests\test_authenticity_audit.py:273** [FATAL]
  - eval() or exec() usage - major security/determinism risk
  - `"""Should detect eval() usage"""`

- **tests\test_authenticity_audit.py:275** [FATAL]
  - eval() or exec() usage - major security/determinism risk
  - `test_file.write_text('result = eval(user_input)\n')`

- **tests\test_authenticity_audit.py:283** [FATAL]
  - eval() or exec() usage - major security/determinism risk
  - `"""Should detect exec() usage"""`

- **tests\test_authenticity_audit.py:285** [FATAL]
  - eval() or exec() usage - major security/determinism risk
  - `test_file.write_text('exec(code_string)\n')`


### Json As Parquet (16)

- **agents\scoring\rubric_models.py:183** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `def to_json(self, output_path: Path) -> None:`

- **apps\mcp_server\server.py:27** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `ok = compile_md_to_json(md, out_json)`

- **rubrics\archive\compile_rubric.py:4** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `def compile_md_to_json(md_path: Path, out_json: Path):`

- **rubrics\archive\compile_rubric.py:20** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `if not compile_md_to_json(md, out_json):`

- **scripts\qa\authenticity_audit.py:217** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `"""Flag to_json() where to_parquet() expected"""`

- **scripts\qa\authenticity_audit.py:228** [WARN]
  - to_json() used for data artifact - should use to_parquet()
  - `if "to_json(" in line and ("artifacts" in content or "maturity" in content):`

- **scripts\qa\authenticity_audit.py:233** [WARN]
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


### Network Import (33)

- **agents\crawler\data_providers\cdp_provider.py:24** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\data_providers\gri_provider.py:11** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\data_providers\sasb_provider.py:13** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\data_providers\sec_edgar_provider.py:25** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\data_providers\ticker_lookup.py:20** [WARN]
  - Network library requests in production code
  - `import requests`

- **agents\crawler\sustainability_reports_crawler.py:39** [WARN]
  - Network library requests in production code
  - `import requests`

- **apps\ingestion\crawler.py:277** [WARN]
  - Network library requests in production code
  - `import requests`

- **apps\ingestion\parser.py:12** [WARN]
  - Network library requests in production code
  - `import requests`

- **apps\ingestion\report_fetcher.py:201** [WARN]
  - Network library requests in production code
  - `import requests`

- **infrastructure\health\check_all.py:6** [WARN]
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


### Nondeterministic Time (81)

- **agents\crawler\data_providers\base_provider.py:109** [WARN]
  - time.time() breaks determinism - needs override
  - `elapsed = time.time() - self._last_request_time`

- **agents\crawler\data_providers\base_provider.py:112** [WARN]
  - time.time() breaks determinism - needs override
  - `self._last_request_time = time.time()`

- **agents\crawler\data_providers\cdp_provider.py:110** [WARN]
  - datetime.now() breaks determinism - needs override
  - `year_val = result.get('year') or result.get('reporting_year', year or datetime.now().year)`

- **agents\crawler\data_providers\gri_provider.py:151** [WARN]
  - datetime.now() breaks determinism - needs override
  - `date_retrieved=datetime.now().strftime("%Y-%m-%d"),`

- **agents\crawler\data_providers\gri_provider.py:239** [WARN]
  - datetime.now() breaks determinism - needs override
  - `date_retrieved=datetime.now().strftime("%Y-%m-%d"),`

- **agents\crawler\data_providers\sasb_provider.py:159** [WARN]
  - datetime.now() breaks determinism - needs override
  - `year=year if year else datetime.now().year,`

- **agents\crawler\data_providers\sasb_provider.py:174** [WARN]
  - datetime.now() breaks determinism - needs override
  - `date_retrieved=datetime.now().strftime("%Y-%m-%d"),`

- **agents\crawler\data_providers\ticker_lookup.py:133** [WARN]
  - datetime.now() breaks determinism - needs override
  - `year=year if year else datetime.now().year,`

- **agents\crawler\data_providers\ticker_lookup.py:142** [WARN]
  - datetime.now() breaks determinism - needs override
  - `date_retrieved=datetime.now().strftime("%Y-%m-%d"),`

- **agents\crawler\sustainability_reports_crawler.py:249** [WARN]
  - datetime.now() breaks determinism - needs override
  - `year = datetime.now().year`

- **agents\crawler\sustainability_reports_crawler.py:356** [WARN]
  - datetime.now() breaks determinism - needs override
  - `year = datetime.now().year`

- **agents\crawler\writers\parquet_writer.py:244** [WARN]
  - datetime.now() breaks determinism - needs override
  - `extraction_ts = datetime.now()`

- **agents\query\orchestrator.py:175** [WARN]
  - time.time() breaks determinism - needs override
  - `ingestion_id = f"orchestrator_{intent.company}_{intent.year}_{int(time.time())}"`

- **apps\evaluation\response_quality.py:27** [WARN]
  - datetime.now() breaks determinism - needs override
  - `return datetime.now().isoformat()`

- **apps\evaluation\response_quality.py:132** [WARN]
  - datetime.now() breaks determinism - needs override
  - `response_id = hashlib.md5(f"{query}{response}{datetime.now()}".encode()).hexdigest()[:12]`

- **apps\ingestion\crawler.py:27** [WARN]
  - datetime.now() breaks determinism - needs override
  - `return datetime.now().isoformat()`

- **apps\ingestion\crawler.py:100** [WARN]
  - time.time() breaks determinism - needs override
  - `elapsed = time.time() - self.last_request_time`

- **apps\ingestion\crawler.py:104** [WARN]
  - time.time() breaks determinism - needs override
  - `self.last_request_time = time.time()`

- **apps\ingestion\report_fetcher.py:340** [WARN]
  - datetime.now() breaks determinism - needs override
  - `key_parts.append(datetime.now().strftime("%Y%m%d"))`

- **apps\ingestion\report_fetcher.py:352** [WARN]
  - datetime.now() breaks determinism - needs override
  - `age_hours = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 3600`

- **apps\ingestion\validator.py:426** [WARN]
  - datetime.now() breaks determinism - needs override
  - `self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")`

- **apps\pipeline\demo_flow.py:361** [WARN]
  - time.time() breaks determinism - needs override
  - `"timestamp": time.time()`

- **apps\pipeline\theme_adapter.py:14** [WARN]
  - time.time() breaks determinism - needs override
  - `def now(): return int(time.time()*1000)`

- **apps\pipeline_orchestrator.py:121** [WARN]
  - datetime.now() breaks determinism - needs override
  - `log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"`

- **apps\pipeline_orchestrator.py:224** [WARN]
  - time.time() breaks determinism - needs override
  - `phase_start = time.time()`

- **apps\pipeline_orchestrator.py:234** [WARN]
  - time.time() breaks determinism - needs override
  - `phase_latency = time.time() - phase_start`

- **apps\pipeline_orchestrator.py:260** [WARN]
  - time.time() breaks determinism - needs override
  - `phase_start = time.time()`

- **apps\pipeline_orchestrator.py:270** [WARN]
  - time.time() breaks determinism - needs override
  - `phase_latency = time.time() - phase_start`

- **apps\pipeline_orchestrator.py:303** [WARN]
  - time.time() breaks determinism - needs override
  - `phase_start = time.time()`

- **apps\pipeline_orchestrator.py:316** [WARN]
  - time.time() breaks determinism - needs override
  - `phase_latency = time.time() - phase_start`

- **apps\pipeline_orchestrator.py:343** [WARN]
  - time.time() breaks determinism - needs override
  - `phase_start = time.time()`

- **apps\pipeline_orchestrator.py:353** [WARN]
  - time.time() breaks determinism - needs override
  - `phase_latency = time.time() - phase_start`

- **diagnose_quality_issues.py:344** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"diagnostic_timestamp": datetime.now().isoformat(),`

- **diagnose_quality_issues.py:360** [WARN]
  - datetime.now() breaks determinism - needs override
  - `output_file = Path("data/diagnostics") / f"confidence_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"`

- **evaluate_real_reports.py:363** [WARN]
  - datetime.now() breaks determinism - needs override
  - `output_file = Path("data/real_evaluations") / f"real_esg_scores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"`

- **evaluate_real_reports.py:368** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"evaluation_date": datetime.now().isoformat(),`

- **fetch_real_reports.py:83** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"extraction_timestamp": datetime.now().isoformat(),`

- **fetch_real_reports.py:173** [WARN]
  - datetime.now() breaks determinism - needs override
  - `output_file = Path("data/real_reports") / f"fetched_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"`

- **libs\embedding\watsonx_embedder.py:248** [WARN]
  - datetime.now() breaks determinism - needs override
  - `now = datetime.now()`

- **libs\llm\watsonx_client.py:477** [WARN]
  - time.time() breaks determinism - needs override
  - `age = time.time() - cache_file.stat().st_mtime`

- **libs\qa\tee.py:11** [WARN]
  - time.time() breaks determinism - needs override
  - `rec={"ts_ms":int(time.time()*1000),"trace_id":self.trace_id,`

- **libs\storage\astradb_graph.py:172** [WARN]
  - datetime.now() breaks determinism - needs override
  - `created_at=datetime.now().isoformat(),`

- **libs\storage\astradb_graph.py:173** [WARN]
  - datetime.now() breaks determinism - needs override
  - `updated_at=datetime.now().isoformat()`

- **libs\storage\astradb_graph.py:228** [WARN]
  - datetime.now() breaks determinism - needs override
  - `created_at=datetime.now().isoformat()`

- **libs\storage\astradb_vector.py:167** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"timestamp": datetime.now().isoformat()`

- **libs\storage\astradb_vector.py:222** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"timestamp": datetime.now().isoformat()`

- **libs\storage\astradb_vector.py:490** [WARN]
  - datetime.now() breaks determinism - needs override
  - `test_metadata = {"test": True, "timestamp": datetime.now().isoformat()}`

- **libs\utils\trace.py:5** [WARN]
  - time.time() breaks determinism - needs override
  - `rec = {"ts": int(time.time()), **event}`

- **mcp_report_fetcher.py:240** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"fetch_timestamp": datetime.now().isoformat()`

- **mcp_report_fetcher.py:312** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"year": year or datetime.now().year,`

- **mcp_report_fetcher.py:338** [WARN]
  - datetime.now() breaks determinism - needs override
  - `age_hours = (datetime.now().timestamp() - cache_file.stat().st_mtime) / 3600`

- **mcp_report_fetcher.py:347** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"fetched_at": datetime.now().isoformat(),`

- **pipelines\airflow\dags\esg_scoring_dag.py:62** [WARN]
  - datetime.now() breaks determinism - needs override
  - `'timestamp': datetime.now().isoformat()`

- **scripts\compare_esg_analysis.py:23** [WARN]
  - datetime.now() breaks determinism - needs override
  - `return datetime.now().isoformat()`

- **scripts\compare_esg_analysis.py:115** [WARN]
  - time.time() breaks determinism - needs override
  - `t0 = time.time()`

- **scripts\compare_esg_analysis.py:118** [WARN]
  - time.time() breaks determinism - needs override
  - `latency_ms = round((time.time() - t0) * 1000, 2)`

- **scripts\compare_esg_analysis.py:144** [WARN]
  - time.time() breaks determinism - needs override
  - `t0 = time.time()`

- **scripts\compare_esg_analysis.py:160** [WARN]
  - time.time() breaks determinism - needs override
  - `latency_ms = round((time.time() - t0) * 1000, 2)`

- **scripts\compare_esg_analysis.py:177** [WARN]
  - time.time() breaks determinism - needs override
  - `t0 = time.time()`

- **scripts\compare_esg_analysis.py:190** [WARN]
  - time.time() breaks determinism - needs override
  - `latency_ms = round((time.time() - t0) * 1000, 2)`

- **scripts\compare_esg_analysis.py:207** [WARN]
  - time.time() breaks determinism - needs override
  - `t0 = time.time()`

- **scripts\compare_esg_analysis.py:224** [WARN]
  - time.time() breaks determinism - needs override
  - `latency_ms = round((time.time() - t0) * 1000, 2)`

- **scripts\compare_esg_analysis.py:290** [WARN]
  - time.time() breaks determinism - needs override
  - `t0 = time.time()`

- **scripts\compare_esg_analysis.py:292** [WARN]
  - time.time() breaks determinism - needs override
  - `latencies["generation_ms"] = round((time.time() - t0) * 1000, 2)`

- **scripts\fix_task_compliance.py:268** [WARN]
  - datetime.now() breaks determinism - needs override
  - `cutoff_ts = datetime.now() - timedelta(days=threshold_days)`

- **scripts\fix_task_compliance_ascii.py:268** [WARN]
  - datetime.now() breaks determinism - needs override
  - `cutoff_ts = datetime.now() - timedelta(days=threshold_days)`

- **scripts\qa\authenticity_audit.py:179** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"""Flag datetime.now() and time.time() without override mechanism"""`

- **scripts\qa\authenticity_audit.py:179** [WARN]
  - time.time() breaks determinism - needs override
  - `"""Flag datetime.now() and time.time() without override mechanism"""`

- **scripts\qa\authenticity_audit.py:182** [WARN]
  - datetime.now() breaks determinism - needs override
  - `(r"datetime\.now\(\)", "datetime.now()"),`

- **scripts\qa\authenticity_audit.py:183** [WARN]
  - time.time() breaks determinism - needs override
  - `(r"time\.time\(\)", "time.time()"),`

- **scripts\qa\authenticity_audit.py:199** [WARN]
  - time.time() breaks determinism - needs override
  - `# Allow time.time() for performance metrics`

- **scripts\run_scoring.py:47** [WARN]
  - datetime.now() breaks determinism - needs override
  - `logging.FileHandler(f'logs/scoring_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')`

- **scripts\run_scoring.py:195** [WARN]
  - datetime.now() breaks determinism - needs override
  - `report_file = output_dir / f"comparative_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"`

- **scripts\run_scoring.py:200** [WARN]
  - datetime.now() breaks determinism - needs override
  - `md_file = output_dir / f"comparative_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"`

- **scripts\run_scoring.py:203** [WARN]
  - datetime.now() breaks determinism - needs override
  - `f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")`

- **scripts\run_scoring.py:297** [WARN]
  - time.time() breaks determinism - needs override
  - `total_start = time.time()`

- **scripts\run_scoring.py:323** [WARN]
  - time.time() breaks determinism - needs override
  - `total_time = time.time() - total_start`

- **tasks\006-multi-source-ingestion\qa\phase1_integration_test.py:69** [WARN]
  - datetime.now() breaks determinism - needs override
  - `self.start_time = datetime.now()`

- **tasks\007-tier2-data-providers\qa\phase2_integration_test.py:137** [WARN]
  - datetime.now() breaks determinism - needs override
  - `"test_date": datetime.now().isoformat(),`

- **tests\infrastructure\conftest.py:58** [WARN]
  - time.time() breaks determinism - needs override
  - `"timestamp": time.time(),`

- **tests\infrastructure\conftest.py:80** [WARN]
  - time.time() breaks determinism - needs override
  - `"end_time": time.time(),`


### Silent Exception (10)

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

- **scripts\load_embeddings_to_astradb.py:171** [WARN]
  - Except block with pass - silently swallows errors
  - `except Exception:`

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


### Unseeded Random (1)

- **apps\mcp_server\server.py:46** [FATAL]
  - Unseeded random.randint call - breaks determinism
  - `stage = random.randint(1,3)`


### Workspace Escape (2)

- **tests\test_authenticity_audit.py:212** [FATAL]
  - Potential workspace escape: relative path traversal
  - `test_file.write_text('open("../../../etc/passwd")\n')`

- **tests\test_authenticity_audit.py:222** [FATAL]
  - Potential workspace escape: relative path traversal
  - `test_file.write_text('p = Path("../secret.txt")\n')`


## Determinism Test

- **Status**: PENDING
- **Runs**: 2
