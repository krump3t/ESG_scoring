# Architecture Decision Records (ADR)

## ADR-001: Local-First Infrastructure
**Date**: 2025-10-21
**Status**: Accepted
**Context**: Need to minimize cloud dependencies and costs during development
**Decision**: Use MinIO for S3-compatible storage, run all services locally via Docker
**Consequences**:
- (+) Full control, no cloud costs, faster iteration
- (+) Easy to replicate across developer machines
- (-) Need to manage Docker resources carefully
- (-) Different from production cloud environment

## ADR-002: Apache Iceberg as Table Format
**Date**: 2025-10-21
**Status**: Accepted
**Context**: Need ACID transactions, schema evolution, and time travel for audit
**Decision**: Use Apache Iceberg for silver and gold layers
**Consequences**:
- (+) Full transaction support with snapshot isolation
- (+) Hidden partitioning reduces user errors
- (+) Time travel enables reproducible analysis
- (-) Additional complexity vs plain Parquet
- (-) Requires catalog service

## ADR-003: MCP for Multi-Agent Communication
**Date**: 2025-10-21
**Status**: Accepted
**Context**: Need standardized tool interfaces between agents
**Decision**: Implement Model Context Protocol (MCP) for all agent tools
**Consequences**:
- (+) Standard protocol with clear specifications
- (+) Supports both stdio and HTTP transports
- (+) Built-in error handling and capability negotiation
- (-) Additional abstraction layer
- (-) Limited ecosystem (new protocol)

## ADR-004: Trino as SQL Engine
**Date**: 2025-10-21
**Status**: Accepted
**Context**: Need distributed SQL queries across Iceberg tables
**Decision**: Use Trino with native Iceberg connector
**Consequences**:
- (+) Excellent Iceberg support including time travel
- (+) Can federate queries across multiple sources
- (+) Good performance for analytical queries
- (-) Resource intensive for small datasets
- (-) Another service to manage

## ADR-005: Keep watsonx.ai and AstraDB in Cloud
**Date**: 2025-10-21
**Status**: Accepted
**Context**: Already have working cloud services with credentials
**Decision**: Continue using watsonx.ai for LLM and AstraDB for vector/graph
**Consequences**:
- (+) No migration needed for these components
- (+) Proven reliability and performance
- (+) Reduced local resource requirements
- (-) Network latency for API calls
- (-) Ongoing cloud costs

## ADR-006: Docker Compose for Orchestration
**Date**: 2025-10-21
**Status**: Accepted
**Context**: Need reproducible multi-service deployment
**Decision**: Use Docker Compose for local orchestration
**Consequences**:
- (+) Simple, declarative configuration
- (+) Easy to share and version control
- (+) Good for development environments
- (-) Not suitable for production
- (-) Limited orchestration features vs Kubernetes

## ADR-007: REST Catalog for Iceberg
**Date**: 2025-10-21
**Status**: Proposed
**Context**: Need catalog service for Iceberg table metadata
**Decision**: Use Iceberg REST Catalog (or Nessie as alternative)
**Alternatives Considered**:
- Hive Metastore (too heavy, requires Hadoop)
- AWS Glue (cloud-only)
- Nessie (git-like branching, more complex)
**Consequences**:
- (+) Lightweight, purpose-built for Iceberg
- (+) Simple HTTP API
- (-) Less mature than Hive Metastore
- (-) Limited features vs Nessie