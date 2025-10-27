# Assumptions - Phase 1: Production Integration - Core Infrastructure

**Task ID**: 016-production-integration-phase1
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Technical Environment Assumptions

### A1: Docker Desktop Resources
**Assumption**: Developer machines have Docker Desktop with minimum 8GB RAM and 4 CPUs allocated.

**Rationale**: 9 services require ~6GB RAM total (postgres 512MB, redis 256MB, minio 1GB, iceberg 512MB, trino 2GB, airflow 1.5GB, mcp-server 512MB, ngrok 128MB, postgres 512MB).

**Risk if Invalid**: Services crash with OOM errors, containers fail health checks.

**Validation**: setup-local.sh checks Docker Desktop resource allocation before starting services.

**Mitigation**: Document minimum requirements in README.md; provide resource optimization guide (e.g., reduce Trino heap to 1GB for local dev).

---

### A2: Internet Connectivity
**Assumption**: Developer machines have stable internet connection for accessing IBM watsonx.ai API, AstraDB cloud database, and ngrok tunnel service.

**Rationale**: 3 of 9 services require external cloud dependencies (watsonx.ai, AstraDB, ngrok).

**Risk if Invalid**: MCP server cannot generate embeddings (watsonx.ai), cannot store/query vectors (AstraDB), cannot expose public endpoint (ngrok).

**Validation**: test-local.sh includes connectivity tests:
```bash
curl -f https://us-south.ml.cloud.ibm.com/ml/v1/deployments  # watsonx.ai
curl -f https://${ASTRA_DB_ID}-${ASTRA_DB_REGION}.apps.astra.datastax.com  # AstraDB
curl -f https://ngrok.com  # ngrok service
```

**Mitigation**: Document offline fallback mode (use local embeddings model, skip AstraDB, disable ngrok).

---

### A3: IBM Cloud API Keys Valid
**Assumption**: User-provided IBM watsonx.ai API key and project ID are valid and not expired.

**Rationale**: watsonx.ai API requires active API key; keys can expire after 90 days.

**Risk if Invalid**: All embedding generation fails with 401 Unauthorized; extraction pipeline cannot run.

**Validation**: setup-local.sh includes credential validation:
```python
from ibm_watsonx_ai import Credentials
creds = Credentials(api_key=os.getenv("IBM_WATSONX_API_KEY"), url=os.getenv("IBM_WATSONX_URL"))
# If invalid, raises APIException
```

**Mitigation**: Document key rotation process; add reminder in .env.production.example ("Rotate every 90 days").

---

### A4: AstraDB Free Tier Quota Available
**Assumption**: AstraDB free tier limits (5GB storage, 20M reads/month) are not exceeded.

**Rationale**: PoC workload expected to be <1GB vectors (10K documents × 384-dim × 4 bytes = ~15MB per 10K docs) and <1M queries/month.

**Risk if Invalid**: AstraDB throttles requests (429 Too Many Requests), vector storage fails.

**Validation**: Monitor AstraDB console usage dashboard weekly; implement query rate limiting (100 req/hour) in MCP server.

**Mitigation**: Implement Redis caching to reduce AstraDB queries by 70%+; document upgrade path to pay-as-you-go tier.

---

### A5: ngrok Tunnel Stability
**Assumption**: ngrok free tier tunnel remains stable for 5+ minutes during testing (acceptable for PoC validation).

**Rationale**: SC5 in hypothesis.md requires 5-minute uptime; user acknowledged production deployment is "months away."

**Risk if Invalid**: Tunnel disconnects mid-test, integration tests fail sporadically.

**Validation**: Integration test `test_ngrok_tunnel_stability()` checks tunnel uptime via /api/tunnels endpoint.

**Mitigation**: Document ngrok Pro tier ($10/month) for 24+ hour sessions; provide Cloudflare Tunnel fallback configuration in Opus_Full_Implementation_Plan.md.

---

## Dependency Assumptions

### A6: No Conflicting Python Dependencies
**Assumption**: ibm-watsonx-ai, cassandra-driver, apache-airflow, and other new dependencies have no transitive dependency conflicts.

**Rationale**: Airflow 2.7.3 pins many dependencies (e.g., protobuf, grpcio); ibm-watsonx-ai may require different versions.

**Risk if Invalid**: pip install fails with dependency resolution error, services cannot start.

**Validation**: CI/CD pipeline runs `pip install -r requirements.txt --dry-run` before actual install.

**Mitigation**: Pin specific versions if conflicts arise (e.g., `protobuf==4.24.4`); isolate Airflow in Docker container.

---

### A7: Docker Images Available in Registry
**Assumption**: All base Docker images (apache/airflow:2.7.3, python:3.11-slim, redis:7-alpine, etc.) are available in Docker Hub.

**Rationale**: docker-compose pull requires public image access.

**Risk if Invalid**: Image pull fails, docker-compose up cannot start services.

**Validation**: setup-local.sh runs `docker-compose pull` before `docker-compose build`.

**Mitigation**: Use corporate image registry if Docker Hub rate-limited; cache images locally.

---

## Data Assumptions

### A8: Existing Parquet Data Compatible
**Assumption**: Parquet files from Phase 4 (data_lake/parquet/) are compatible with DuckDB 0.9.2 reader.

**Rationale**: DuckDB supports Parquet format v2.x; Phase 4 used pyarrow 15.0.2 (writes Parquet v2.6).

**Risk if Invalid**: DuckDB cannot read Parquet files, analytics queries fail.

**Validation**: Integration test `test_duckdb_parquet_read()` attempts to read existing Parquet files.

**Mitigation**: Regenerate Parquet files with compatible schema if needed; document Parquet version requirements.

---

### A9: Ground Truth Data Available
**Assumption**: Ground truth data for Microsoft (CIK 0000789019) and Tesla (CIK 0001318605) FY2024 is available in `context/ground_truth/` from Phase 5.

**Rationale**: Phase 1 integration tests need ground truth for validation; Phase 5 already created these files.

**Risk if Invalid**: Integration tests cannot validate query results, SC4 validation fails.

**Validation**: Test setup checks for ground_truth/*.json files; fails fast if missing.

**Mitigation**: Document manual ground truth extraction process; provide SEC EDGAR URLs in evidence.json.

---

## Operational Assumptions

### A10: Single Developer Local Development
**Assumption**: Phase 1 is single-developer, single-machine local development (no multi-user collaboration).

**Rationale**: Docker Compose runs on localhost only; no shared database or distributed services.

**Risk if Invalid**: Multiple developers cannot collaborate on same environment, data conflicts arise.

**Validation**: N/A (design assumption for Phase 1).

**Mitigation**: Document multi-developer setup in Phase 6 (shared AstraDB, separate ngrok tunnels, IAM for Airflow).

---

### A11: No Production Traffic During Testing
**Assumption**: MCP server exposed via ngrok is for testing only (no external users, no SLA requirements).

**Rationale**: Free ngrok tier has 2-hour session limit and random URLs; not production-ready.

**Risk if Invalid**: External users access test endpoint, data inconsistencies arise.

**Validation**: Document in README.md: "This is a development environment only. Do not share ngrok URLs publicly."

**Mitigation**: Implement API key authentication (MCP_API_KEY) to prevent unauthorized access; add rate limiting (100 req/hour).

---

### A12: Local Data Persistence Acceptable
**Assumption**: Docker volumes (postgres_data, redis_data, minio_data, etc.) persist data across container restarts but are not backed up.

**Rationale**: Phase 1 is testing/development; data loss is acceptable (can regenerate from SEC filings).

**Risk if Invalid**: Data loss occurs, developers lose test results.

**Validation**: N/A (design assumption for Phase 1).

**Mitigation**: Document backup strategy for production deployment (Phase 7+); use MinIO replication for critical data.

---

### A13: Localhost Port Availability
**Assumption**: Ports 5432 (postgres), 6379 (redis), 8000 (mcp-server), 8081 (airflow), 9000-9001 (minio), 8181 (iceberg), 8082 (trino), 4040 (ngrok) are available on localhost.

**Rationale**: docker-compose.yml maps container ports to host ports; conflicts cause services to fail.

**Risk if Invalid**: Port binding fails, services cannot start (e.g., "port 5432 already in use").

**Validation**: setup-local.sh checks port availability:
```bash
for port in 5432 6379 8000 8081 9000 9001 8181 8082 4040; do
  if lsof -i :$port; then
    echo "Error: Port $port already in use"
    exit 1
  fi
done
```

**Mitigation**: Document port conflicts in troubleshooting guide; allow port customization via .env.production.

---

## Security Assumptions

### A14: .env.production Not Committed to Git
**Assumption**: Developers follow security best practice and never commit .env.production to version control.

**Rationale**: .env.production contains sensitive API keys (watsonx.ai, AstraDB, ngrok).

**Risk if Invalid**: Secrets leaked in git history, unauthorized access to cloud resources.

**Validation**: .gitignore includes .env.production; pre-commit hook runs detect-secrets.

**Mitigation**: Document in README.md (bold warning); use detect-secrets to scan commits; revoke leaked keys immediately.

---

### A15: API Keys Have Minimal Permissions
**Assumption**: IBM watsonx.ai API keys and AstraDB tokens are scoped to minimum required permissions (no admin access).

**Rationale**: Principle of least privilege; limits damage if keys leaked.

**Risk if Invalid**: Leaked key allows unauthorized resource creation, data deletion.

**Validation**: Manually verify permissions in IBM Cloud IAM console and AstraDB console.

**Mitigation**: Document permission requirements in .env.production.example:
- watsonx.ai: "Viewer" role on project (read-only model inference)
- AstraDB: Token scoped to single keyspace (esg_vectors) with read/write, no admin

---

## Testing Assumptions

### A16: Hypothesis Property Tests Use Finite Input Space
**Assumption**: Property-based tests (hypothesis library) use finite input generators to avoid infinite loops.

**Rationale**: @given(service_pairs: List[Tuple[str, str]]) for network tests must sample from 9 services, not arbitrary strings.

**Risk if Invalid**: Property tests run indefinitely, CI/CD pipeline times out.

**Validation**: Hypothesis tests include max_examples parameter:
```python
@given(st.lists(st.sampled_from(SERVICES), min_size=2, max_size=2))
@settings(max_examples=50)
```

**Mitigation**: Document Hypothesis test guidelines in tests/README.md; set global max_examples in pytest.ini.

---

### A17: Coverage Target Realistic for Shell Scripts
**Assumption**: ≥95% line coverage target applies to Python files only, not bash scripts (setup-local.sh, test-local.sh).

**Rationale**: Bash coverage tooling (kcov) is complex; scripts are validated via integration tests (they run successfully).

**Risk if Invalid**: Bash scripts have bugs not caught by tests.

**Validation**: Integration test `test_setup_script_succeeds()` runs setup-local.sh and asserts exit code 0.

**Mitigation**: Use shellcheck for static analysis of bash scripts; document that coverage applies to .py files only.

---

## Deployment Assumptions

### A18: IBM Code Engine Future Deployment Compatible
**Assumption**: Dockerfiles created for Phase 1 (Dockerfile.airflow, Dockerfile.mcp) are compatible with IBM Code Engine without modification.

**Rationale**: Code Engine runs Docker containers; if Dockerfile works locally, it works in Code Engine (modulo environment variables).

**Risk if Invalid**: Code Engine deployment fails due to platform-specific issues (e.g., read-only filesystem, no privileged mode).

**Validation**: Dockerfile uses non-root user, no privileged operations, 12-factor app principles (env vars for config).

**Mitigation**: Document Code Engine-specific configuration in Opus_Full_Implementation_Plan.md (Phase 7); test in Code Engine sandbox before production.

---

**Total Assumptions**: 18
**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: All Assumptions Documented
**Next**: Create cp_paths.json
