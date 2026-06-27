"""Custom Prometheus metrics for search observability."""

from prometheus_client import Counter, Histogram

SEARCH_REQUESTS = Counter(
    "kb_search_requests_total",
    "Total number of /search requests handled.",
    labelnames=("cached",),
)

SEARCH_LATENCY = Histogram(
    "kb_search_latency_seconds",
    "Latency of /search request handling in seconds.",
)
