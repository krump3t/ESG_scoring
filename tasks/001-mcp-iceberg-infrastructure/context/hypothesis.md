# Hypothesis: MCP + Iceberg Infrastructure Foundation

## Core Hypothesis
Establishing a local-first, cloud-optional infrastructure with MinIO (S3-compatible storage), Apache Iceberg (table format), and MCP server architecture will provide a scalable, traceable, and production-ready foundation for multi-agent ESG evaluation while maintaining existing cloud services (watsonx.ai, AstraDB).

## Success Metrics
- **Infrastructure Availability**: All services running with < 5 second startup time
- **Storage Performance**: MinIO write throughput > 100 MB/s locally
- **Iceberg Catalog**: REST catalog responding to queries < 100ms
- **MCP Server**: Tool registration and invocation < 50ms overhead
- **Memory Usage**: Total stack < 4GB RAM under normal operation
- **Protocol Compliance**: All 14 SCA v13.7 gates passing

## Input/Output Specifications
**Inputs:**
- Docker/Docker Compose installation
- 50GB available disk space
- watsonx.ai API credentials
- AstraDB connection string

**Outputs:**
- Running MinIO instance with `esg-lake` bucket
- Iceberg REST catalog or Nessie server operational
- Trino/Spark SQL engine connected to Iceberg
- MCP server with base tool registration
- docker-compose.yml for reproducible deployment
- .env.template with all required variables

## Critical Path Components
- `docker-compose.yml` - Infrastructure orchestration
- `mcp_server/base_server.py` - MCP server foundation
- `iceberg/catalog_init.py` - Catalog initialization
- `storage/minio_setup.py` - S3 bucket configuration
- `config/environment.py` - Environment validation

## Exclusions
- Cloud infrastructure provisioning (using local only)
- Production-grade authentication (development credentials)
- High availability/clustering (single node for PoC)
- Backup/recovery mechanisms (snapshot-based only)

## Power Analysis & Confidence Intervals
- **Statistical Power**: N/A for infrastructure setup
- **Performance CI (95%)**: Response times 50ms ± 25ms
- **Throughput CI (95%)**: 100 MB/s ± 20 MB/s
- **Availability Target**: 99% uptime during development

## Risk Mitigators
1. **Docker daemon failure**: Provide systemd restart scripts
2. **Port conflicts**: Configurable port mapping in .env
3. **Memory exhaustion**: Resource limits in docker-compose
4. **Credential leakage**: Use .env files, never commit secrets
5. **Version conflicts**: Pin all container versions

## Verification Strategy
- Health check endpoints for all services
- Connectivity tests to cloud services
- Sample Iceberg table creation/query
- MCP tool invocation test suite
- Protocol gate validation runner