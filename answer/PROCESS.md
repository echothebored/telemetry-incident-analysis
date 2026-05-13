# Process Log: Telemetry Analysis Case Study

Key decisions and reasoning behind the analysis. For AI tooling disclosure, see [`AI_USAGE.md`](AI_USAGE.md).

---

## Approach

Structure before analysis. The report mirrors the case study's Parts 1/2/3 so the jury can check off each item without searching. Methodology was defined per section before writing any code — the notebook demonstrates the methodology in action.

---

## Key Decisions

### Report structure mirrors the evaluator's rubric

The report maps 1:1 to Part 1 (EDA), Part 2 (Incidents), Part 3 (Recommendations). The jury evaluates against their own rubric; mirroring it means they can check off each item without friction.

### Phase 0 — temporal bootstrap solves the circular dependency

Parts 1.3 and 1.4 need a baseline, but defining "normal" requires knowing which data is healthy — which requires incident detection from Part 2. Resolution: Phase 0 computes 5xx rate per 30s bin, identifies the lowest-error contiguous period (18:56:00–19:01:00), and establishes baseline metrics before Part 1 begins. Multi-resolution validation (1s, 5s, 10s) lets the data determine the right analysis granularity.

### First principles over authority

Every RCA assumption is grounded in mechanics, not citations. Overload → gradual (queuing theory). Deployment → sudden (container lifecycle). Health check failure → total (LB binary decision).

### Part 3 reordered — SLOs before Monitoring

The case study lists Monitoring before SLOs. We reorder because burn-rate alerting requires error budgets, which require SLO targets. Following a structure with a dependency inversion demonstrates compliance, not understanding.

### SLO targets are business decisions, not data decisions

SLO targets encode business tolerance, not data conclusions. With zero business context, prescribing a number from 10 minutes of data oversteps. Framed as a framework: bound the viable range (91.4%–96.89%), show error budget sensitivity, list 8 business inputs required for final target selection. The 429 exclusion is a design choice with 5 stated unknowns, not a fact.

### LB weighting (50/25/25) is a compounding risk factor

The data supports a direct recommendation rather than a qualified suggestion. Six evidence points: redistribution shock nearly doubled (99% vs 50%), failure concentration, underutilization, counterfactual, recovery risk, no visible justification. Recommendation: equalize to 33/33/33.

### Audience-aware framing

Eight integrity passes on the notebook found 50 issues. Rule: Part 1 observes, Part 2 explains, Part 3 recommends. Navigational forward references guide the reader — keep them. Conclusion spoilers — remove them.

---

## Scope Boundaries

**Available data:** 95,015 rows of HTTP request/response telemetry, ~10-minute window. 14 fields including timestamp, server, endpoint, method, status code, latency, client/agent/region identifiers.

**Known gaps:** No infrastructure metrics, no distributed tracing, no deployment logs, no health check config, no application logs, no LB config, no historical baseline beyond 10 minutes.

**In scope:** Statistical analysis, incident detection, hypothesis-driven RCA with confidence levels, impact quantification, data-derived SLO/SLI proposals, monitoring design, traceable improvement recommendations.

**Out of scope:** Confirmed root causes, long-term capacity forecasting, infrastructure-level debugging, cost analysis, industry benchmarks, SLO validation.

**Framing:** The 10-minute window is a self-contained incident study, not a representative sample. Limitations stated upfront in each section, not buried in footnotes.
