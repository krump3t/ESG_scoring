# Assumptions

## Technical Assumptions

1. **Docker Desktop Available**: Developers have Docker Desktop installed with WSL2 backend (Windows) or native Docker (Linux/Mac)

2. **Resource Availability**:
   - Minimum 8GB RAM available for Docker
   - 50GB free disk space for data and images
   - 4+ CPU cores for reasonable performance

3. **Network Connectivity**:
   - Stable internet for pulling Docker images
   - Access to watsonx.ai endpoints (us-south region)
   - Access to AstraDB cloud instances

4. **Credential Access**:
   - Valid watsonx.ai API key and project ID
   - Valid AstraDB token and endpoint
   - Permissions to create collections/tables

## Data Assumptions

1. **Data Volume**:
   - Initial POC with < 100 companies
   - < 1000 documents per company
   - Total storage < 10GB for POC phase

2. **Data Format**:
   - Sustainability reports in PDF/HTML format
   - Structured data extractable via parsing
   - English language documents primarily

3. **Data Quality**:
   - Reports follow standard formats (GRI, SASB, TCFD)
   - Numeric data is machine-readable
   - Tables and figures are extractable

## Operational Assumptions

1. **Development Environment**:
   - Single developer machine deployment
   - No high availability requirements
   - Restart acceptable for recovery

2. **Performance Expectations**:
   - Batch processing acceptable (not real-time)
   - Query response < 5 seconds acceptable
   - Sequential agent execution initially

3. **Security Model**:
   - Development credentials in .env files
   - No external access required
   - Trust within Docker network

## Migration Assumptions

1. **Gradual Migration**:
   - Can run legacy and new system in parallel
   - No immediate cutover required
   - 2-week validation period available

2. **Data Preservation**:
   - Existing AstraDB data remains accessible
   - Can replay historical scores if needed
   - Audit trail maintained throughout

3. **Rollback Capability**:
   - Can revert to legacy system if issues
   - Iceberg snapshots enable point-in-time recovery
   - No data loss during migration

## Protocol Assumptions

1. **SCA v13.7 Compliance**:
   - All gates must pass before proceeding
   - Traceability artifacts always generated
   - Snapshot save at each phase completion

2. **Testing Coverage**:
   - 95% line/branch coverage achievable
   - Property-based tests via Hypothesis
   - Differential testing between systems

3. **Documentation**:
   - All critical path code documented
   - Architecture decisions recorded
   - Reproducibility instructions maintained

## Risk Assumptions

1. **Technical Risks Manageable**:
   - Docker stability issues rare
   - Service failures recoverable
   - Data corruption detectable

2. **Timeline Flexibility**:
   - Schedule can accommodate debugging
   - Phases can be extended if needed
   - Parallel work possible on some tasks

3. **Stakeholder Alignment**:
   - Requirements stable during migration
   - Testing feedback incorporated
   - Go/no-go decisions at phase gates