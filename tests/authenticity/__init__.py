"""
Authenticity Critical Path Tests (AR-001)

Tests for the 5 gates:
1. ingestion_authenticity: Ledger, manifest, SHA256 traceability
2. parity: Evidence ⊆ fused top-k invariant
3. rubric_compliance: ≥2 quotes per theme enforcement
4. determinism: 3× identical outputs
5. docker_only: Runtime read-only scoring, no network egress (not tested here)

SCA v13.8
"""
