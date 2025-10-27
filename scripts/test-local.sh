#!/bin/bash
#
# ESG Evaluation Platform - Local Service Tests
# Phase 1: Core Infrastructure Validation
#
# Usage: ./scripts/test-local.sh
#
# Tests all 9 services and container networking
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test function
test_service() {
    local test_name=$1
    local test_cmd=$2

    echo -n "Testing $test_name... "

    if eval "$test_cmd" &> /dev/null; then
        echo -e "${GREEN}✓${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC}"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${BLUE}"
echo "=========================================="
echo "ESG Evaluation Platform - Service Tests"
echo "=========================================="
echo -e "${NC}"

# ============================================================================
# PostgreSQL
# ============================================================================
test_service "PostgreSQL" \
    "docker exec postgres pg_isready -U airflow -h localhost"

# ============================================================================
# Redis
# ============================================================================
test_service "Redis" \
    "docker exec redis redis-cli PING | grep -q PONG"

# ============================================================================
# MinIO
# ============================================================================
test_service "MinIO Health" \
    "curl -s http://localhost:9000/minio/health/live | grep -q ''"

# ============================================================================
# Iceberg REST
# ============================================================================
test_service "Iceberg Catalog" \
    "curl -s http://localhost:8181/v1/config | grep -q 'defaults\|overrides'"

# ============================================================================
# Trino
# ============================================================================
test_service "Trino Query Engine" \
    "curl -s http://localhost:8082/v1/info | grep -q 'nodeVersion'"

# ============================================================================
# Airflow Webserver
# ============================================================================
test_service "Airflow Webserver" \
    "curl -s http://localhost:8081/health | grep -q 'healthy'"

# ============================================================================
# Airflow Scheduler
# ============================================================================
test_service "Airflow Scheduler Running" \
    "docker-compose ps airflow-scheduler | grep -q 'Up'"

# ============================================================================
# MCP Server
# ============================================================================
test_service "MCP Server Health" \
    "curl -s http://localhost:8000/health | grep -q 'ok'"

# ============================================================================
# ngrok Tunnel
# ============================================================================
test_service "ngrok Tunnel API" \
    "curl -s http://localhost:4040/api/tunnels | grep -q 'tunnels'"

# ============================================================================
# Container Networking: mcp-server → redis
# ============================================================================
test_service "Network: mcp-server → redis" \
    "docker exec mcp-server redis-cli -h redis PING | grep -q PONG"

# ============================================================================
# Container Networking: mcp-server → postgres
# ============================================================================
test_service "Network: mcp-server → postgres (DNS)" \
    "docker exec mcp-server getent hosts postgres | grep -q 'postgres'"

# ============================================================================
# Environment Variables
# ============================================================================
test_service "Environment: .env.production" \
    "[ -f .env.production ]"

# ============================================================================
# Docker Volumes
# ============================================================================
test_service "Docker Volumes Created" \
    "docker volume ls | grep -q 'postgres_data'"

# ============================================================================
# ngrok Public URL
# ============================================================================
echo -n "Testing ngrok Public URL... "
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url' 2>/dev/null)

if [ ! -z "$NGROK_URL" ] && [ "$NGROK_URL" != "null" ]; then
    echo -e "${GREEN}✓${NC} ($NGROK_URL)"
    PASSED=$((PASSED + 1))

    # Test external access to public URL (optional)
    echo -n "  Testing external access... "
    if curl -s -m 5 "$NGROK_URL/health" 2>/dev/null | grep -q 'ok'; then
        echo -e "${GREEN}✓${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${YELLOW}⚠${NC} (tunnel not yet accessible externally)"
    fi
else
    echo -e "${YELLOW}⚠${NC} (tunnel not yet established)"
fi

# ============================================================================
# Summary
# ============================================================================

echo -e "${BLUE}"
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${NC}"

echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All services healthy!${NC}"
    exit 0
else
    echo -e "${RED}Some services failed. Check docker-compose logs.${NC}"
    exit 1
fi
