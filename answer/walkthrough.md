# Case Study Walkthrough

A mentor-style walkthrough of the telemetry analysis case study. Written as if teaching a junior DevOps engineer the reasoning behind every decision — what we did, why we did it, what most people get wrong, and how to defend each choice.

---

## Part 0: Before You Touch Any Code

### Read the brief twice

The evaluation criteria are listed in order:

1. **Judgment and Focus** — listed first for a reason
2. Technical Analysis
3. Problem Solving
4. Communication

They bold-printed: *"We value depth over breadth."* That tells you something critical — they'd rather see you nail 3 findings than skim 15.

Most people make the mistake of trying to answer every bullet point in the suggested areas list. Don't. Those are suggestions, not a checklist. The brief says so explicitly: *"intentionally open-ended."*

**The trap:** Treating this as a homework assignment where you need to check every box. The real test is whether you can identify what matters most and go deep on it.

### Know your data before you analyze it

Before any fancy analysis, answer basic questions:

```python
df.shape              # How much data?
df.dtypes             # Are the types right?
df.head()             # What does a row look like?
df.describe()         # What are the distributions?
df['timestamp'].min(), df['timestamp'].max()  # Time window?
df['server_id'].nunique()                     # How many servers?
df['response_status_code'].value_counts()     # Health overview?
df.isnull().sum()                             # Missing data?
```

That's your **triage panel**. Every single time you get a new dataset in production — logs, metrics, traces — this is what you do first. You're answering:

1. How much data do I have? (shape)
2. Are the types right? (dtypes — timestamp is probably a string, convert it)
3. What's the time window? (min/max timestamp)
4. How many services? (server_id unique values)
5. What's the health look like? (status code distribution)
6. Is anything missing? (null check)

**Why these specifically?** In a real incident, you have maybe 10 minutes before someone asks "what's going on?" These six questions let you say something intelligent fast. They separate "I'm looking into it" from "We have 95k requests across 3 servers over 10 minutes, and I'm already seeing elevated 5xx rates on service-1."

---

## Part 1: The Strategic Decisions

These are the choices that separate a junior answer from a principal-level one.

### Decision 1: The Circular Dependency Problem

The brief asks you to do EDA (Part 1) before Incident Detection (Part 2). But here's the trap:

To analyze performance and errors (Part 1.3, 1.4), you need a **baseline** — what does "normal" look like? But to define "normal," you need to know which data is from healthy operation. And to know *that*, you need to identify the incidents... which is Part 2.

**Most people just use the whole dataset as baseline.** That's wrong. If there's an incident in your data, your "normal" includes the incident, and every comparison is polluted.

The solution is **Phase 0: Temporal Bootstrap.** Before doing anything else:

1. Compute the 5xx rate per 30-second bin across the entire 10 minutes
2. Find the longest contiguous window with no 503s, no 429s, and 5xx below 4%
3. That's your baseline proxy: **18:56:00–19:01:00** (300 seconds, 45,070 requests)

**Why 30-second bins?** Fine enough to see incident boundaries, coarse enough to suppress noise. We validated at 1s, 5s, 10s, and 30s. 10-second bins provide the best balance for incident analysis. 30-second bins are used for trend overviews.

**Why this matters:** Every number in the report is compared against this baseline. If the baseline is contaminated, every conclusion is wrong. Stating the selection criteria (no 503s, no 429s, 5xx < 4%, minimum 100 requests per bin) makes it reproducible — the jury can verify it independently.

### Decision 2: Verify the Duration Unit

The `duration` column has values like `19773`. Is that 19.7 milliseconds or 19.7 seconds?

The brief says microseconds. But you verify anyway — the max value is `7,778,093`. If that were milliseconds, it'd be 7,778 seconds (2+ hours), which is impossible in a 10-minute window. In microseconds, it's 7.8 seconds — plausible for a timeout.

**Why this matters:** In production, nobody labels columns correctly 100% of the time. Always sanity-check units. Getting the unit wrong means your entire latency analysis is off by 1000x. The report states the verification explicitly so the reader knows it was checked, not assumed.

### Decision 3: The 50/25/25 Load Balancer Split

Looking at the full dataset, traffic splits roughly 41/30/29 across three servers. Most people would report that and move on.

But the healthy-window split is **50/25/25**. The full-dataset number is depressed for service-1 because it was *offline during the incident*. The true routing policy is 2:1:1.

**Why this matters enormously:** When service-1 goes down, its traffic has to go somewhere. Under 50/25/25, the surviving servers go from ~38 req/s to ~75 req/s — a **99% increase**. Under equal weighting (33/33/33), they'd go from ~50 to ~75 — a **50% increase**. The weighting *nearly doubles* the blast radius of the most likely server to fail.

This is the kind of finding that makes a jury sit up. It's not just "here's a number" — it's "here's how this number compounds risk." Six evidence points support the recommendation to equalize:

1. Redistribution shock nearly doubled (99% vs 50%)
2. Failure concentration — most-loaded server is most likely to fail first
3. Underutilization — service-2/3 sit idle while service-1 runs at 2x
4. Counterfactual — service-1 already proves ~75 req/s is sustainable
5. Recovery risk — at 50% weight, service-1 gets 75 req/s immediately on return
6. No visible justification — all three servers have identical baseline latency

### Decision 4: Reordering Part 3 — SLOs Before Monitoring

The brief lists Monitoring, then SLOs. We flip the order.

Burn-rate alerting requires error budgets. Error budgets require SLO targets. If you write alert thresholds before defining your SLO, you're configuring alerts with no reference frame.

**Defending this to the jury:** Following a structure with a dependency inversion demonstrates compliance. Fixing it demonstrates understanding. The PROCESS.md file states this decision explicitly so the jury knows it was intentional.

### Decision 5: SLOs Are Business Decisions

The biggest trap in the whole case study. You have 10 minutes of data. Most people will say "I recommend a 99.9% SLO" or "the SLO should be 95%."

Both are wrong. You don't have the business context to pick a number.

What you *can* do:

- **Bound the viable range:** 91.4% (below which incident 1 is invisible) to 96.89% (the observed baseline — anything above is immediately breached)
- **Show the sensitivity table:** at each target, what does the baseline consume? What does incident 1 burn?
- **List the 8 business inputs required** to actually pick the point

This is covered in depth in the SLO Framework section below.

### Decision 6: First Principles Over Authority

Every root cause hypothesis is grounded in mechanics, not citations:

- Overload produces gradual degradation (queuing theory: as utilization approaches 1, wait time grows toward infinity)
- Deployment produces sudden onset (container lifecycle: old container stops, new one starts)
- Health check failure produces total binary failure (LB makes a binary healthy/unhealthy decision)

**Why not cite the SRE book?** Because "Google says so" doesn't prove your hypothesis fits this data. Showing that the observed behavior matches what queuing theory predicts for this failure mode — that proves it.

### Decision 7: Report Structure Mirrors the Rubric

The report maps 1:1 to the brief's Part 1 (EDA), Part 2 (Incidents), Part 3 (Recommendations). This is deliberate. The jury evaluates against their own rubric. Mirroring it means they can check off each item without friction — they don't have to search for where you addressed each topic.

### Decision 8: Audience-Aware Framing

Rule: Part 1 observes, Part 2 explains, Part 3 recommends.

Part 1 doesn't say "this caused the incident" — it says "503s are exclusive to service-1." Part 2 says "this is consistent with a health check failure." Part 3 says "review health check configuration."

Each section does its job. Forward references guide the reader ("implications explored in Part 2"). Conclusion spoilers are removed — don't tell the reader the answer before you've shown the evidence.

---

## Part 2: Exploratory Data Analysis (What We Found)

### System Characteristics (1.1)

The triage reveals:

- **95,015 rows**, 14 columns, zero nulls, zero duplicates
- **600 seconds** (18:55:59 to 19:05:59 UTC)
- **3 servers** behind a weighted round-robin LB (50/25/25 in healthy window)
- **5 endpoint patterns:** `/users`, `/posts`, `/users/{id}`, `/posts/{id}`, `/users/{id}/posts` — roughly equal volume
- **Read-heavy:** GET 90%, POST 9%, PUT 1%
- **Status codes:** 200 (96.1%), 500 (3.1%), 503 (0.4%), 429 (0.3%), 404 (0.1%)

The 503s and 429s are concentrated in specific time windows — incident signals. The 500s are distributed across the full timeline — persistent baseline noise.

### Traffic Patterns (1.2)

**Request volume:** Stable at ~150 req/s. No temporal trend in 10 minutes — expected given the short window. The only volume anomaly is the incident 2 burst at 19:04:00 (2.07x baseline).

**Load balancer is geography-agnostic.** All five regions send traffic in the same ~50/25/25 ratio. No server-region affinity. This simplifies impact analysis: no region is preferentially exposed to a specific server's failure.

**Client concentration follows a steep power law:**

- Top 1 client: 5.5% of all traffic
- Top 100 clients (5% of population): 48.5% of traffic
- Median requests per client: 12

The dominant client (`yNGr0ru8jkXx`) trickles at 1-3 req/bin normally, then bursts to ~5,100 requests in one 30-second bin. That's incident 2.

**GET ratio is stable across incidents.** We hypothesized that GET ratio shifts during incidents would indicate retry storms (browsers retry GETs but not POSTs). No shift occurred. Hypothesis retired as a negative finding — worth stating because it rules something out.

**South region has higher latency.** p50 of 44.3ms vs ~37ms for other regions (~19% higher). Consistent across all time periods, not incident-related. Likely geographic distance or routing.

**Device types and agents:** Error rates uniform across all dimensions (0.48pp range across agents). Failures are server-side, not client-triggered.

### Performance Analysis (1.3)

**Use percentiles, not means.** Latency distributions are heavy-tailed. The mean is useless because a few 2-second timeouts drag it up, hiding what most users actually experience. Always report p50, p95, p99.

**The key finding — latency by status code:**

| Status | p50 | p95 | Interpretation |
|--------|-----|-----|----------------|
| 200 | 38.2ms | 175.2ms | Normal processing |
| 500 | 45.9ms | 2,091ms | **Timeout behavior** — requests queue, wait, then fail |
| 503 | 42.7ms | 193ms | **Fast rejection** — LB returns 503 before reaching backend |

The 500 latency profile is critical. Requests that return 500 spend 10-15x longer than healthy requests at the tail. This is not fast-fail — something is timing out. The 503 profile has latency similar to 200s — consistent with the LB rejecting requests before they reach the backend.

This distinction matters for root cause analysis. 500s and 503s have completely different mechanisms. Conflating them would lead to wrong conclusions.

**POST/PUT latency is ~2x GET** at every percentile. A single latency SLO threshold would disproportionately flag writes. Noted for SLI design.

**Degraded success:** A 200 response with latency above the healthy p95 (175.2ms) is "functionally degraded" — the request succeeded but user experience was poor. By definition, ~5% of healthy 200s exceed this. During incident 1, the rate rises to 7.6% (10.4% in the peak bin). This metric captures impact that error rate alone misses.

**Response size confirms genuine errors.** 500/503 responses are ~10x smaller than 200s (~300 bytes vs ~3,050 bytes). These are real error bodies, not mislabeled successes.

### Error Analysis (1.4)

**Error classification framework — not all non-200s are equal:**

- **5xx (500, 503):** SLO-relevant failures. Genuine service failures.
- **429:** Rate limiter working correctly. All 283 from one client. Excluded from error budget (with caveats).
- **404:** Normal application behavior. 81 total, scattered, uncorrelated with incidents.

**The baseline 5xx is persistent and stable.** 3.11% during the healthy window. Chi-square test across bins yields p=0.39 — the bin-to-bin variation is Poisson noise, not genuine fluctuation. The system produces 500s at a steady rate like clockwork.

**503s are exclusive to service-1 and to incident 1.** All 426 503s came from service-1, concentrated in two 10-second bins. Zero from service-2/3 at any point. This exclusivity strongly suggests infrastructure, not application code.

**No endpoint-specific or agent-specific error clustering.** 5xx rates by endpoint: 0.17pp spread. By agent: 0.48pp spread. Errors are infrastructure-level.

---

## Part 3: Incident Detection and Analysis

### Finding the Incidents

The detection method is a three-step process, and the order matters.

**Step 1 — Pure threshold detection.** Define "anomalous" as 5xx rate exceeding 2x baseline (>6.2%) for 2+ consecutive 10-second bins. Simple, mechanical, no judgment required.

This flags one bin: **19:01:10** — 5xx hits 29%. But only one bin exceeds threshold, not two consecutive. The acute phase is so short that the rule technically doesn't trigger. The signal is still unmissable — you investigate anyway.

**Step 2 — Check what the threshold missed.** At 19:04:00, traffic spikes to 4.2x baseline and 283 429s appear. But 5xx rate? Flat at ~3%. Latency? Flat. Threshold detection is **completely blind** to this event because the rate limiter contained it perfectly.

This is the first lesson: **a contained incident is still an incident.** If you only monitor 5xx and latency, you'll never know it happened.

**Step 3 — Add a 429 channel.** Now you detect both incidents with different mechanisms. Two events, two completely different failure shapes.

### Incident 1: Service-1 Failure (19:01:00–19:02:00)

Here's the timeline at 10-second resolution, per server:

| Time | service-1 | service-2 | service-3 |
|------|-----------|-----------|-----------|
| 19:00:50 | ~3% (baseline) | ~3% | ~3% |
| 19:01:00 | 12 503s appear | ~3% | ~3% |
| **19:01:10** | **96.5% failure (414 503s)** | **~3%** | **~3%** |
| 19:01:20 | 503s stop, 500s ~8% | ~3% | ~3% |
| 19:01:30-02:00 | 500s declining 8% to 3% | ~3% | ~3% |
| 19:02:00+ | Baseline | Baseline | Baseline |

Notice what's happening on service-2 and service-3. **Nothing.** They stay at baseline the entire time. This is a service-1-exclusive event.

That fact alone eliminates a huge category of causes. If this were a bad deployment of application code, all three servers run the same code — they'd all break. If this were a downstream dependency failure, all three servers call the same dependencies — they'd all see it. The exclusivity points to **infrastructure**: something happened to service-1 specifically.

#### The Mechanism: Health Check Failure (HIGH confidence)

Four pieces of evidence:

**1. The status code is 503, not 500.** A 503 means "Service Unavailable" — that's what a load balancer returns when a target fails health checks. A 500 means the application itself errored. These are different failure modes with different causes.

**2. The latency profile confirms it.** 503 responses have a p50 of 42.7ms — normal. They're being rejected *fast*. Compare to 500s: p95 of **2,091ms**. The 500s are queuing and waiting. The 503s are immediate rejections. That's the LB saying "this server is dead, don't even try."

**3. Binary onset.** service-1 went from 0% 503 to near-total failure in under 5 seconds. No ramp-up. No gradual degradation. That's a binary decision — healthy/unhealthy — not a system slowly falling over.

**4. Traffic redistribution.** In the same 10-second bin as the first 503s, service-2 volume jumped ~49% and service-3 jumped ~33%. The LB immediately started sending service-1's traffic elsewhere. That's what happens when a target is removed from rotation.

#### The Trigger: Deployment or Container Restart (MEDIUM-HIGH confidence)

So the LB pulled service-1. Why?

**Overload is unlikely.** If a server is approaching saturation, wait time grows *gradually* toward infinity (queuing theory). You'd see p95 and p99 climbing in the seconds before failure. We checked: **p95 was at baseline in the 10 seconds before the first 503.** No latency precursor. No warning. Just sudden death.

That rules out gradual overload. What causes sudden death?

- Container restart (OOM kill, deployment, scaling event)
- Network partition between LB and service-1
- Health check endpoint failure (dependency check fails)

All three produce the same signature: binary onset, binary recovery, ~10-second duration consistent with container startup time, single-server exclusive.

**We can't confirm which one.** No deployment logs, no infra metrics, no health check config. This is why the confidence is MEDIUM-HIGH, not HIGH. The mechanism is clear (health check failure). The trigger is a hypothesis.

#### The Recovery Tail — This Is the Real Story

Here's what most people miss. The 503s stopped at ~19:01:20. service-1 passed its health checks, the LB put it back in rotation. Incident over, right?

No. Look at 19:01:20 to 19:02:00. **500 errors on service-1 stayed elevated at ~8% for 40 seconds.** Why?

Requests that were in-flight when service-1 went down were sitting in queues, waiting for resources. When service-1 came back, those queued requests timed out as 500s. Of the 341 500s during the incident window, **281 occurred during this recovery tail** — that's 82%.

The healing mechanism (put the server back in rotation) caused continued failures because there was **no draining.** The LB flipped service-1 from "dead" to "fully healthy" in one step, sending it ~75 req/s immediately while it was still processing stale requests.

This is why Recommendation 1 in Part 3 focuses on graceful draining and multi-failure health check thresholds. The 503 burst lasted 10 seconds. The 500 tail lasted 40 seconds. **The recovery was 4x longer than the failure.**

#### Collateral Damage

When service-1 was pulled, service-2 and service-3 absorbed its traffic. Under the 50/25/25 weighting, that's a 99% load increase on each survivor.

Did they break? No — their error rates stayed at baseline ~3%. But their **latency degraded.** The degraded 200 rate rose from the baseline 5% to 8.8% on service-2 and 7.5% on service-3.

The system healed itself. The healing hurt the survivors. Error rate alone wouldn't tell you — you need the degraded success metric to see it.

### Incident 2: Client Burst (19:04:00–19:04:30)

Completely different animal. One client — `yNGr0ru8jkXx` — went from ~0.33 req/s to ~170 req/s. A 500x increase. Chrome, mobile, south region, hitting all endpoints proportionally.

The profile says "broken retry loop" or "runaway script." It's not targeted at one endpoint (which would suggest scraping). It's proportional across all endpoints, which looks like normal traffic at absurd volume.

The rate limiter activated within ~10 seconds. 283 429s issued. **All to that one client.** No other client in the entire dataset received a 429.

Legitimate user impact: **zero.** Error rate at 2.93% (below the 3.11% baseline). Latency at baseline. Degraded success rate at 5.15% (baseline ~5%).

This is a textbook success story for rate limiting. The system did exactly what it should.

**But** — the rate limiter took ~10 seconds to kick in, during which the client sent ~4,800 unthrottled requests. A token bucket with a lower burst allowance would catch it faster. That's why it's a MEDIUM priority recommendation — hardening something that already works, not fixing something broken.

#### The Detection Gap

If you only had 5xx rate and latency monitoring, **you would never know incident 2 happened.** Both metrics stayed flat. The rate limiter completely absorbed the blast.

That's good for users. It's bad for observability. You want to know when someone is hammering your system at 500x normal rate, even if the system handles it. Because next time it might be 5,000x, or distributed across clients, and the rate limiter might not hold.

That's why the report recommends 5 detection channels, not just burn rate. Different failure shapes need different detectors.

### Impact Assessment

Two incidents, two completely different profiles:

| | Incident 1 | Incident 2 |
|--|-----------|-----------|
| **Type** | Infrastructure failure | Client anomaly |
| **Duration** | 60s (10s acute + 40s tail) | 30s |
| **Failed requests** | 767 (490 excess over baseline) | 283 429s (zero legitimate impact) |
| **Detection** | 5xx spike | 429 rate / traffic volume |
| **System response** | Traffic redistribution (caused collateral damage) | Rate limiting (contained perfectly) |
| **Root cause confidence** | MEDIUM-HIGH | HIGH |

**Limitation we state explicitly:** We see requests, not users. 767 failed requests could be 767 users failing once or 77 users retrying 10 times. Without session correlation, we can't distinguish these. The absence of GET ratio shift suggests retry amplification was minimal — but it doesn't prove it.

### Known Unknowns

What additional telemetry would resolve each gap:

| Gap | What it would resolve |
|-----|----------------------|
| Deployment logs | Confirm/deny deployment as incident 1 trigger |
| Health check config | Confirm failure threshold timing and interval |
| Infrastructure metrics (CPU, memory, connections) | Definitively rule out overload |
| Distributed tracing | Map dependency chain, confirm no upstream trigger |
| Client session data | Confirm retry loop mechanism for incident 2 |
| Rate limiter config | Understand threshold, scope (per-client vs per-IP) |

Stating what you don't know is as important as stating what you do. It shows you understand the limits of your analysis. RCA confidence is capped at MEDIUM-HIGH specifically because of the deployment logs gap.

---

## Part 4: SLO Framework

### Why Most People Get This Wrong

The natural instinct when someone says "propose SLOs" is to pick a number. "I recommend 99.9% availability." Sounds professional. It's completely indefensible with 10 minutes of data and zero business context.

Most candidates do one of two things:

- Pick a number from thin air ("99.9%") and sound confident
- Hedge endlessly and commit to nothing

This framework does neither. It says: here's exactly what we know, here's the range, here's how each point in the range behaves, and here's what we'd need to pick the final number.

### Start With SLIs, Not SLOs

An SLO is a target. An SLI is what you're measuring. You can't set a target until you know what the thermometer reads.

**SLI-1: Availability** — `non-5xx requests / total requests`

Simple ratio. But you immediately hit classification decisions:

- **404 — Exclude.** A client asked for something that doesn't exist. Normal application behavior. Straightforward.

- **429 — Design choice with unknowns.** We recommend excluding, but we state five things we don't know:
  1. Is the rate limiter threshold correctly configured?
  2. Do legitimate users hit 429s under other conditions?
  3. What does the caller's contract say?
  4. What does the caller *experience* when rate-limited?
  5. Could a misconfigured rate limiter silently hide real failures?

If you exclude 429s and the rate limiter is broken, you're lying to yourself about availability. The report states all five unknowns rather than pretending the decision is obvious.

**SLI-2: Latency** — `successful requests within threshold / total successful requests`

Important finding: **for this system, latency barely moved during incidents.** The gap between healthy and incident 1 is only 1-3 percentage points across all candidate thresholds. Incident 1's primary signal was error rate, not latency.

That tells you about this system's failure modes. It fails by **breaking** (503s, 500s), not by **slowing down**. Availability is the primary detection channel. Latency SLI catches brownouts — slow degradation — not blackouts.

Also: POST/PUT latency runs ~2x GET. A single threshold would disproportionately flag writes.

**SLI-3: Quality (Composite)** — a request is "good" only if non-5xx AND within latency threshold. One number for dashboards.

### Bounding the Viable Range

**Upper bound: 96.89%.** That's observed baseline availability. Set your target above this and you're in breach from day one. Useless.

**Lower bound: ~91.4%.** That's incident 1's window availability. Set your target below this and incident 1 doesn't breach the budget. Your SLO can't see the worst event in your data. Also useless.

**Viable range: 91.4%–96.89%.**

### Error Budget Sensitivity — The Core Insight

| Target | Budget | Baseline consumption | Inc 1 burn rate | Inc 2 burn rate |
|--------|--------|---------------------|----------------|----------------|
| 92.0% | 8.0% | 38.9% | 1.1x | silent |
| 94.0% | 6.0% | 51.9% | 1.4x | silent |
| 95.0% | 5.0% | 62.3% | 1.7x | silent |
| 96.0% | 4.0% | 77.8% | 2.2x | silent |
| 96.5% | 3.5% | 88.9% | 2.5x | silent |

Read this carefully. At 96.5% target:

- Your error budget is 3.5%
- The **baseline alone** consumes 88.9% of it (3.11 / 3.5 = 0.889)
- Incident 1 burns at 2.5x during its 60 seconds
- Incident 2 is **silent at every target** — the rate limiter kept legitimate errors at baseline

**What does incident 1 actually cost in a monthly budget?**

At 96.5%, extrapolate 150 req/s over 30 days: ~389 million monthly requests. Error budget: ~13.6 million allowable 5xx. Incident 1 produced 490 excess failures. That's **0.004% of the monthly budget.**

A 60-second incident is a rounding error in a 30-day error budget.

**The SLO is really tracking whether the baseline 5xx rate stays stable, not whether short incidents occur.** The baseline steady-state eats ~89% of your budget at 96.5%. A 1-point reduction in baseline 5xx (3.11% to 2.11%) frees up more budget than preventing a hundred incident-1s.

This is why investigating the baseline 5xx rate (Recommendation 4) is marked HIGH priority. It's the dominant factor in SLO health. In the same 10-minute window, baseline 5xx accounts for ~2,950 failures vs 490 excess from incident 1 — **the baseline produces ~6x more failures than the incident's excess.**

### The 8 Business Inputs

The data bounds the range. The business picks the point:

1. **Service criticality** — what does this API do? 3.11% is catastrophic for payments, maybe fine for a content feed
2. **User tolerance** — humans waiting for page loads, or machines with retry logic?
3. **Cost of SLO breach** — feature freeze? Pager? Executive review?
4. **Cost of over-alerting** — team's operational maturity, on-call capacity
5. **Improvement trajectory** — is the 3.11% baseline being actively worked on?
6. **Dependency SLOs** — what do upstream callers expect from you?
7. **SLO window** — 30-day rolling vs shorter windows that make acute incidents more visible
8. **Rate limiter contract** — validate the 429 exclusion against config and client agreements

**Recommendation:** Start at 95-96%, instrument burn-rate alerting, iterate after 2-4 weeks of real data. The first SLO is a hypothesis — the error budget tells you if it's right.

### Why This Approach Works

The jury is evaluating judgment. Prescribing a number from 10 minutes of data is bad judgment. Saying "I can't answer this" is a non-answer. Bounding the range and showing the sensitivity is the principal-level move.

---

## Part 5: Monitoring Design

### The Design Principle

Every detection channel traces to an observed gap. No generic "best practices." The value is in the traceability chain: observed X, missed by Y, recommend Z.

### Burn Rate Doesn't Page for This Incident

Standard SRE burn-rate alerting tiers:

| Tier | Window | Burn rate | Response |
|------|--------|-----------|----------|
| Critical | 1 hour | 14.4x | Page |
| High | 6 hours | 6x | Page |
| Medium | 1 day | 3x | Ticket |
| Low | 3 days | 1x | Review |

At a 95% target, incident 1's blended 60-second error rate produces **~1.7x burn**. Below the ticket threshold. At 96%: **~2.2x**. Still below ticket.

**Burn-rate alerting does not page for incident 1.** Not at any viable target.

This isn't a flaw in burn rate. It's a property of the failure shape. Burn rate excels at catching sustained degradation — 6% error rate for 3 hours. This incident was a 60-second spike with sharp onset and recovery. Burn rate smooths it away.

**The lesson:** If someone tells you "just implement burn-rate alerting" and calls it done, they haven't thought about what failure shapes their system actually produces. Different failures need different detectors.

### The Five Detection Channels

Each channel maps to an observed gap:

**Channel 1 — Availability burn rate (SLI-1).** Multi-window burn rate on non-5xx proportion. Catches sustained degradation (brownouts, memory leaks, overload). Detects incident 1 at review tier. Misses short acute failures and contained incidents. This is the PRIMARY channel for the general case — most production incidents last longer than 60 seconds.

**Channel 2 — Acute 5xx spike.** Threshold-based: 5xx rate exceeding 3x baseline for 2+ consecutive bins. Complements burn rate by catching short severe spikes that windowed burn rate smooths away.

**Critical detail: requires 5-second granularity.** At 10-second bins, the 2-consecutive rule never fires for incident 1's <15-second acute phase. At 5-second bins, the alert fires ~10 seconds after the first 503. This means the default Prometheus scrape interval (15s) is too coarse — it must be reduced for this system.

This is threshold detection *alongside* burn rate, not instead of it. They catch different failure shapes: threshold for acute, burn rate for chronic.

**Channel 3 — Rate limiter activity (429 rate).** Triggers when 429 count transitions from 0 to non-zero. Catches contained incidents invisible to 5xx/latency (incident 2). Whether this pages or tickets depends on the 429-exclusion decision.

**Channel 4 — Traffic volume anomaly.** Request rate exceeding 2x baseline for 2+ consecutive bins. Catches demand surges before they cause failures. High false-positive risk — requires operational tuning.

**Channel 5 — Per-server divergence.** Single server's 5xx rate diverging from fleet average by >10pp. Catches partial failures diluted in aggregate metrics.

During incident 1: service-1 hit 96.5% while service-2/3 stayed at 3%. The aggregate peaked at ~29%. With 3 servers, single-server failure is still visible in aggregate. **With 100 servers, it becomes invisible.** This channel is essential at scale.

### Implementation Priority

Start with Channels 1 + 2. For this system's observed failure mode, Channel 2 is the faster detector. Channel 1 protects against sustained degradation that 10 minutes cannot represent. Add Channels 3-5 based on operational experience.

### Leading Indicators

**Latency as a precursor:** For incident 1, a marginal p99 latency precursor appeared ~4 seconds before the first 503 at 1-second resolution. At 5-second resolution, it's smoothed away. 4 seconds is not actionable for humans and marginal even for automation. This is consistent with a binary event (health check failure), not gradual degradation.

Latency-based leading indicators remain valuable for overload failures (gradual queue buildup) — a common failure mode not observed in this window.

**GET ratio as retry storm indicator:** No shift detected. Hypothesis retired as a negative finding. Negative findings are worth stating because they close investigation paths.

### The Alert Rules File

The submission includes `supporting/alert_rules.yaml` with Prometheus/Alertmanager rules for all 5 channels. Each rule has:

- The PromQL expression calibrated against observed data
- Annotations explaining what it catches and what it misses
- Implementation notes (e.g., Channel 2 requires 5s scrape interval)

The `{{ SLO_TARGET }}` is a template variable — set it to the chosen target from the SLO definitions.

---

## Part 6: System Improvement Recommendations

### The Design Principle

Every recommendation traces to an observed problem. Structure: observed X, caused by Y, recommend Z, this interrupts the chain because W.

No generic "best practice" lists. The value is in the traceability.

### Recommendation 1: Health Check and LB Configuration (HIGH)

**Observed:** service-1 went from 0% to 100% 503 in <5 seconds. Binary onset and recovery.

**Mechanism:** Health check failure causes LB removal. 503 = LB fast-rejection.

**Recommendations:**
1. Multi-failure health check threshold (2-3 consecutive failures) to prevent flapping
2. Graceful draining — "draining" state where server stops accepting new connections but completes in-flight requests
3. Health check logging — without logs, this remains a hypothesis

**Why draining matters:** Of the 341 500s during incident 1, 281 occurred during recovery (19:01:20-19:02:00). The LB flipped service-1 from "dead" to "fully healthy" in one step. Draining would eliminate the 500 recovery tail.

### Recommendation 2: Traffic Redistribution Safety (HIGH)

**Observed:** When service-1 was pulled, service-2/3 absorbed traffic. Volume increased ~49% and ~33%. Error rates stayed baseline but latency degraded.

**Recommendations:**
1. N-1 capacity headroom — with equal weighting, redistribution shock halves
2. Traffic-aware load shedding during redistribution
3. Connection draining during server removal

**The key insight:** The healing mechanism caused collateral damage. The system "fixed" itself by making things worse for everyone else.

### Recommendation 3: Rate Limiter Hardening (MEDIUM)

**Observed:** Rate limiter worked. Contained the blast. But took ~10 seconds to activate.

**Recommendations:**
1. Verify configuration (per-client, per-endpoint, global?)
2. Consider lower burst allowance for earlier activation
3. Monitor rate limiter activity (Channel 3)

**The framing matters:** This is hardening, not fixing. The report says so explicitly. Don't present a working system as broken.

### Recommendation 4: Investigate Baseline 5xx Rate (HIGH)

**Observed:** 3.11% 5xx, Poisson-stable, uniform across servers and endpoints.

**Why HIGH priority:** The baseline produces ~6x more failures than incident 1's excess from the same 10-minute window. Over any longer horizon, this ratio only grows. Reducing baseline 5xx has a larger effect on error budget than preventing any single incident.

**Recommendations:**
1. Instrument 500 responses with error context (structured error metadata)
2. Determine whether 3.11% is accepted or unknown

**Caveat stated:** "3.11% is too high" assumes a user-facing API. For some workloads, this may be acceptable. Business judgment.

### Recommendation 5: 500 Timeout Pattern (MEDIUM)

**Observed:** 500s are slow-fail (p95 = 2,091ms), not fast-fail. Requests queue, wait, then timeout.

**Why it matters for users:** If clients retry on 500, total perceived latency is ~2,130ms (wait 2.1s for 500, retry, wait 38ms for 200). Fast-failing at ~10ms would reduce total to ~48ms. That's 56x better.

**Recommendations:**
1. Investigate the timeout chain — what is the 500 waiting for?
2. Set explicit request timeout at the service level
3. Implement circuit breaker on the failing dependency

### Load Balancing: Equalize to 33/33/33 (HIGH)

This is the recommendation with the strongest evidence chain. Six supporting points:

1. **Redistribution shock** — 99% increase under 50/25/25 vs 50% under 33/33/33
2. **Failure concentration** — most-loaded server is most likely to fail first
3. **Underutilization** — service-2/3 sit idle at ~37 req/s
4. **Counterfactual** — service-1 already runs at ~75 req/s with normal latency, proving the capacity exists
5. **Recovery risk** — at 50% weight, returning server gets 75 req/s immediately
6. **No visible justification** — identical baseline latency across all three servers

**If the weighting is intentional** (service-1 has more hardware), it should be documented with the risk trade-off acknowledged. If it's not intentional, equalizing is pure risk reduction with zero cost.

### Operational Procedures

Two runbook paths, one per incident type:

**Runbook A (infrastructure failure):** Channel 2 fires, Channel 5 confirms single server. Check which server, then: health check status, deployment pipeline, infra metrics. Escalate if >1 server or recovery >5 minutes.

**Runbook B (traffic anomaly):** Channel 3 fires, Channel 4 confirms volume. Check single client vs distributed. If contained, monitor. If not, escalate.

These runbooks are derived from what actually happened, not from a textbook.

---

## Part 7: Capacity Planning

### N-1 Survival

**Current throughput:** 150.2 req/s across 3 servers. service-1: ~75 req/s, service-2/3: ~38 req/s each.

**Observed N-1 behavior:** During incident 1, the system survived without error rate increase but with latency degradation. However, service-1 was only fully down for ~10 seconds. During the 500 tail, it was back in rotation. A true sustained N-1 would put more pressure on remaining servers.

**Scaling recommendation:** Either add a 4th server (each handles ~38 req/s normally, ~50 during N-1) or optimize per-server capacity. Can't determine which is more cost-effective without pricing data.

**Limitation stated:** 10 minutes at ~150 req/s. Can't project traffic growth, peak/off-peak, seasonal variation. These are minimums, not targets.

### Geographic Distribution

No server-region affinity. No geographic concentration of risk under current routing. Current distribution is appropriate.

South region's ~19% higher latency is geographic, not infrastructure. Region-aware routing could reduce it but would introduce geographic concentration risk (server failure = regional outage). Trade-off requires business input.

---

## Part 8: Supporting Materials and Code Quality

### What the Submission Package Contains

| File | Purpose |
|------|---------|
| `report.md` / `report.html` | Primary deliverable — the analysis report |
| `analysis.ipynb` | All analysis code, sections map 1:1 to report |
| `PROCESS.md` | Decision log — shows deliberate thinking |
| `AI_USAGE.md` | AI collaboration disclosure |
| `supporting/data_profile_triage.md` | Signal/noise/surprising classification of profiler findings |
| `supporting/slo_definitions.yaml` | Machine-readable SLI/SLO definitions (OpenSLO-style) |
| `supporting/alert_rules.yaml` | Prometheus/Alertmanager rules for all 5 channels |
| `supporting/derived_metrics.md` | Every computed column, threshold, and aggregation |
| `run_profiler.py`, `triage_*.py`, `audit_manual.py` | One-shot scripts for profiling and triage |

### Why the Supporting Materials Matter

The **data_profile_triage.md** classifies every profiler finding as signal (10), noise (7), or surprising (6). This shows the jury that we didn't just run a profiler and dump the output — we evaluated what the profiler found and decided what matters. 11 additional manual investigations (M1-M11) go beyond the profiler's reach.

The **slo_definitions.yaml** is machine-readable. The jury could wire it into their own monitoring. It includes the status code classification, candidate thresholds with gap analysis, the viable range, and the sensitivity table.

The **alert_rules.yaml** includes actual PromQL expressions calibrated against observed data, not pseudocode. Each rule has annotations explaining what it catches and what it misses.

The **derived_metrics.md** enables verification of every number in the report. Every threshold, every computed column, every aggregation is documented with its derivation. The jury doesn't have to trust us — they can check.

### The Profiling Pipeline

Before the notebook, four scripts did the initial triage:

1. **run_profiler.py** — generates ydata-profiling HTML report (automated column-level exploration)
2. **triage_profiler.py** — extracts key findings from the profiler output
3. **triage_urls.py** — URL-level error clustering analysis
4. **triage_baseline.py** — temporal bootstrap and baseline metric computation
5. **audit_manual.py** — 11 manual investigations beyond profiler capability

These scripts are documented as "one-shot" — run once, feed findings into the notebook. The notebook is the analysis; the scripts are the scaffolding that informed it.

---

## Part 9: What Makes This Principal-Level

### Judgment Over Completeness

The brief says "depth over breadth." The report picks the findings that matter most (baseline 5xx, LB weighting, recovery tail, burn rate blind spot) and goes deep. It doesn't try to cover every suggested bullet point.

### Every Number Is Verifiable

Baseline comes from a defined window with stated criteria. Thresholds are derived from baseline with stated multipliers. Incident metrics are computed from defined time windows. The derived_metrics.md file makes every calculation auditable.

### Confidence Levels and Caveats

RCA has explicit confidence levels (HIGH, MEDIUM-HIGH, LOW). Every limitation is stated in the section where it matters, then consolidated at the end. The 429-exclusion has five stated unknowns. The SLO has eight stated business inputs.

This signals intellectual honesty. You know what you know and you know what you don't.

### Traceability

Every recommendation traces to an observation. Observation to mechanism to recommendation to how-it-interrupts-the-chain. No recommendation exists without evidence. No evidence exists without a citation to the data.

### The Surprising Findings

The things that would make a jury sit up:

1. **The baseline 5xx produces 6x more failures than the incident's excess.** Most people focus on the dramatic incident and miss the chronic issue.
2. **Burn-rate alerting doesn't page for this incident.** Most people would set up burn rate and call it done.
3. **The recovery tail is 4x longer than the failure.** The healing mechanism was the primary damage vector.
4. **The LB weighting nearly doubles the blast radius.** Most people report the traffic split and move on.
5. **SLO targets can't be derived from data alone.** Most people pick a number. This framework bounds the range and shows what's needed to narrow it.

---

## Summary

The case study tests whether you can think like a principal engineer with 10 minutes of data and zero business context. The answer isn't in the numbers — it's in knowing which numbers matter, what they mean, what they don't mean, and what you'd need to know to take action.

Structure before analysis. Baseline before comparison. Mechanism before recommendation. Evidence before assertion. Limitations stated, not hidden.
