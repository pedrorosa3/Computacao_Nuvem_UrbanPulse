from prometheus_client import Counter, Histogram

GRPC_REQUESTS_TOTAL = Counter(
    "grpc_client_requests_total",
    "Total de chamadas gRPC feitas pelo Location Service",
    ["target_service", "method", "status"],
)

GRPC_REQUEST_DURATION = Histogram(
    "grpc_client_request_duration_seconds",
    "Latência das chamadas gRPC (segundos)",
    ["target_service", "method"],
)