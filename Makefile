.PHONY: setup cp coverage types ccn docs integ docker-build docker-run docker-stop docker-smoke doctor live ci-guard determinism differential security e2e-full

setup:
	pip install -r requirements.txt

cp:
	pytest -m cp -q

coverage:
	coverage run -m pytest
	coverage report --fail-under=95
	coverage xml
	coverage html

types:
	mypy --strict apps/ agents/ libs/

ccn:
	lizard -C 10 apps/ agents/ libs/

docs:
	interrogate -v -f 95 apps/ agents/ libs/

integ:
	LIVE_EMBEDDINGS=true ALLOW_NETWORK=true pytest -m "integration and requires_api" -q

docker-build: doctor live-preflight
	docker build -t esg-scoring:ci .

docker-run:
	docker run -d --rm --name esg-scoring-local -p 8000:8000 esg-scoring:ci

docker-stop:
	- docker stop esg-scoring-local

docker-smoke: doctor live-preflight
	bash scripts/docker_smoke.sh

doctor:
	@bash scripts/wsl_docker_doctor.sh
	@if command -v pwsh >/dev/null 2>&1; then \
		pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/wsl_docker_doctor.ps1; \
	elif command -v powershell.exe >/dev/null 2>&1; then \
		powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$$(wslpath -w scripts/wsl_docker_doctor.ps1 2>/dev/null || printf 'scripts\\wsl_docker_doctor.ps1')"; \
	else \
		echo "PowerShell not found (install pwsh or enable powershell.exe)" >&2; exit 1; \
	fi

live: doctor live-preflight
	@echo "LIVE preflight OK"
	@SEC_DEFAULT="IBM-ESG/ScoringApp/0.1 (Contact: <your-email>; Purpose: EDGAR 10-K fetch for ESG demo)"; \
	if [ -z "$$WX_API_KEY" ] || [ -z "$$WX_PROJECT" ] || [ -z "$$WX_MODEL_ID" ]; then \
		echo "Missing WX_API_KEY/WX_PROJECT/WX_MODEL_ID environment variables." >&2; exit 1; \
	fi; \
	SEC_USER_AGENT=$${SEC_USER_AGENT:-$$SEC_DEFAULT} ALLOW_NETWORK=$${ALLOW_NETWORK:-true} LIVE_EMBEDDINGS=$${LIVE_EMBEDDINGS:-true} docker compose -f docker-compose.live.yml up -d --build

.PHONY: live-preflight
live-preflight:
	@python3 scripts/live_preflight.py

# ============================================================================
# E2E Orchestration Targets (SCA v13.8)
# ============================================================================

ci-guard:
	@echo "Running CI guard checks..."
	bash scripts/ci_guard.sh

determinism:
	@echo "Running determinism validation..."
	bash scripts/determinism_check.sh

differential:
	@echo "Running differential tests..."
	bash scripts/differential_test.sh

security:
	@echo "Running security scanning..."
	bash scripts/security_scan.sh

e2e-full: docker-build ci-guard determinism differential security
	@echo ""
	@echo "=== E2E Orchestration Complete ==="
	@echo "All gates passed. Generating output contract..."
	@python3 scripts/aggregate_output_contract.py > artifacts/output_contract.json
	@echo "Output contract: artifacts/output_contract.json"
	@echo ""
