.PHONY: setup cp coverage types ccn docs integ docker-build docker-run docker-stop docker-smoke doctor live ci-guard determinism differential security e2e-full live.ingest live.embed live.index live.score live.ingest-docker

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

# ============================================================================
# Live Multi-Source Ingestion Targets (SCA v13.8-MEA)
# ============================================================================

.PHONY: live.ingest live.embed live.index live.ingest-docker

live.ingest: live-preflight
	@echo "Starting live multi-source ingestion..."
	@SEED=42 PYTHONHASHSEED=0 python3 scripts/ingest_live_matrix.py \
		--config configs/companies_live.yaml \
		--output-dir artifacts/ingestion \
		--seed 42
	@echo "Ingestion complete: Check artifacts/ingestion/ for manifests and logs"

live.embed: live.ingest
	@echo "Building embeddings from ingested documents..."
	@SEED=42 PYTHONHASHSEED=0 LIVE_EMBEDDINGS=true python3 scripts/embed_ingested.py \
		--input-dir data/bronze \
		--output-dir data/silver \
		--model "deterministic" \
		--seed 42
	@echo "Embeddings complete: Check data/silver/ for processed documents"

live.index: live.embed
	@echo "Indexing embedded documents into vector store..."
	@SEED=42 PYTHONHASHSEED=0 python3 scripts/upsert_vector_store.py \
		--input-dir data/silver \
		--index-path artifacts/live_index \
		--backend "milvus" \
		--seed 42
	@echo "Indexing complete: Ready for ESG scoring"

live.score: live.index
	@echo "Scoring ingested documents with ESG rubric..."
	@SEED=42 PYTHONHASHSEED=0 python3 scripts/orchestrate.py \
		--companies artifacts/ingestion/ingestion_summary.json \
		--output artifacts/live_scoring \
		--seed 42
	@echo "Scoring complete: Check artifacts/live_scoring/ for results"

# ============================================================================
# Live Authentic Multi-Source Ingestion (SCA v13.8-MEA | Real HTTP)
# ============================================================================

.PHONY: live.fetch live.replay live.score live.parity live.contract live.all live.authentic-runbook

live.fetch:
	@echo "=== FETCH PASS (network ON) ==="
	@echo "Requirement: ALLOW_NETWORK=true"
	@[ "$${ALLOW_NETWORK}" = "true" ] || (echo "ERROR: ALLOW_NETWORK must be true" && exit 1)
	@echo "Importing real providers (SEC EDGAR, Company IR)..."
	@python3 -m pip -q install pyyaml requests >/dev/null 2>&1 || true
	@SEED=42 PYTHONHASHSEED=0 ALLOW_NETWORK=true python3 scripts/ingest_live_matrix.py --config configs/companies_live.yaml
	@echo "=== FETCH PASS COMPLETE ==="

live.replay:
	@echo "=== REPLAY PASS (network OFF, determinism 3×) ==="
	@echo "Requirement: ALLOW_NETWORK unset"
	@[ -z "$${ALLOW_NETWORK}" ] || (echo "ERROR: Unset ALLOW_NETWORK for replay" && exit 1)
	@python3 -m pip -q install pyyaml >/dev/null 2>&1 || true
	@SEED=42 PYTHONHASHSEED=0 python3 scripts/run_matrix.py --config configs/companies_live.yaml
	@echo "=== REPLAY PASS COMPLETE ==="

live.score:
	@echo "Scoring integrated into replay pass (run_matrix.py)"

live.parity:
	@echo "Parity validation stub emitted in artifacts/matrix/*/pipeline_validation/"

live.contract:
	@echo "Per-doc contracts: artifacts/matrix/<doc_id>/output_contract.json"
	@echo "Matrix contract: artifacts/matrix/matrix_contract.json"

live.all: live.fetch
	@unset ALLOW_NETWORK; $$(MAKE) live.replay
	@$$(MAKE) live.contract
	@echo ""
	@echo "=== PIPELINE COMPLETE ==="
	@echo "Review artifacts:"
	@echo "  - Data ingestion: artifacts/ingestion/ingestion_summary.json"
	@echo "  - Determinism proof: artifacts/matrix/*/baseline/determinism_report.json"
	@echo "  - Output contracts: artifacts/matrix/*/output_contract.json"
	@echo "  - Matrix contract: artifacts/matrix/matrix_contract.json"

live.authentic-runbook:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║  SCA v13.8-MEA | LIVE INGESTION AUTHENTIC RUNBOOK             ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "STEP 1: Verify configuration"
	@echo "  - Edit: configs/companies_live.yaml"
	@echo "  - Override URLs: Add real SEC 10-K or IR sustainability report PDF URLs"
	@echo "  - OR set CIK_* environment variables for SEC API lookups"
	@echo ""
	@echo "STEP 2: Fetch pass (network ON)"
	@echo "  $$ ALLOW_NETWORK=true make live.fetch"
	@echo "  Outputs: data/raw/org_id=*/year=*/[doc].pdf (cached with HTTP manifests)"
	@echo "           artifacts/ingestion/ingestion_summary.json"
	@echo ""
	@echo "STEP 3: Replay pass (network OFF, determinism 3×)"
	@echo "  $$ unset ALLOW_NETWORK; make live.replay"
	@echo "  Outputs: artifacts/matrix/*/baseline/run_{1,2,3}/output.json|hash.txt"
	@echo "           artifacts/matrix/*/baseline/determinism_report.json (PASS/FAIL)"
	@echo "           artifacts/matrix/*/output_contract.json"
	@echo ""
	@echo "STEP 4: Review evidence & parity gates"
	@echo "  - Check: artifacts/matrix/*/pipeline_validation/evidence_audit.json"
	@echo "  - Check: artifacts/matrix/*/pipeline_validation/demo_topk_vs_evidence.json"
	@echo "  - Check: artifacts/matrix/*/pipeline_validation/rd_sources.json"
	@echo ""
	@echo "GATES (SCA v13.8-MEA fail-closed):"
	@echo "  ✓ AUTHENTICITY: No mocks; real HTTP requests with manifest tracking"
	@echo "  ✓ DETERMINISM: 3-run identical hash proof"
	@echo "  ✓ TRACEABILITY: Full HTTP manifests (source_url, headers, sha256, timestamp)"
	@echo "  ✗ EVIDENCE: Stub (real extraction in next phase)"
	@echo "  ✗ PARITY: Stub (real constraint check in next phase)"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo ""

# ============================================================================
# Component 2: Semantic Retrieval Targets
# ============================================================================

.PHONY: semantic.fetch semantic.replay semantic.full

semantic.fetch:
	@echo "=== SEMANTIC FETCH: Building embeddings for all documents ==="
	@[ "$$ALLOW_NETWORK" = "true" ] || (echo "ERROR: Set ALLOW_NETWORK=true" && exit 2)
	@[ -n "$$WX_API_KEY" ] || (echo "ERROR: Set WX_API_KEY" && exit 2)
	@[ -n "$$WX_PROJECT" ] || (echo "ERROR: Set WX_PROJECT" && exit 2)
	@export SEED=42 PYTHONHASHSEED=0 && \
	python3 scripts/semantic_fetch_replay.py --phase fetch --doc-id msft_2023 || true

semantic.replay:
	@echo "=== SEMANTIC REPLAY: Querying with cached embeddings ==="
	@[ -z "$$ALLOW_NETWORK" ] || (echo "ERROR: Unset ALLOW_NETWORK for replay" && exit 2)
	@[ "$$WX_OFFLINE_REPLAY" = "true" ] || (echo "ERROR: Set WX_OFFLINE_REPLAY=true" && exit 2)
	@export SEED=42 PYTHONHASHSEED=0 && \
	python3 scripts/semantic_fetch_replay.py --phase replay --doc-id msft_2023

semantic.full:
	@echo "=== SEMANTIC FULL: FETCH -> REPLAY workflow ==="
	@export ALLOW_NETWORK=true SEED=42 PYTHONHASHSEED=0 && \
	$(MAKE) semantic.fetch && \
	unset ALLOW_NETWORK && \
	export WX_OFFLINE_REPLAY=true SEED=42 PYTHONHASHSEED=0 && \
	$(MAKE) semantic.replay



.PHONY: local.fetch
local.fetch:
	python scripts/ingest_local_matrix.py --config configs/companies_local.yaml

.PHONY: semantic.fetch.local
semantic.fetch.local:
	WX_OFFLINE_REPLAY=false ALLOW_NETWORK=true SEED=42 PYTHONHASHSEED=0 python scripts/semantic_fetch_replay.py --phase fetch --doc-id all || true

.PHONY: local.replay
local.replay:
	WX_OFFLINE_REPLAY=true SEED=42 PYTHONHASHSEED=0 python scripts/run_matrix.py --config configs/companies_local.yaml --semantic

.PHONY: report.local
report.local:
	python scripts/generate_nl_report.py --config configs/companies_local.yaml
