# Design Document - Phase 1: Production Integration - Core Infrastructure

**Task ID**: 016-production-integration-phase1
**Phase**: 1 (Infrastructure Setup)
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│              Local Docker Development Environment            │
└─────────────────────────────────────────────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       │                        │                        │
┌──────▼──────┐        ┌───────▼───────┐      ┌────────▼────────┐
│   Data      │        │  Application  │      │   External      │
│  Services   │        │   Services    │      │   Services      │
└─────────────┘        └───────────────┘      └─────────────────┘
│                      │                      │
├─ MinIO (S3)         ├─ MCP Server          ├─ ngrok Tunnel
├─ Iceberg REST       ├─ Airflow Web         │  (public HTTPS)
├─ Trino              ├─ Airflow Sched       │
├─ Redis              └─ Postgres (meta)     ├─ IBM watsonx.ai
└─ DuckDB (local)                             │  (API calls)
                                              │
                                              └─ AstraDB
                                                 (cloud database)
```

---

## Docker Compose Service Definitions

### 1. MinIO (S3-Compatible Object Storage)
**Purpose**: Local object storage for raw data, artifacts, logs
**Image**: `minio/minio:RELEASE.2024-10-13T13-34-11Z`
**Ports**: 9000 (API), 9001 (Console)
**Volumes**: `minio_data:/data`
**Health Check**: `curl -f http://localhost:9000/minio/health/live`

**Configuration**:
```yaml
minio:
  image: minio/minio:RELEASE.2024-10-13T13-34-11Z
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  ports:
    - "9000:9000"
    - "9001:9001"
  volumes:
    - minio_data:/data
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
    interval: 30s
    timeout: 10s
    retries: 3
```

---

### 2. Iceberg REST Catalog
**Purpose**: Iceberg table metadata management
**Image**: `tabulario/iceberg-rest:1.5.0`
**Ports**: 8181
**Volumes**: `iceberg_warehouse:/warehouse`
**Health Check**: `curl -f http://localhost:8181/v1/config`

**Configuration**:
```yaml
iceberg-rest:
  image: tabulario/iceberg-rest:1.5.0
  environment:
    CATALOG_WAREHOUSE: /warehouse
    CATALOG_IO_IMPL: org.apache.iceberg.aws.s3.S3FileIO
    CATALOG_S3_ENDPOINT: http://minio:9000
  ports:
    - "8181:8181"
  volumes:
    - iceberg_warehouse:/warehouse
  depends_on:
    - minio
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8181/v1/config"]
    interval: 30s
    timeout: 10s
    retries: 3
```

---

### 3. Trino (Query Engine)
**Purpose**: SQL query engine for Parquet/Iceberg data
**Image**: `trinodb/trino:438`
**Ports**: 8080
**Volumes**: `trino_catalog:/etc/trino/catalog`
**Health Check**: `curl -f http://localhost:8080/v1/info`

**Configuration**:
```yaml
trino:
  image: trinodb/trino:438
  ports:
    - "8082:8080"  # Changed to avoid conflict with Airflow
  volumes:
    - ./infrastructure/trino/catalog:/etc/trino/catalog
  depends_on:
    - minio
    - iceberg-rest
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/v1/info"]
    interval: 30s
    timeout: 10s
    retries: 3
```

---

### 4. Redis (Caching Layer)
**Purpose**: Cache embeddings, API responses, session data
**Image**: `redis:7-alpine`
**Ports**: 6379
**Volumes**: `redis_data:/data`
**Health Check**: `redis-cli ping`

**Configuration**:
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 3
```

---

### 5. PostgreSQL (Airflow Metadata DB)
**Purpose**: Store Airflow DAG runs, task instances, connections
**Image**: `postgres:15-alpine`
**Ports**: 5432
**Volumes**: `postgres_data:/var/lib/postgresql/data`
**Health Check**: `pg_isready -U airflow`

**Configuration**:
```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_USER: airflow
    POSTGRES_PASSWORD: airflow
    POSTGRES_DB: airflow
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U airflow"]
    interval: 10s
    timeout: 5s
    retries: 5
```

---

### 6. Airflow Webserver
**Purpose**: Airflow UI for DAG management
**Build**: `infrastructure/Dockerfile.airflow`
**Ports**: 8081 (mapped to 8080 internally)
**Volumes**: `./pipelines/airflow/dags:/opt/airflow/dags`
**Health Check**: `curl -f http://localhost:8080/health`

**Configuration**:
```yaml
airflow-webserver:
  build:
    context: .
    dockerfile: infrastructure/Dockerfile.airflow
  command: webserver
  environment:
    AIRFLOW__CORE__EXECUTOR: LocalExecutor
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
    AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
    AIRFLOW__CORE__LOAD_EXAMPLES: "false"
  env_file:
    - .env.production
  ports:
    - "8081:8080"
  volumes:
    - ./pipelines/airflow/dags:/opt/airflow/dags
    - ./logs:/opt/airflow/logs
  depends_on:
    - postgres
    - redis
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

---

### 7. Airflow Scheduler
**Purpose**: Schedule and execute DAG tasks
**Build**: `infrastructure/Dockerfile.airflow`
**No Exposed Ports**: Internal service only
**Health Check**: `airflow jobs check --job-type SchedulerJob`

**Configuration**:
```yaml
airflow-scheduler:
  build:
    context: .
    dockerfile: infrastructure/Dockerfile.airflow
  command: scheduler
  environment:
    AIRFLOW__CORE__EXECUTOR: LocalExecutor
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
    AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
  env_file:
    - .env.production
  volumes:
    - ./pipelines/airflow/dags:/opt/airflow/dags
    - ./logs:/opt/airflow/logs
  depends_on:
    - postgres
    - redis
  healthcheck:
    test: ["CMD-SHELL", "airflow jobs check --job-type SchedulerJob --hostname $(hostname)"]
    interval: 30s
    timeout: 10s
    retries: 3
```

---

### 8. MCP Server (FastAPI ESG API)
**Purpose**: ESG maturity assessment API with MCP protocol
**Build**: `infrastructure/Dockerfile.mcp`
**Ports**: 8000
**Volumes**: `./data_lake:/app/data_lake`
**Health Check**: `curl -f http://localhost:8000/health`

**Configuration**:
```yaml
mcp-server:
  build:
    context: .
    dockerfile: infrastructure/Dockerfile.mcp
  command: uvicorn mcp_server.server:app --host 0.0.0.0 --port 8000
  environment:
    REDIS_HOST: redis
    REDIS_PORT: 6379
  env_file:
    - .env.production
  ports:
    - "8000:8000"
  volumes:
    - ./data_lake:/app/data_lake
    - ./logs:/app/logs
  depends_on:
    - redis
    - postgres
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 15s
    timeout: 5s
    retries: 3
```

---

### 9. ngrok (Secure Tunnel)
**Purpose**: Expose MCP server via public HTTPS URL
**Image**: `ngrok/ngrok:latest`
**Ports**: 4040 (ngrok dashboard)
**Environment**: `NGROK_AUTHTOKEN` from .env.production
**Health Check**: `curl -f http://localhost:4040/api/tunnels`

**Configuration**:
```yaml
ngrok:
  image: ngrok/ngrok:latest
  command: http mcp-server:8000 --log stdout
  environment:
    NGROK_AUTHTOKEN: ${NGROK_AUTH_TOKEN}
  ports:
    - "4040:4040"
  depends_on:
    - mcp-server
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:4040/api/tunnels"]
    interval: 15s
    timeout: 5s
    retries: 3
```

---

## Dockerfiles

### Dockerfile.airflow (infrastructure/Dockerfile.airflow)
```dockerfile
FROM apache/airflow:2.7.3-python3.11

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy requirements
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Initialize Airflow DB (run once)
RUN airflow db init

# Create admin user (for first-time setup)
RUN airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

EXPOSE 8080

CMD ["airflow", "webserver"]
```

---

### Dockerfile.mcp (infrastructure/Dockerfile.mcp)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/data_lake /app/logs /app/qa

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI server
CMD ["uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Environment Configuration (.env.production)

**Template**: `.env.production.example`

```bash
# ============================================================================
# IBM watsonx.ai Configuration
# ============================================================================
IBM_WATSONX_API_KEY=your-watsonx-api-key-here
IBM_WATSONX_PROJECT_ID=your-project-id-here
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com

# ============================================================================
# AstraDB Configuration
# ============================================================================
ASTRA_DB_APPLICATION_TOKEN=your-astradb-token-here
ASTRA_DB_ID=your-database-id-here
ASTRA_DB_REGION=us-east1
ASTRA_DB_KEYSPACE=esg_vectors

# ============================================================================
# ngrok Configuration
# ============================================================================
NGROK_AUTH_TOKEN=your-ngrok-auth-token-here

# ============================================================================
# MCP Server Configuration
# ============================================================================
# Generate random 32-char hex: python -c "import secrets; print(secrets.token_hex(16))"
MCP_API_KEY=your-generated-api-key-here
MCP_RATE_LIMIT=100

# ============================================================================
# DuckDB Configuration
# ============================================================================
DUCKDB_PATH=data_lake/analytics.duckdb
PARQUET_BASE_PATH=data_lake/parquet/

# ============================================================================
# Redis Configuration
# ============================================================================
REDIS_HOST=redis
REDIS_PORT=6379

# ============================================================================
# Airflow Configuration
# ============================================================================
# Generate Fernet key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
AIRFLOW_FERNET_KEY=your-fernet-key-here
```

---

## Setup Scripts

### scripts/setup-local.sh
**Purpose**: Automated local environment setup
**Execution Time Target**: <10 minutes

**Steps**:
1. Validate prerequisites (Docker, docker-compose, jq)
2. Check .env.production exists
3. Generate missing secrets (MCP_API_KEY, AIRFLOW_FERNET_KEY)
4. Pull Docker images
5. Build custom images (airflow, mcp-server)
6. Start infrastructure services (postgres, redis, minio)
7. Wait for health checks (30s)
8. Initialize Airflow DB
9. Start application services (airflow-webserver, mcp-server, ngrok)
10. Display ngrok public URL

**Output**:
```
ESG Evaluation Platform - Local Setup
=======================================
[✓] Docker installed
[✓] docker-compose installed
[✓] jq installed
[✓] .env.production found
[✓] Generated MCP_API_KEY
[✓] Generated AIRFLOW_FERNET_KEY
[✓] Pulling Docker images... (2 min)
[✓] Building custom images... (5 min)
[✓] Starting infrastructure services...
[✓] Waiting for health checks... (30s)
[✓] Initializing Airflow DB... (1 min)
[✓] Starting application services...
[✓] All services healthy!

MCP Server: http://localhost:8000
ngrok URL: https://abc123.ngrok.io
API Key: abc123...

Setup complete! Run 'docker-compose logs -f' to view logs.
```

---

### scripts/test-local.sh
**Purpose**: Validate all services are healthy
**Execution Time Target**: <2 minutes

**Tests**:
1. PostgreSQL connectivity
2. Redis connectivity
3. MinIO S3 API
4. Iceberg REST catalog
5. Trino query engine
6. Airflow webserver UI
7. MCP server health endpoint
8. ngrok tunnel public URL
9. Container networking (mcp → redis, mcp → postgres)

**Output**:
```
Testing ESG Evaluation Platform
================================
[✓] PostgreSQL: Connected
[✓] Redis: PONG
[✓] MinIO: S3 API responding
[✓] Iceberg REST: Catalog configured
[✓] Trino: Query engine ready
[✓] Airflow: Web UI accessible (http://localhost:8081)
[✓] MCP Server: Health check OK (http://localhost:8000/health)
[✓] ngrok: Public URL active (https://abc123.ngrok.io)
[✓] Network Test 1: mcp-server → redis (PING OK)
[✓] Network Test 2: mcp-server → postgres (Query OK)

All services healthy!
```

---

## Dependency Updates

### requirements.txt Additions
```
# Production AI/ML
ibm-watsonx-ai>=0.2.0
cassandra-driver>=3.28.0

# Data Infrastructure
duckdb>=0.9.2
apache-airflow[postgres]==2.7.3
redis>=5.0.0

# Networking & Security
pyngrok>=6.0.0
python-dotenv>=1.0.0

# Airflow Providers
apache-airflow-providers-docker==3.7.0
apache-airflow-providers-http==4.5.0
```

---

## Validation Strategy

### Health Checks
All services must pass health checks before considered "ready":
- **Interval**: 10-30s (varies by service)
- **Timeout**: 5-10s
- **Retries**: 3
- **Start Period**: 5s (grace period before checks begin)

### Integration Tests
**File**: `tests/infrastructure/test_docker_services.py`

**Test Cases** (15+ tests, all marked `@pytest.mark.cp`):
1. `test_postgres_connection()` - Validate PostgreSQL connectivity
2. `test_redis_ping()` - Validate Redis PING response
3. `test_minio_s3_api()` - Validate MinIO S3 API
4. `test_iceberg_rest_catalog()` - Validate Iceberg catalog
5. `test_trino_query_engine()` - Execute simple Trino query
6. `test_airflow_webserver_ui()` - GET http://localhost:8081
7. `test_airflow_scheduler_running()` - Check scheduler job
8. `test_mcp_server_health()` - GET http://localhost:8000/health
9. `test_ngrok_tunnel_active()` - Check ngrok API
10. `test_ngrok_public_url_accessible()` - External HTTP request
11. `test_mcp_to_redis_network()` - Container network test
12. `test_mcp_to_postgres_network()` - Container network test
13. `test_env_vars_loaded()` - Validate .env.production
14. `test_docker_volumes_created()` - Check persistent volumes
15. `test_ngrok_tunnel_stability()` - 5-minute uptime

### Property-Based Tests
**File**: `tests/infrastructure/test_docker_properties.py`

**Test Cases**:
1. `test_all_services_start_idempotently()` - @given(restart_count: int)
   - Property: Restarting services N times always results in same healthy state
2. `test_container_networking_transitive()` - @given(service_pairs: List[Tuple[str, str]])
   - Property: If A → B and B → C network paths work, A → C must work

---

## Network Architecture

### Docker Bridge Network
**Name**: `esg_network` (auto-created by docker-compose)

**Service Hostnames** (DNS resolution):
- `minio` → MinIO S3 API
- `iceberg-rest` → Iceberg REST catalog
- `trino` → Trino query engine
- `redis` → Redis cache
- `postgres` → PostgreSQL metadata DB
- `airflow-webserver` → Airflow web UI
- `airflow-scheduler` → Airflow scheduler
- `mcp-server` → MCP FastAPI server
- `ngrok` → ngrok tunnel

**Communication Patterns**:
```
mcp-server:
  → redis (cache read/write)
  → postgres (Airflow metadata query)
  → External: IBM watsonx.ai API (HTTPS)
  → External: AstraDB (HTTPS)

airflow-scheduler:
  → postgres (DAG metadata)
  → redis (Celery backend, if needed)
  → mcp-server (trigger pipelines)

ngrok:
  → mcp-server (tunnel backend)
```

---

## Success Metrics Recap

| Metric | Target | Validation |
|--------|--------|-----------|
| Dependencies installed | 7+ packages | pip check = 0 errors |
| Services started | 9/9 healthy | docker-compose ps |
| Environment vars loaded | 11+ vars | dotenv validation script |
| Container networking | 4/4 tests pass | curl from containers |
| ngrok tunnel uptime | ≥5 minutes | External URL accessible |
| Integration tests | 15+ passing | pytest -m cp |
| Coverage (scripts) | ≥95% line | pytest-cov |

---

**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: Design Document Complete
**Next**: Create evidence.json
