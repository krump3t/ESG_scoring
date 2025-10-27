# Hypothesis & Success Criteria - Phase 1: Production Integration - Core Infrastructure

**Task ID**: 016-production-integration-phase1
**Phase**: 1 (Infrastructure Setup)
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA
**Parent Plan**: Opus_Full_Implementation_Plan.md

---

## Primary Hypothesis

**The ESG Evaluation platform successfully integrates production-grade infrastructure components (AstraDB, watsonx.ai, DuckDB, Airflow, ngrok) with Docker containerization, enabling authentic local development and testing before IBM Code Engine deployment.**

### Core Claims
1. All production dependencies install successfully without conflicts
2. Docker Compose orchestrates 9 services (minio, iceberg, trino, redis, airflow, mcp-server, ngrok, astradb-tunnel, app) with 100% health check pass rate
3. Environment configuration (.env.production) correctly loads all IBM Cloud credentials
4. Container networking enables cross-service communication
5. ngrok tunnel exposes MCP server with stable public URL

---

## Success Criteria (SC1-SC5)

### SC1: Dependency Installation Success
**Statement**: All production dependencies install cleanly with zero conflicts

**Dependencies Added**:
```
ibm-watsonx-ai>=0.2.0
cassandra-driver>=3.28.0
duckdb>=0.9.2
apache-airflow[docker]==2.7.3
pyngrok>=6.0.0
redis>=5.0.0
python-dotenv>=1.0.0
```

**Success Metric**:
```bash
pip install -r requirements.txt --dry-run  # No conflicts
pip check  # No broken dependencies
```

**Measurement**:
```python
# Test imports
import ibm_watsonx_ai
from cassandra.cluster import Cluster
import duckdb
from airflow import DAG
import pyngrok
import redis
from dotenv import load_dotenv

# All imports succeed with zero ModuleNotFoundError
```

---

### SC2: Docker Compose Services Start Successfully
**Statement**: All 9 services start with 100% health check pass rate

**Services**:
1. minio (S3-compatible object storage)
2. iceberg-rest (Iceberg REST catalog)
3. trino (Query engine)
4. redis (Caching layer)
5. airflow-webserver (Orchestration UI)
6. airflow-scheduler (DAG scheduler)
7. mcp-server (FastAPI ESG API)
8. ngrok (Secure tunnel)
9. postgres (Airflow metadata DB)

**Success Metric**:
```bash
docker-compose up -d
docker-compose ps | grep -c "Up (healthy)"  # Should return 9
```

**Measurement**:
```bash
# All services show "Up (healthy)" status
$ docker-compose ps
NAME                STATUS              PORTS
minio               Up (healthy)        9000-9001
iceberg-rest        Up (healthy)        8181
trino               Up (healthy)        8080
redis               Up (healthy)        6379
airflow-webserver   Up (healthy)        8081:8080
airflow-scheduler   Up (healthy)        -
mcp-server          Up (healthy)        8000
ngrok               Up (healthy)        4040
postgres            Up (healthy)        5432
```

---

### SC3: Environment Configuration Loaded Correctly
**Statement**: All IBM Cloud credentials and configuration values load from .env.production

**Required Environment Variables**:
```bash
# IBM watsonx.ai (mandatory)
IBM_WATSONX_API_KEY
IBM_WATSONX_PROJECT_ID
IBM_WATSONX_URL

# AstraDB (mandatory)
ASTRA_DB_APPLICATION_TOKEN
ASTRA_DB_ID
ASTRA_DB_REGION
ASTRA_DB_KEYSPACE

# ngrok (mandatory)
NGROK_AUTH_TOKEN

# MCP Server (generated)
MCP_API_KEY

# DuckDB (local paths)
DUCKDB_PATH
PARQUET_BASE_PATH

# Redis
REDIS_HOST
REDIS_PORT
```

**Success Metric**:
```python
import os
from dotenv import load_dotenv

load_dotenv(".env.production")

assert os.getenv("IBM_WATSONX_API_KEY") is not None
assert os.getenv("ASTRA_DB_APPLICATION_TOKEN") is not None
assert os.getenv("NGROK_AUTH_TOKEN") is not None
assert os.getenv("MCP_API_KEY") is not None
```

**Measurement**: Zero AssertionError when running validation script

---

### SC4: Container Networking Functional
**Statement**: Services can communicate across Docker bridge network

**Network Tests**:
1. **mcp-server → redis**: Cache write/read
2. **mcp-server → postgres**: Airflow metadata query
3. **airflow-webserver → mcp-server**: HTTP health check
4. **ngrok → mcp-server**: Tunnel established

**Success Metric**:
```bash
# From mcp-server container
docker exec mcp-server redis-cli -h redis PING  # PONG
docker exec mcp-server curl http://airflow-webserver:8080/health  # {"status":"healthy"}

# From host
curl http://localhost:8000/health  # {"status":"ok"}
```

**Measurement**: All 4 network tests return expected responses

---

### SC5: ngrok Tunnel Stability
**Statement**: ngrok tunnel remains stable for ≥5 minutes with public URL accessible

**Success Metric**:
```bash
# Get ngrok public URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')

# Test public access (with API key)
curl -X POST "$NGROK_URL/health" \
  -H "X-API-Key: $MCP_API_KEY" \
  -H "Content-Type: application/json"  # {"status":"ok"}

# Verify tunnel stability (5-minute uptime)
sleep 300
curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].metrics.conns.count'  # ≥ 0 (no errors)
```

**Measurement**: Tunnel accessible externally with zero downtime over 5 minutes

---

## Acceptance Criteria

**Phase 1 passes when ALL of the following are true**:

1. ✅ requirements.txt updated with 7+ new dependencies (SC1)
2. ✅ `pip install -r requirements.txt` succeeds with zero conflicts (SC1)
3. ✅ .env.production created with all 11+ required variables (SC3)
4. ✅ docker-compose.yml updated with 9 service definitions (SC2)
5. ✅ `docker-compose up -d` starts all services (SC2)
6. ✅ All 9 services show "Up (healthy)" status (SC2)
7. ✅ Container networking tests pass (4/4) (SC4)
8. ✅ ngrok tunnel stable for 5+ minutes (SC5)
9. ✅ Integration tests passing: `tests/infrastructure/test_docker_services.py` (15+ tests, @pytest.mark.cp)
10. ✅ Coverage: ≥95% line, ≥90% branch on CP files
11. ✅ MEA validation: status == "ok"

---

## Power Analysis & Sample Size

**Services Tested**: 9 (complete infrastructure stack)
- Rationale: All services required for production deployment

**Network Paths**: 4 (covers all critical service interactions)
- Rationale: Validates Docker bridge network and inter-service communication

**Stability Window**: 5 minutes (baseline for tunnel uptime)
- Rationale: Sufficient to detect immediate failures; production monitoring will extend to 24+ hours

**Confidence Level**: 95% (standard for infrastructure validation)

---

## Risks & Mitigation

### Risk 1: Docker Desktop Resource Limits
**Risk**: 9 services exceed default Docker Desktop limits (4GB RAM, 2 CPUs) → services OOM/crash

**Mitigation**:
- Document minimum requirements: 8GB RAM, 4 CPUs
- Configure resource limits in docker-compose.yml:
  ```yaml
  services:
    mcp-server:
      deploy:
        resources:
          limits:
            memory: 1G
            cpus: '0.5'
  ```
- Add health check retries (3 attempts, 10s interval)

**Contingency**: Use Docker Swarm or Kubernetes for heavier workloads

---

### Risk 2: IBM Cloud API Key Expiration
**Risk**: API keys expire → services fail to authenticate

**Mitigation**:
- Document key rotation process in .env.production.example
- Add validation script: `scripts/validate-credentials.sh`
  ```bash
  # Test watsonx.ai connectivity
  python -c "from ibm_watsonx_ai import Credentials; ..."
  ```
- Set reminder in README: "Rotate API keys every 90 days"

**Contingency**: Use IBM Cloud Secrets Manager for automatic rotation (future)

---

### Risk 3: AstraDB Free Tier Quota Limits
**Risk**: Free tier limits (5GB storage, 20M reads/month) exceeded → service degradation

**Mitigation**:
- Monitor usage via AstraDB console
- Implement query throttling (100 req/hour via rate limiter)
- Use Redis caching to reduce AstraDB queries by 70%+

**Contingency**: Upgrade to pay-as-you-go tier if needed

---

### Risk 4: ngrok Tunnel Disconnection
**Risk**: ngrok tunnel drops after hours → MCP server inaccessible

**Mitigation**:
- Implement health check script: `scripts/monitor-ngrok.sh`
  ```bash
  while true; do
    if ! curl -s http://localhost:4040/api/tunnels | jq -e '.tunnels[0]'; then
      docker-compose restart ngrok
    fi
    sleep 60
  done
  ```
- Add reconnection logic in ngrok container
- Document Cloudflare Tunnel as alternative

**Contingency**: Switch to Cloudflare Tunnel for production stability

---

### Risk 5: Dependency Conflicts (Airflow + watsonx.ai)
**Risk**: Airflow 2.7.3 and ibm-watsonx-ai have conflicting transitive dependencies (e.g., protobuf, grpcio)

**Mitigation**:
- Use `pip install --dry-run` to detect conflicts before actual install
- Pin specific versions if conflicts arise:
  ```
  protobuf==4.24.4
  grpcio==1.59.0
  ```
- Isolate Airflow in separate Docker container (already planned)

**Contingency**: Use virtual environments or Docker layer caching to isolate dependencies

---

## Exclusions & Out-of-Scope

- **IBM Code Engine Deployment**: Phase 1 is local Docker only
- **Production Secrets Management**: Using .env.production (not Vault/Secrets Manager)
- **Horizontal Scaling**: Single-instance services only
- **SSL/TLS**: ngrok provides HTTPS; internal services use HTTP
- **Backup/Recovery**: Data persistence via Docker volumes; no automated backups yet
- **Monitoring/Alerting**: Basic health checks only; no Prometheus/Grafana yet

---

## Critical Path Files

### CP1: `requirements.txt`
**Lines**: +7 (additions only)
**Rationale**: All production dependencies must install cleanly
**Coverage Target**: N/A (dependency manifest)

### CP2: `docker-compose.yml`
**Lines**: +120 (9 service definitions)
**Rationale**: Core infrastructure orchestration
**Coverage Target**: Validated via `docker-compose config` and health checks

### CP3: `.env.production` (template)
**Lines**: 20-25
**Rationale**: Centralized configuration for all services
**Coverage Target**: N/A (configuration file)

### CP4: `infrastructure/Dockerfile.mcp`
**Lines**: 20-30
**Rationale**: MCP server containerization
**Coverage Target**: Built successfully via `docker build`

### CP5: `infrastructure/Dockerfile.airflow`
**Lines**: 30-40
**Rationale**: Airflow webserver/scheduler containerization
**Coverage Target**: Built successfully via `docker build`

### CP6: `scripts/setup-local.sh`
**Lines**: 80-100
**Rationale**: Turnkey local environment setup
**Coverage Target**: Executes without errors in CI/CD

### CP7: `scripts/test-local.sh`
**Lines**: 60-80
**Rationale**: Validates all services are healthy
**Coverage Target**: All 9 service tests pass

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Hypothesis & Success Criteria Complete
**Next**: Create design.md
