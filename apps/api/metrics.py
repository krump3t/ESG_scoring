"""
Prometheus Metrics for ESG Scoring API

Metrics exported:
- esg_api_requests_total: Counter of API requests
- esg_semantic_knn_latency_seconds: Histogram of KNN latencies
- esg_fusion_latency_seconds: Histogram of fusion latencies
- esg_score_latency_seconds: Histogram of scoring latencies
- esg_vector_index_size: Gauge of vector index size
- esg_semantic_enabled_total: Counter of semantic-enabled requests
- esg_build_info: Info metric with model/rubric versions
- esg_demo_ingest_total: Counter of demo ingestions by source
- esg_demo_index_size: Gauge of demo index size by backend
- esg_demo_score_latency_seconds: Histogram of demo score latencies
- esg_parity_break_total: Counter of parity violations

SCA v13.8 Compliance:
- Type safety: 100% annotated
- No network: Metrics exported via /metrics endpoint only
- Determinism: Counters/histograms are inherently non-deterministic (time-based)
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

# Counter: Total API requests
esg_api_requests_total = Counter(
    "esg_api_requests_total",
    "Total number of ESG API requests",
    labelnames=["route", "method", "status"]
)

# Histogram: Semantic KNN latency
esg_semantic_knn_latency_seconds = Histogram(
    "esg_semantic_knn_latency_seconds",
    "Latency of semantic KNN retrieval in seconds",
    labelnames=["backend"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)

# Histogram: Fusion latency
esg_fusion_latency_seconds = Histogram(
    "esg_fusion_latency_seconds",
    "Latency of lexical+semantic fusion in seconds",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0)
)

# Histogram: Score latency
esg_score_latency_seconds = Histogram(
    "esg_score_latency_seconds",
    "Latency of rubric scoring in seconds",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

# Gauge: Vector index size
esg_vector_index_size = Gauge(
    "esg_vector_index_size",
    "Number of vectors in index",
    labelnames=["backend"]
)

# Counter: Semantic enabled requests
esg_semantic_enabled_total = Counter(
    "esg_semantic_enabled_total",
    "Total number of requests with semantic retrieval enabled"
)

# Info: Build information
esg_build_info = Info(
    "esg_build_info",
    "ESG API build information"
)

# Set build info (will be updated at startup)
esg_build_info.info({
    "model_version": "v1.0",
    "rubric_version": "v3.0"
})

# Demo metrics
esg_demo_ingest_total = Counter(
    "esg_demo_ingest_total",
    "Total number of demo company ingestions",
    labelnames=["source"]
)

esg_demo_index_size = Gauge(
    "esg_demo_index_size",
    "Number of documents in demo index",
    labelnames=["backend"]
)

esg_demo_score_latency_seconds = Histogram(
    "esg_demo_score_latency_seconds",
    "Latency of demo scoring requests in seconds",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

esg_parity_break_total = Counter(
    "esg_parity_break_total",
    "Total number of evidence parity violations (evidence not in fused top-k)"
)

# Router for /metrics endpoint
router = APIRouter()

@router.get("/metrics")
def metrics() -> Response:
    """
    Export Prometheus metrics.

    Returns:
        Response with Prometheus text format
    """
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
