# Response Latency Benchmark

Synopsis Section 7 target: <300ms (end-to-end, prompt submission to decision).

- Mode: in-process (TestClient)
- Requests measured: 100 (after 5 warmup requests, excluded)
- Mean: 27.6ms
- p50: 30.5ms
- p95: 37.7ms
- p99: 41.0ms
- Max: 41.7ms

**p95 meets the <300ms target.**

Note: in-process mode (the default) measures the detection+scoring pipeline itself, isolated from network/hosting variables (DNS, TLS, free-tier CPU throttling, cold starts). Run with --url against a live deployment for a real end-user-facing number, which will be higher and more variable, especially on Render's free tier.