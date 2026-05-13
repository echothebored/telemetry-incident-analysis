# Derived Metrics and Transformations

All computed columns, aggregations, and thresholds created during analysis. Enables reviewers to verify calculations and understand how raw telemetry was transformed into analytical outputs.

## Computed Columns (added to raw dataframe)

| Column | Formula | Purpose |
|--------|---------|---------|
| `duration_ms` | `duration / 1000` | Convert microseconds to milliseconds for readability |
| `endpoint` | URL pattern classification (see below) | Group parameterized URLs into 5 patterns |
| `bin_10s` | `timestamp.dt.floor('10s')` | 10-second time bins for incident analysis |
| `bin_30s` | `timestamp.dt.floor('30s')` | 30-second time bins for trend analysis |
| `is_5xx` | `response_status_code >= 500` | Boolean flag for SLO-relevant failures (500, 503) |
| `is_success` | `response_status_code == 200` | Boolean flag for successful requests |
| `is_degraded` | `is_success AND duration > DEGRADED_THRESHOLD_US` | 200s slower than healthy p95 |

## Endpoint Classification

Raw `request_url` values are collapsed into 5 patterns:

| Pattern | Rule | Example URLs |
|---------|------|-------------|
| `/users` | 1 path segment | `/users` |
| `/users/{id}` | 2 path segments | `/users/abc123` |
| `/users/{id}/posts` | 3 path segments | `/users/abc123/posts` |
| `/posts` | 1 path segment | `/posts` |
| `/posts/{id}` | 2 path segments | `/posts/xyz789` |

## Key Thresholds

| Threshold | Value | Derivation | Used in |
|-----------|-------|-----------|---------|
| Healthy window start | 2025-08-12 18:56:00 UTC | Longest contiguous period: no 503s, no 429s, 5xx < 4%, > 100 req/bin | All baseline comparisons |
| Healthy window end | 2025-08-12 19:01:00 UTC | Same | Same |
| Baseline 5xx rate | 3.11% | Healthy window mean (Wilson 95% CI: 2.96–3.28%) | SLO calibration, incident excess |
| Degraded success threshold | 175,203 μs (175.2 ms) | Healthy window p95 of 200-only latency | Quality SLI, degraded 200 counts |
| Incident detection: 5xx | 6.2% | 2x baseline 5xx rate | Incident identification (2.1) |
| Incident detection: p95 | 350 ms | 2x baseline p95 latency | Incident identification (2.1) |
| Acute alert threshold | 9.3% | 3x baseline 5xx rate | Channel 2 alert rule |

## Baseline Metrics (healthy window, 200-only latency)

| Metric | Value | Raw (μs where applicable) |
|--------|-------|--------------------------|
| Request count | 45,070 | |
| Request rate | 150.2 req/s | |
| 200 count | 43,625 | |
| 200 rate | 96.79% | |
| 5xx count | 1,403 | |
| 5xx rate | 3.11% | |
| p50 latency | 38.2 ms | 38,220 μs |
| p75 latency | 77.0 ms | 77,011 μs |
| p90 latency | 131.2 ms | 131,225 μs |
| p95 latency | 175.2 ms | 175,203 μs |
| p99 latency | 293.1 ms | 293,079 μs |
| Max latency | 864.7 ms | 864,740 μs |

## Per-Server Baseline (200-only, healthy window)

| Server | Requests | p50 (ms) | p95 (ms) | p99 (ms) | Rate (req/s) |
|--------|----------|----------|----------|----------|-------------|
| service-1 | 21,748 | 38.8 | 174.9 | 295.9 | 74.9 |
| service-2 | 10,931 | 37.8 | 177.3 | 292.7 | 37.6 |
| service-3 | 10,946 | 37.6 | 172.5 | 277.7 | 37.7 |

## Incident 1 Metrics (19:01:00–19:02:00)

| Metric | Value |
|--------|-------|
| Total requests | 8,913 |
| 5xx count | 767 (503: 426, 500: 341) |
| 5xx rate | 8.6% |
| Availability | 91.4% |
| Degraded 200s | 615 (7.6% of 200s) |
| Total impacted | 1,382 |
| Expected baseline 5xx | 277 |
| Excess failures | 490 |
| Blended burn rate (at 96.5% target) | 2.5x |
| Peak burn rate (10s, at 96.5% target) | 8.3x |
| Recovery-phase 500s | 281 of 341 (19:01:20–19:02:00) |

## Incident 2 Metrics (19:04:00–19:04:30)

| Metric | Value |
|--------|-------|
| Total requests | 9,339 |
| Traffic multiplier | 2.07x baseline |
| Burst client requests | 5,111 (54.7% of window) |
| Legitimate user requests | 4,228 |
| 429s issued | 283 (all to burst client) |
| Burst client 5xx rate | 2.82% |
| Legitimate user 5xx rate | 2.93% (below baseline) |
| Legitimate user p50 latency | 37.4 ms |
| Legitimate user p95 latency | 177.3 ms |
| Legitimate degraded 200 rate | 5.1% (at baseline) |

## Stationarity Test (baseline 5xx)

| Metric | Value |
|--------|-------|
| Test | Chi-square homogeneity across 30s bins |
| Chi-square statistic | 9.58 |
| Degrees of freedom | 9 |
| p-value | 0.385 |
| Variance/mean ratio | 1.02 |
| Conclusion | Poisson noise — stable underlying rate |
