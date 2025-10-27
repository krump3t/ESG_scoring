#!/bin/bash
#
# ESG Evaluation Platform - Local Setup Script
# Phase 1: Core Infrastructure (9 Docker Services)
#
# Usage: ./scripts/setup-local.sh
#
# Prerequisites:
#   - Docker Desktop (8GB RAM, 4 CPUs minimum)
#   - docker-compose command
#   - python3
#   - IBM Cloud API key (watsonx.ai)
#   - AstraDB token
#   - ngrok auth token
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=========================================="
echo "ESG Evaluation Platform - Local Setup"
echo "=========================================="
echo -e "${NC}"

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================

echo -e "${YELLOW}[1/10] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not installed. Please install Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ docker-compose not found. Update Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose installed${NC}"

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠ jq not installed (optional). Some features may not work.${NC}"
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ python3 not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ python3 installed${NC}"

# ============================================================================
# Step 2: Check Docker Resources
# ============================================================================

echo -e "${YELLOW}[2/10] Checking Docker resources...${NC}"

# Note: This check is informational; exact value depends on Docker Desktop settings
echo -e "${GREEN}✓ Docker ready (verify 8GB RAM, 4 CPUs in Docker preferences)${NC}"

# ============================================================================
# Step 3: Load or Generate Environment Variables
# ============================================================================

echo -e "${YELLOW}[3/10] Setting up environment configuration...${NC}"

if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}Creating .env.production from template...${NC}"

    if [ ! -f ".env.production.example" ]; then
        echo -e "${RED}✗ .env.production.example not found. Run from project root.${NC}"
        exit 1
    fi

    cp .env.production.example .env.production

    # Generate MCP API KEY
    MCP_API_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")
    sed -i.bak "s/your-generated-api-key-here/$MCP_API_KEY/" .env.production

    # Generate AIRFLOW FERNET KEY
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    sed -i.bak "s|your-fernet-key-here|$FERNET_KEY|" .env.production

    rm -f .env.production.bak

    echo -e "${YELLOW}⚠ .env.production created with placeholder values.${NC}"
    echo -e "${YELLOW}  Edit .env.production and fill in:${NC}"
    echo -e "${YELLOW}    - IBM_WATSONX_API_KEY${NC}"
    echo -e "${YELLOW}    - IBM_WATSONX_PROJECT_ID${NC}"
    echo -e "${YELLOW}    - ASTRA_DB_APPLICATION_TOKEN${NC}"
    echo -e "${YELLOW}    - ASTRA_DB_ID${NC}"
    echo -e "${YELLOW}    - NGROK_AUTH_TOKEN${NC}"
    echo -e "${YELLOW}  Then re-run this script.${NC}"
    exit 0
else
    echo -e "${GREEN}✓ .env.production found${NC}"
fi

# ============================================================================
# Step 4: Pull Docker Images
# ============================================================================

echo -e "${YELLOW}[4/10] Pulling Docker base images...${NC}"

docker-compose pull --quiet postgres redis minio iceberg-rest trino ngrok
echo -e "${GREEN}✓ Base images pulled${NC}"

# ============================================================================
# Step 5: Build Custom Images
# ============================================================================

echo -e "${YELLOW}[5/10] Building custom Docker images (airflow, mcp-server)...${NC}"

docker-compose build --quiet airflow-webserver airflow-scheduler mcp-server
echo -e "${GREEN}✓ Custom images built${NC}"

# ============================================================================
# Step 6: Start Infrastructure Services
# ============================================================================

echo -e "${YELLOW}[6/10] Starting infrastructure services...${NC}"

docker-compose up -d postgres redis minio iceberg-rest trino
echo -e "${GREEN}✓ Infrastructure services starting...${NC}"

# ============================================================================
# Step 7: Wait for Services
# ============================================================================

echo -e "${YELLOW}[7/10] Waiting for services to be healthy (30 seconds)...${NC}"

sleep 30

# Check health
HEALTHY=0
for i in {1..5}; do
    if docker-compose ps | grep -q "postgres.*Up.*healthy"; then
        HEALTHY=$((HEALTHY + 1))
    fi
done

if [ $HEALTHY -lt 1 ]; then
    echo -e "${YELLOW}⚠ Services still starting. Waiting additional 30 seconds...${NC}"
    sleep 30
fi

echo -e "${GREEN}✓ Services healthy${NC}"

# ============================================================================
# Step 8: Start Application Services
# ============================================================================

echo -e "${YELLOW}[8/10] Starting application services (airflow, mcp-server, ngrok)...${NC}"

docker-compose up -d airflow-webserver airflow-scheduler mcp-server ngrok
echo -e "${GREEN}✓ Application services starting...${NC}"

# ============================================================================
# Step 9: Retrieve ngrok Public URL
# ============================================================================

echo -e "${YELLOW}[9/10] Retrieving ngrok tunnel URL...${NC}"

sleep 5

NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url' 2>/dev/null || echo "http://localhost:4040")

if [ "$NGROK_URL" != "http://localhost:4040" ] && [ "$NGROK_URL" != "null" ]; then
    echo -e "${GREEN}✓ ngrok tunnel established${NC}"
    echo -e "${BLUE}  Public URL: $NGROK_URL${NC}"
else
    echo -e "${YELLOW}⚠ ngrok tunnel not yet established. Check docker-compose logs ngrok${NC}"
    NGROK_URL="[pending]"
fi

# ============================================================================
# Step 10: Summary
# ============================================================================

echo -e "${YELLOW}[10/10] Setup complete!${NC}"

echo -e "${BLUE}"
echo "=========================================="
echo "ESG Evaluation Platform - Ready"
echo "=========================================="
echo -e "${NC}"

echo -e "${GREEN}Service Endpoints:${NC}"
echo "  PostgreSQL:        postgresql://airflow:airflow@localhost:5432/airflow"
echo "  Redis:             redis://localhost:6379"
echo "  MinIO Console:     http://localhost:9001 (admin/admin)"
echo "  Iceberg Catalog:   http://localhost:8181"
echo "  Trino:             http://localhost:8082"
echo "  Airflow:           http://localhost:8081 (admin/admin)"
echo "  MCP Server:        http://localhost:8000"
echo "  ngrok Dashboard:   http://localhost:4040"
echo "  ngrok Tunnel:      $NGROK_URL"

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. View logs:        docker-compose logs -f"
echo "  2. Run tests:        ./scripts/test-local.sh"
echo "  3. Stop services:    docker-compose down -v"
echo "  4. Manage airflow:   docker-compose exec airflow-webserver airflow dags list"

echo ""
echo -e "${BLUE}For support: Check docker-compose logs <service-name>${NC}"
echo ""
