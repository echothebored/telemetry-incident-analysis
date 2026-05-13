# Data Profile Triage

<!--
Critical evaluation of initial data exploration findings.
Each finding is flagged as signal, noise, or surprising — with reasoning.
Includes Phase 0 temporal bootstrap, baseline metrics, multi-resolution validation.

Sources:
  - ydata-profiling HTML report (supporting/data_profile_report.html)
  - triage_profiler.py, triage_urls.py, triage_baseline.py
-->

## Dataset Overview

- **95,015 rows**, 14 columns
- **Time range:** 2025-08-12 18:55:59 to 19:05:59 UTC (exactly 600 seconds)
- **Zero missing values** across all columns
- **Zero duplicate rows**
- **request_id and response_id are globally unique** — 1:1 mapping, no fan-out visible
- **1,991 unique clients**, 3 servers, 5 regions, 6 agent types, 5 status codes, 3 HTTP methods
- **5 endpoint patterns**: /users, /posts, /users/{id}, /posts/{id}, /users/{id}/posts — roughly equal volume (~19K each)

---

## Profiler Findings Triage

### Signal — Analytically significant, feeds into analysis

| # | Finding | Evidence | Implication |
|---|---------|----------|-------------|
| S1 | **Two distinct incidents with different failure modes** | 30s bins: 19:01:00 spike to 11.8% 5xx (503+500); 19:04:00 traffic doubles with 429s | Two separate incidents requiring independent root cause analysis. Not a single degradation event. |
| S2 | **503s are service-1 exclusive** | All 426 503s from service-1. service-2 and service-3 have zero 503s across entire dataset. | service-1 experienced a failure mode the others did not. Suggests infrastructure-level event (health check failure, deployment, connection refused) not application-level bug. If it were code, all instances would fail identically. |
| S3 | **Incident 1 is a service-1 failure, not system-wide** | 19:01:00–19:02:00: 587 of 767 5xx from service-1 (76.5%). service-2 and service-3 contributed ~90 each (background rate). | The 11.8% aggregate 5xx rate is misleading — service-1's actual rate during this window is far higher. service-2/3 appear elevated only because 30s binning averages them together. |
| S4 | **503 burst is sub-10-second event** | 10s resolution: 414 of 426 503s concentrated in the 19:01:10 bin. 12 503s in 19:01:00, zero in all other bins. | service-1 went into a brief but total failure state. The abrupt onset and cessation is consistent with health check failure (LB binary decision) or container restart, not gradual overload. |
| S5 | **500 latency is massively elevated vs other status codes** | 500s: p50=45.9ms, p95=2,091ms (~2.1s), p99=2,876ms (~2.9s). 200s: p50=38.9ms, p95=180ms, p99=302ms. 503s: p50=42.7ms, p95=193ms. | 500s are not fast-fail — something is timing out. Requests that eventually 500 spend 10-15x longer than healthy requests at the tail. This is consistent with queuing/resource exhaustion (as utilization→1, wait→∞). 503s have latency similar to 200s — fast rejection, not queuing. |
| S6 | **Single client caused incident 2** | yNGr0ru8jkXx: 5,251 total requests. 5,111 of those in a single 30s bin (19:04:00). All 283 429s belong to this client. Chrome/mobile/south. | Traffic spike is not organic — one client sent ~170 req/s (vs system baseline ~150 req/s for ALL clients). Rate limiter caught it (429s), but the blast radius needs assessment. |
| S7 | **Latency aftershock following incident 1** | Degraded 200s (>healthy p95): 10.35% during 19:01:00 bin vs ~5% baseline. p95 elevated at 248K (baseline 175K). service-2 and service-3 show elevated degraded rates (8.8% and 7.5%) even though service-1 was the failure source. | service-1's failure caused collateral damage on service-2/3 — likely from traffic redistribution when LB pulled service-1 out of rotation. More traffic to fewer servers = higher latency. |
| S8 | **South region has systematically higher latency** | 200-only: south p50=44.3ms vs ~37ms for other regions. p95=203ms vs ~172ms. ~19% higher across all percentiles. | Geographic distance or routing effect. Consistent across all time periods, not incident-related. Relevant for capacity planning (3.4) and differential impact assessment (2.3). |
| S9 | **Client concentration is steep** | Top client: 5.5% of traffic. Top 100 clients (5%): 48.5% of traffic. p75 of per-client requests is 16, but max is 5,251. | Long-tail distribution. A small number of heavy clients drive disproportionate load. The dominant client's burst behavior (S6) is the extreme case of this pattern. Relevant for rate limiting recommendations (3.3). |
| S10 | **Persistent ~3% baseline 5xx rate** | Healthy window (18:56–19:01): 5xx rate ranges 2.70%–3.62% per 30s bin, avg 3.11%. All 500s, zero 503s. Distributed uniformly across servers and endpoints. | This is not a zero-error baseline. The system has a persistent ~3% 500 error rate even when "healthy." This is either normal application behavior (transient failures, timeouts on slow requests) or indicates a chronic issue. SLO targets must account for this — setting availability target at 99.9% would be immediately violated. |

### Noise — Expected behavior, no analytical value

| # | Finding | Evidence | Why it's noise |
|---|---------|----------|----------------|
| N1 | **GET dominance at ~90%** | GET 85,489 (90.0%), POST 8,566 (9.0%), PUT 960 (1.0%). Consistent across servers (89.7–90.2%) and time bins (88.7–90.8%). | Read-heavy API, typical for user/post retrieval service. No GET ratio shift during incidents — weakens the retry-storm-via-GET hypothesis we had in methodology. |
| N2 | **No server-region affinity** | Each region sends ~41% to service-1, ~30% to service-2, ~29% to service-3. Ratios are uniform (±1.7%) across all 5 regions. | Traffic is distributed by weighted round-robin (or similar), not geographic routing. LB treats all regions identically. Simplifies incident impact analysis — no region is preferentially exposed to a specific server. |
| N3 | **Error rates uniform across agents** | 5xx rates: Chrome 3.22%, Edge 3.63%, Firefox 3.64%, Opera 3.60%, Safari 3.70%, app 3.60%. Range is 0.48pp. | No agent type experiences systematically worse errors. Failures are server-side, not client-triggered. |
| N4 | **Error rates uniform across endpoint groups** | 5xx rates: /posts 3.49%, /posts/{id} 3.66%, /users 3.50%, /users/{id} 3.49%, /users/{id}/posts 3.62%. Range is 0.17pp. | No endpoint is inherently more failure-prone. Errors are infrastructure-level, not route-specific. |
| N5 | **No URL-level error clustering** | Only 2 URLs (collection endpoints) have ≥10 requests. All parameterized URLs have 3–9 requests each. 500s on parameterized URLs are singletons (max 2 per URL). | The long tail of parameterized endpoints makes per-URL error rate analysis impossible — sample sizes too small. But the uniform distribution across endpoint groups (N4) confirms no route-specific failure. |
| N6 | **404s are scattered, normal behavior** | 81 total across 52 unique URLs. Collection endpoints get the most (17 and 14 on /posts and /users). Rest are singletons. 91% are GETs. | Clients requesting resources that don't exist — normal application behavior. Not correlated with incidents. Correctly excluded from SLO error budget per methodology. |
| N7 | **Clean data quality** | Zero nulls, zero duplicates, zero negative values, no zeros in numeric fields. | No data quality issues to work around. |

### Surprising — Needs investigation or impacts methodology

| # | Finding | Evidence | Why it matters |
|---|---------|----------|----------------|
| X1 | **Duration minimum is exactly 1,000μs (1ms) across all records** | Global min: 1,000μs. p1: 1,000μs. No value below 1,000μs. | Suspicious floor. Either: (a) instrumentation rounds sub-1ms responses to 1ms, (b) minimum processing time genuinely is 1ms, (c) synthetic data artifact. If (a), it affects tail analysis only at the very low end — minimal impact. If (c), it applies to all numeric fields. Acknowledged as limitation, not blocking. |
| X2 | **response_size and request_size have minimum of exactly 100 (bytes)** | Both fields: min=100, no values below 100. | Same pattern as X1. Reinforces the possibility of floors in the data generation. Does not affect our analysis since we care about distribution shape and relative differences, not absolute minimums. |
| X3 | **request_size bimodal distribution** | p50=321, p75=433, p90=1,131, p95=15,314. Sharp jump between p75 and p95. | Two populations: small requests (GETs with minimal payload) and large requests (POST/PUT bodies). Will verify by correlating with request_type. Expected but worth confirming — not an anomaly. |
| X4 | **429s only from Chrome agent** | All 283 429s attributed to Chrome. But all 283 are from client yNGr0ru8jkXx (who uses Chrome). Zero 429s from any other client. | The Chrome association is spurious — it's one client, not an agent-type behavior. The rate limiter is per-client, not per-agent. This would be a misleading finding if reported without the client-level decomposition. |
| X5 | **Incident 1 tail: 500 rate stays elevated through 19:02:00** | 10s resolution: 19:01:30 (4.87%), 19:01:40 (5.64%), 19:01:50 (5.43%) vs 3.1% baseline. Returns to baseline at 19:02:00 (3.15%). | The 503 burst (S4) was sub-10s, but 500s stayed elevated for ~40s after. Two possibilities: (a) request queue draining — requests that were waiting during the 503 window eventually timeout as 500s, (b) service-1 recovery was gradual, not instant. Need to check per-server 500 rate at fine resolution to distinguish. |
| X6 | **service-2/3 degraded during incident 1 despite not failing** | Degraded 200 rate during 19:01 (threshold: 175.2ms): service-1 5.9%, service-2 8.8%, service-3 7.5% (baseline ~5%). | Counter-intuitive: the non-failing servers had MORE latency degradation than service-1. Explanation: when service-1 was pulled from rotation, its traffic was redistributed to service-2/3, increasing their load. service-1's surviving 200s were from the tail end of the incident (post-recovery), so their degraded rate is lower. This is evidence of LB-mediated cascading impact. |

---

## Temporal Bootstrap (Phase 0)

### Healthy vs Incident Window Partition

| Window | Start | End | Duration | 5xx Rate | Classification | Key Evidence |
|--------|-------|-----|----------|----------|----------------|--------------|
| Ramp-in | 18:55:59 | 18:56:00 | ~1s | 3.57% | Exclude | Only 56 requests — partial bin, not representative |
| **Healthy** | **18:56:00** | **19:01:00** | **300s** | **3.11% avg** | **Baseline** | Longest contiguous period: no 503s, no 429s, 5xx rate 2.70–3.62%, stable request rate ~150 req/s. 10 bins, 45,070 requests. |
| **Incident 1** | **19:01:00** | **19:02:00** | **60s** | **11.80%** | **Service-1 failure** | 426 503s (all service-1) + elevated 500s. Onset at 19:01:10, peak 5xx 29% at 10s resolution. 503 burst <10s, 500 tail ~40s. |
| Recovery | 19:02:00 | 19:04:00 | 120s | 3.04% avg | Healthy (post-incident) | Returns to baseline. 4 bins, no 503s, no 429s. |
| **Incident 2** | **19:04:00** | **19:04:30** | **30s** | **2.87% 5xx + 3.03% 429** | **Client burst** | Single client sends 5,111 requests in one 30s bin. 283 rate-limited (429). Traffic doubles. 5xx rate doesn't spike — rate limiter contained the blast radius. |
| Post-incident | 19:04:30 | 19:05:59 | 90s | 2.72% avg | Healthy (post-incident) | Returns to baseline. Lowest 5xx rates in the dataset (2.43%, 2.73%). |

**Partition decision:** Baseline window is 18:56:00–19:01:00 (300s). This is the longest contiguous healthy period and provides the most stable metrics. The post-incident windows (19:02–19:04, 19:04:30–19:06) are also healthy but shorter and potentially influenced by recovery dynamics. Using the pre-incident window avoids contamination.

**Caveat:** Even the healthy window has a persistent ~3% 500 rate. This baseline may itself be degraded compared to true steady-state. All baseline-derived thresholds carry this uncertainty.

### Baseline Metrics (from healthy window, 18:56:00–19:01:00)

**Duration unit:** Microseconds (μs). Stated in the case study spec: "`duration`: Request processing time in microseconds." Independently confirmed by observation window constraint — the dataset spans 600 seconds, but max duration is 7,778,093. In milliseconds that would be 7,778 seconds (2.16 hours), which cannot exist inside a 10-minute window. In microseconds it's 7.8 seconds — plausible. The spec and the data agree.

| Metric | Value | Human-readable | Notes |
|--------|-------|---------------|-------|
| Total requests | 45,070 | | 300s window |
| Request rate | 150.2 req/s | | Stable across bins (147–154 req/s per bin) |
| 200 rate | 96.79% | | 43,625 successful requests |
| 5xx rate | 3.11% | | 1,403 errors (all 500, zero 503) |
| 5xx range | 2.70–3.62% | | Per-30s-bin range during healthy window |
| 429 rate | 0% | | No rate limiting in healthy window |
| 404 rate | 0.06% | | 29 total, normal application behavior |
| **p50 latency (200s)** | **38,220μs** | **38.2ms** | |
| **p75 latency (200s)** | **77,011μs** | **77.0ms** | |
| p90 latency (200s) | 131,225μs | 131.2ms | |
| **p95 latency (200s)** | **175,203μs** | **175.2ms** | **Degraded success threshold** |
| **p99 latency (200s)** | **293,079μs** | **293.1ms** | |
| Max latency (200s) | 864,740μs | 864.7ms | |

**Per-server baselines (200s only):**

| Server | n | p50 | p95 | p99 |
|--------|---|-----|-----|-----|
| service-1 | 21,748 | 38,761μs (38.8ms) | 174,899μs (174.9ms) | 295,906μs (295.9ms) |
| service-2 | 10,931 | 37,779μs (37.8ms) | 177,347μs (177.3ms) | 292,747μs (292.7ms) |
| service-3 | 10,946 | 37,627μs (37.6ms) | 172,454μs (172.5ms) | 277,738μs (277.7ms) |

Servers perform similarly at baseline. service-1 handles ~2x traffic (consistent with weighted routing) but latency profiles are within noise.

### Degraded Success Threshold

**Threshold:** 175,203μs / 175.2ms (healthy-window p95 of 200-only latency)

200s with duration above this threshold are "functionally degraded" — the request succeeded but user experience was poor.

- Healthy window degraded rate: ~5% (by definition — this is the p95 threshold)
- Incident 1 degraded rate: **10.35%** (double baseline)
- Incident 2 degraded rate: **6.26%** (elevated but contained)
- Post-incident: returns to ~5%

### Multi-Resolution Validation

| Resolution | Bins (incident window) | Findings | Verdict |
|-----------|----------------------|----------|---------|
| 1-second | 90 | 118–181 requests per bin. Incident 1 onset visible at 19:01:09 (10.27%), peak at 19:01:15 (35.33%). Noisy: 0% to 35% swings in adjacent bins. Aftershock at 19:01:56 (10.85%). | Too noisy for trend analysis. Useful only for precise onset timing. |
| 5-second | 18 | 656–798 requests per bin. Incident 1: two bins at 30% and 28% (19:01:10 and 19:01:15), clear separation from noise. Tail visible at 19:01:30–19:01:55 (4.4–6.3%). | Good incident resolution, manageable noise. |
| **10-second** | **9** | **1,380–1,535 requests per bin. Incident 1: one clear peak at 29% (19:01:10), one tail bin at 3.26% (19:01:20). Subsequent tail at 4.87–5.64% (19:01:30–19:01:50).** | **Best balance: incident structure visible, noise suppressed. Enough temporal detail without false granularity.** |
| 30-second | 3 | 4,388–4,529 requests per bin. Incident 1: single spike at 11.8%, tail at 5.31%. | Too coarse — the 11.8% hides the true 29% peak. Loses incident onset/recovery shape. |

**Resolution decision:** 10-second bins for incident analysis, 30-second bins for trend and overview. 5-second used selectively for precise onset timing. 1-second only for confirming exact timestamps.

---

## Incident Characterization (Preliminary)

### Incident 1 — Service-1 Failure (19:01:00–19:02:00)

| Attribute | Value |
|-----------|-------|
| **Onset** | 19:01:10 (10s resolution), 19:01:09 (1s resolution) |
| **Peak** | 29.0% 5xx at 10s resolution (19:01:10 bin) |
| **Duration** | ~10s acute phase (503s), ~50s total including 500 tail |
| **503 count** | 426 (414 in the 19:01:10 bin alone) |
| **500 count (incident)** | 341 (elevated above baseline, includes queued request timeouts) |
| **Scope** | service-1 only (76.5% of all 5xx in the window) |
| **Collateral** | service-2/3 latency degradation (8.8% and 7.5% degraded 200s vs 5% baseline) |
| **Recovery** | 503s stop abruptly after 19:01:20. 500s return to baseline by 19:02:00. |
| **Onset character** | Sudden — consistent with container restart, deployment, or health check failure. NOT consistent with gradual overload (queuing theory: overload onset is gradual). |
| **Recovery character** | 503s: abrupt cessation. 500s: gradual decay over ~40s. Consistent with: server comes back online (503s stop), queued requests drain and timeout (500 tail). |

### Incident 2 — Client Burst / Rate Limiting Event (19:04:00–19:04:30)

| Attribute | Value |
|-----------|-------|
| **Onset** | 19:04:00 (10s resolution shows 6,339 requests in 19:04:00 bin vs ~1,500 baseline) |
| **Peak traffic** | ~9,339 requests in 30s bin (2.07x baseline volume) |
| **Duration** | ~20s (bulk of burst in 19:04:00–19:04:20 at 10s resolution) |
| **429 count** | 283 (all from one client: yNGr0ru8jkXx) |
| **5xx rate** | 2.87% — NOT elevated above baseline |
| **Scope** | Single client, contained by rate limiter |
| **Client profile** | yNGr0ru8jkXx, Chrome, mobile, south region. 5,111 requests in one 30s bin. Normally sends 1–3 req/bin. |
| **Rate limiter behavior** | Triggered on client yNGr0ru8jkXx only. 429s appear in 19:04:10 and 19:04:20 bins. No other client received 429s in the entire dataset. |
| **System impact** | Latency slightly elevated (p50=42.1ms vs 38.2ms baseline, p95=199.3ms vs 175.2ms). Degraded 200 rate at 6.26% vs 5% baseline. Rate limiter prevented cascading failure. |

---

## Extracted for Investigation (feeds into analysis.ipynb)

### Phase 0 outputs → all subsequent analysis
1. Healthy window definition: 18:56:00–19:01:00
2. Baseline metrics table (above)
3. Degraded success threshold: 175,203μs
4. Resolution choice: 10s for incidents, 30s for trends

### Part 1.1 (System Characteristics)
5. 3 servers, weighted round-robin routing (~41/30/29 split)
6. 5 endpoint patterns, ~equal volume
7. 1:1 request-response mapping (no fan-out)

### Part 1.2 (Traffic Patterns)
8. No server-region affinity — LB is geography-agnostic
9. Client concentration: top 100 = 48.5% of traffic
10. Dominant client (yNGr0ru8jkXx): 5.5% of all traffic, burst behavior
11. GET ratio stable at ~90% — no shift during incidents

### Part 1.3 (Performance Analysis)
12. South region ~19% higher latency
13. Per-server latency similar at baseline
14. 500 latency 10-15x healthy (timeout behavior)
15. 503 latency normal (fast rejection)
16. Degraded success rate doubles during incident 1

### Part 1.4 (Error Analysis)
17. Persistent ~3.1% baseline 500 rate — stable (Poisson noise, not variable), CI: 2.96–3.28% (M10)
18. 503s exclusive to service-1 and to incident 1
19. 429s exclusive to one client in one 30s window
20. No endpoint-specific or agent-specific error clustering
21. GET ratio shift hypothesis retired — no evidence of retry storms via request type (M9)

### Part 2 (Incidents)
22. Two distinct incidents with different mechanisms
23. Incident 1: service-1 failure, sudden onset, 503+500, collateral LATENCY (not errors) on service-2/3
24. Incident 1 tail: service-1 recovery dynamics — 500s at 8-10% for ~40s post-503 (M8)
25. Incident 2: client burst, rate limiter fully contained — legitimate users unaffected (M11)
26. Fine-resolution onset timing for both incidents

### Part 3 (Recommendations)
27. Rate limiter worked for single-client burst — what about distributed bursts?
28. service-1 failure caused cascading latency (not errors) — LB redistribution needs damping
29. Persistent 3.1% error rate is the real SLO calibration challenge (stable, not trending)
30. No server-region affinity means geographic recommendations are limited to latency optimization
31. Pre/post baseline equivalence (M7) — system self-heals cleanly after both incidents

---

## Manual Audit Additions

Patterns identified through manual inspection that the profiler missed or would have mischaracterized:

| # | Finding | How discovered | Why profiler missed it |
|---|---------|---------------|----------------------|
| M1 | **429s are one-client, not one-agent** | URL-level triage: cross-referenced 429s by client_id | Profiler would report "Chrome has 283 429s, other agents have 0" — technically true but causally wrong. Agent is spurious; client is causal. |
| M2 | **Incident 1 is service-1, not system-wide** | Server × status code cross-tab filtered by time window | Profiler's aggregate cross-tab shows service-1 has more errors, but doesn't reveal the temporal concentration. 30s bin aggregation masks the per-server story. |
| M3 | **503 burst is sub-10-second** | Multi-resolution analysis of incident window | Profiler operates at row level, not temporal bins. The concentration of 414/426 503s in a single 10s window is invisible without time-series decomposition. |
| M4 | **Collateral latency on non-failing servers** | Degraded success analysis filtered by server during incident 1 | Profiler can compute latency distributions but doesn't partition by incident windows or correlate failure on one server with degradation on another. |
| M5 | **No URL-level error clustering despite thousands of URLs** | Per-URL error analysis with minimum traffic threshold | Profiler would flag high cardinality and compute stats, but wouldn't distinguish "no signal because uniform" from "no signal because sample size too small." Both apply here, for different URL types. |
| M6 | **Duration, response_size, request_size all share suspicious minimums** | Numeric summary review | Profiler reports these as statistics but doesn't flag the coincidence of all three having round-number floors (1000, 100, 100). |
| M7 | **Pre- vs post-incident baseline: no material difference** | Two-proportion z-test (p=0.23) on 5xx rate, Mann-Whitney U (p=0.032) on latency. 5xx: 3.11% vs 2.96% (0.15pp, not significant). Latency: p50 differs by 0.6ms, p95 by 1.7ms (statistically detectable, practically irrelevant). | Validates baseline window choice — pre-incident is not contaminated. Post-incident recovery dynamics don't distort the baseline. |
| M8 | **Incident 1 tail (500s) is service-1 recovery, not redistribution overload** | Per-server 500 rate at 10s resolution: service-1 spikes to 8.4–9.9% in 19:01:30–19:01:50 while service-2/3 stay at 1.5–4.3% (normal range). | The collateral damage on service-2/3 (finding X6) was latency degradation only, not error rate increase. service-1 was still recovering when the 503s stopped — requests queued during the outage were timing out as 500s. |
| M9 | **GET ratio shift hypothesis: retired** | GET ratio flat at 88.3–90.7% across all 10s bins, all servers, both incidents. Per-server during incident 1: service-1 90.1%, service-2 89.6%, service-3 89.9%. | No evidence of retry storms via request type composition. If retries occurred, they maintained the same GET/POST/PUT mix as normal traffic. Methodology assumption in PROCESS.md Part 1.2 must be retired as a negative finding. |
| M10 | **Baseline 5xx variation is Poisson noise, not real variation** | Chi-square test for homogeneity: χ²=9.58, df=9, p=0.39. Observed std (11.4 errors/bin) matches Poisson predicted (11.8). 95% CI on true rate: 2.96–3.28%. | The system has a stable, persistent ~3.1% 500 rate. The 2.70–3.62% bin-to-bin range is sampling noise, not genuine fluctuation. SLO calibration should use 3.1% as a point estimate, not a range. |
| M11 | **Incident 2: rate limiter fully contained blast radius for legitimate users** | Burst client: 144/5,111 = 2.82% 500 rate. Legitimate users: 124/4,228 = 2.93% (below baseline 3.11%). Legitimate latency during burst: p50=37.4ms, p95=177.3ms — identical to baseline. Degraded 200 rate: 5.15% vs 5.00% baseline. | The 268 500s are split ~50/50 between burst client and legitimate traffic, but legitimate error rate and latency are at or below baseline. No crowding-out effect. The rate limiter worked precisely as intended. |
