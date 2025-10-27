# Architecture Decision Records (ADR) - Phase 1: Production Integration

**Task ID**: 016-production-integration-phase1
**Date**: 2025-10-24
**SCA Protocol**: v13.8-MEA

---

## ADR-001: Use Docker Compose Over Kubernetes for Local Development

**Status**: Accepted
**Date**: 2025-10-24
**Decision Makers**: User (Product Owner), SCA v13.8-MEA

### Context
The ESG Evaluation platform requires local containerized deployment for development and testing before IBM Code Engine production deployment (months away). Two orchestration options: Docker Compose vs. Kubernetes (minikube/kind).

### Decision
Use **Docker Compose** for local development.

### Rationale
- **Simplicity**: Single `docker-compose.yml` file vs. multiple Kubernetes manifests (deployments, services, ingress, configmaps)
- **Resource Efficiency**: Docker Compose has lower overhead (no etcd, control plane) → fits within 8GB RAM, 4 CPU target
- **Faster Iteration**: `docker-compose up -d` is faster than `kubectl apply` + image pulls
- **Parity with Code Engine**: Code Engine uses Docker images, not Kubernetes manifests; Compose → Dockerfile → Code Engine is simpler path
- **Developer Experience**: Most developers familiar with Docker Compose; Kubernetes adds complexity for single-node local setup

### Consequences
**Positive**:
- Faster setup (<10 minutes vs. 30+ minutes for Kubernetes)
- Easier debugging (docker logs vs. kubectl logs + namespace complexity)
- Lighter resource footprint

**Negative**:
- No auto-scaling (acceptable for local development)
- No rolling updates (not needed locally; use docker-compose down/up)
- Different from Kubernetes-based Code Engine (mitigation: Dockerfile portability ensures smooth transition)

### Alternatives Considered
1. **Kubernetes (minikube)**: Rejected due to complexity and resource overhead for local dev
2. **Podman Compose**: Rejected due to compatibility issues with ngrok Docker image
3. **Bare Metal (pip install)**: Rejected due to dependency conflicts (Airflow + watsonx.ai)

---

## ADR-002: Use LocalExecutor for Airflow (Not CeleryExecutor)

**Status**: Accepted
**Date**: 2025-10-24
**Decision Makers**: SCA v13.8-MEA

### Context
Airflow supports multiple executors: LocalExecutor (single-node, sequential task execution), CeleryExecutor (distributed, parallel execution with Redis/RabbitMQ backend), KubernetesExecutor (tasks as pods).

### Decision
Use **LocalExecutor** for Phase 1 local development.

### Rationale
- **Simplicity**: No Celery workers, no RabbitMQ dependency → 1 fewer service in docker-compose.yml
- **Single-Node Workload**: Phase 1 processes 1 company at a time sequentially (no parallelism required)
- **Lower Resource Usage**: LocalExecutor runs tasks in subprocess (no worker overhead)
- **Faster Debugging**: Task logs directly in scheduler process (no distributed tracing needed)

### Consequences
**Positive**:
- Simpler docker-compose.yml (no celery-worker service)
- Faster task execution for low-concurrency workloads
- Easier debugging (single process to inspect)

**Negative**:
- Cannot scale horizontally (tasks execute sequentially)
- Phase 6+ may require CeleryExecutor for parallel company processing (migration path exists)

### Alternatives Considered
1. **CeleryExecutor**: Rejected due to added complexity (RabbitMQ/Redis backend, multiple workers) for single-company workload
2. **SequentialExecutor**: Rejected because it doesn't support parallel task execution within a DAG (LocalExecutor can run multiple tasks if DAG allows)

---

## ADR-003: Use ngrok Over Cloudflare Tunnel for MCP Server Exposure

**Status**: Accepted (Provisional)
**Date**: 2025-10-24
**Decision Makers**: User (specified ngrok in requirements), SCA v13.8-MEA

### Context
The MCP server must be accessible via public HTTPS URL for remote testing. Two options: ngrok (secure tunneling SaaS) vs. Cloudflare Tunnel (free, more stable).

### Decision
Use **ngrok** for Phase 1, with Cloudflare Tunnel as documented fallback.

### Rationale
- **User Requirement**: User explicitly requested ngrok in original requirements ("public ngrok endpoint to send queries")
- **Faster Setup**: ngrok requires only auth token (no domain configuration like Cloudflare Tunnel)
- **Developer Familiarity**: ngrok widely used for local dev tunneling
- **Dashboard**: ngrok provides /api/tunnels endpoint for public URL retrieval and metrics

### Consequences
**Positive**:
- Single-command setup: `ngrok http mcp-server:8000`
- Public URL immediately available via API
- Built-in request inspector (http://localhost:4040)

**Negative**:
- **Free Tier Limits**: 2-hour session limit, 1 tunnel max, random URLs (no custom domains)
- **Tunnel Instability**: Free tier can disconnect unexpectedly (mitigation: health check + auto-restart script in design.md)
- **Cost for Stability**: Pro tier ($10/month) required for 24+ hour sessions

### Alternatives Considered
1. **Cloudflare Tunnel**: Rejected for Phase 1 due to user's explicit ngrok requirement; documented as fallback in Opus_Full_Implementation_Plan.md (Phase 6)
2. **AWS API Gateway + Lambda**: Rejected due to added complexity and AWS cost vs. free ngrok
3. **Tailscale**: Rejected because it's VPN-based (requires client setup), not public HTTP endpoint

### Migration Path
If ngrok proves unstable in Phase 2+, switch to Cloudflare Tunnel:
```yaml
# docker-compose.yml
cloudflared:
  image: cloudflare/cloudflared:latest
  command: tunnel run --token ${CLOUDFLARE_TUNNEL_TOKEN}
```

---

## ADR-004: Use .env.production for Secrets (Not Vault/Secrets Manager)

**Status**: Accepted (Temporary)
**Date**: 2025-10-24
**Decision Makers**: SCA v13.8-MEA

### Context
The application requires sensitive credentials (IBM watsonx.ai API key, AstraDB token, ngrok auth token). Options: .env files, HashiCorp Vault, IBM Cloud Secrets Manager, Kubernetes Secrets.

### Decision
Use **.env.production** for Phase 1 local development, with explicit documentation that this is NOT production-grade.

### Rationale
- **Simplicity**: Single file, no external service dependencies
- **Local Development Focus**: Phase 1 is local testing only (no cloud deployment)
- **Docker Compose Integration**: `env_file: .env.production` natively supported
- **Explicit Temporary Status**: User requirement stated "local development first, Code Engine months away"

### Consequences
**Positive**:
- Zero-setup secret management (no Vault installation)
- Easy debugging (secrets visible in .env.production for troubleshooting)
- Fast iteration (edit .env, restart container)

**Negative**:
- **Security Risk**: .env.production must NEVER be committed to version control (git-ignored, documented in data_sources.json)
- **No Rotation Automation**: Manual key rotation every 90 days (documented in .env.production.example)
- **No Audit Trail**: No logging of secret access (acceptable for local dev)

### Migration Path
**For IBM Code Engine Deployment** (Phase 7+):
- Migrate to IBM Cloud Secrets Manager
- Store secrets as Code Engine environment variables (encrypted at rest)
- Use IAM service-to-service auth for watsonx.ai (no API keys)

---

## ADR-005: Use AstraDB Over Self-Hosted Cassandra for Vector Storage

**Status**: Accepted
**Date**: 2025-10-24
**Decision Makers**: User (specified AstraDB in requirements), SCA v13.8-MEA

### Context
The application requires vector database for embeddings storage. Options: AstraDB (managed Cassandra), self-hosted Cassandra, pgvector (Postgres extension), Pinecone (vector DB SaaS).

### Decision
Use **AstraDB** (DataStax managed Cassandra with vector search).

### Rationale
- **User Requirement**: User explicitly specified "AstraDB" in original requirements
- **Managed Service**: No operational overhead (backups, scaling, patching handled by DataStax)
- **Vector Search Support**: Native VECTOR<FLOAT, 384> type + ANN index (StorageAttachedIndex)
- **Free Tier**: 5GB storage, 20M reads/month (sufficient for PoC)
- **IBM Cloud Integration**: AstraDB available in IBM Cloud Marketplace (future Code Engine integration)

### Consequences
**Positive**:
- Zero infrastructure management (no Cassandra cluster to run locally)
- Production-grade vector search (cosine similarity via ANN index)
- Cloud-based (accessible from any environment, not just localhost)

**Negative**:
- **Network Dependency**: Requires internet connection (vs. local Cassandra)
- **Free Tier Limits**: 5GB storage cap (sufficient for 10K+ documents with 384-dim embeddings)
- **Vendor Lock-In**: Migrating off AstraDB requires CQL export + reimport

### Alternatives Considered
1. **Self-Hosted Cassandra**: Rejected due to operational complexity (3-node cluster minimum for quorum)
2. **pgvector (Postgres)**: Rejected because Postgres already used for Airflow metadata (separate concerns)
3. **Pinecone**: Rejected due to cost ($70/month for production tier) vs. free AstraDB

---

## ADR-006: Use DuckDB Over Trino for Local Analytics

**Status**: Accepted
**Date**: 2025-10-24
**Decision Makers**: SCA v13.8-MEA

### Context
The application requires SQL analytics over Parquet data lake. Existing infrastructure includes Trino (query engine). Options: DuckDB (embedded), Trino (distributed), Spark (batch processing).

### Decision
Use **DuckDB** for local analytics, keep Trino for future production use.

### Rationale
- **Embedded Database**: Zero-setup, no server required (duckdb.connect() in Python)
- **Parquet Native**: Fast Parquet scans without ETL (read_parquet('*.parquet'))
- **Low Resource Usage**: <100MB RAM for 1M row queries (vs. Trino 2GB+ JVM heap)
- **Local Development Focus**: Phase 1 is single-node, no distributed queries needed
- **Trino Preservation**: Keep Trino in docker-compose.yml for future multi-node analytics

### Consequences
**Positive**:
- Instant query execution (no JVM startup delay)
- Arrow integration (zero-copy to pandas/pyarrow)
- SQL-only aggregations (no Spark/PySpark dependencies)

**Negative**:
- **Single-Node Limitation**: Cannot scale beyond single machine (acceptable for PoC)
- **No Federated Queries**: DuckDB cannot join Parquet + Postgres (Trino can; future use case)

### Alternatives Considered
1. **Trino Only**: Rejected due to JVM overhead and complexity for local single-node analytics
2. **Apache Spark**: Rejected due to massive resource requirements (4GB+ driver memory)
3. **Pandas Only**: Rejected because it loads entire Parquet file into RAM (DuckDB scans on disk)

---

## ADR-007: Generate Secrets Locally (Not Pre-Generated)

**Status**: Accepted
**Date**: 2025-10-24
**Decision Makers**: SCA v13.8-MEA

### Context
The application requires generated secrets (MCP_API_KEY, AIRFLOW_FERNET_KEY) that are not provider-issued. Options: pre-generate and commit to repo, generate during setup, use placeholder values.

### Decision
**Generate secrets locally during setup** via setup-local.sh script.

### Rationale
- **Security Best Practice**: Never commit secrets to version control (even in .env.example)
- **Unique Per Environment**: Each developer/deployment gets unique secrets (no shared keys)
- **Automated Generation**: setup-local.sh auto-generates if missing (zero manual effort)
- **Cryptographically Secure**: Use Python secrets module (CSPRNG) for key generation

### Consequences
**Positive**:
- No risk of leaked secrets in git history
- Each local environment isolated (keys not shared)
- Turnkey setup (no manual copy-paste from documentation)

**Negative**:
- **.env.production Not Portable**: Cannot copy .env.production between machines (must regenerate)
- **Regeneration Risk**: Running setup-local.sh again overwrites existing keys (mitigation: check if .env.production exists first)

### Implementation
```bash
# In setup-local.sh
if [ ! -f .env.production ]; then
  echo "Generating MCP_API_KEY..."
  MCP_API_KEY=$(python -c "import secrets; print(secrets.token_hex(16))")

  echo "Generating AIRFLOW_FERNET_KEY..."
  AIRFLOW_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

  cat > .env.production <<EOF
MCP_API_KEY=$MCP_API_KEY
AIRFLOW_FERNET_KEY=$AIRFLOW_FERNET_KEY
# ... other vars
EOF
fi
```

---

**Total ADRs**: 7
**Prepared By**: Scientific Coding Agent v13.8-MEA
**Status**: All ADRs Accepted
**Next**: Create assumptions.md
