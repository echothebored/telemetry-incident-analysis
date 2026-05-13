# Telemetry Incident Analysis

Production telemetry analysis of a three-server microservice system. Identifies two distinct incidents from 95,015 HTTP request-response records over a 10-minute window, performs root cause analysis, and delivers SLO/SLI frameworks, monitoring design, and capacity planning recommendations.

## What's Here

```
question/               # The problem
  INTRO.md              # Case study brief
  telemetry_dataset.csv # 95,015 telemetry events

answer/                 # The analysis
  report.md             # Full analysis report (primary deliverable)
  report.html           # Self-contained HTML version
  analysis.ipynb        # All analysis code (14 cells, outputs inline)
  PROCESS.md            # Decision log — why, not just what
  AI_USAGE.md           # AI tooling disclosure
  walkthrough.md        # Mentor-style walkthrough of the entire analysis
  requirements.txt      # Python dependencies
  README.md             # Reproduction instructions
  figures/              # 9 visualizations
  supporting/           # SLO definitions, alert rules, derived metrics, dashboards
```

## Key Findings

- **Incident 1 (service-1 failure):** Health check failure caused LB removal. The recovery tail (40s) caused 4x more damage than the failure itself (10s) due to lack of graceful draining.
- **Incident 2 (client burst):** Single client at 500x normal rate. Rate limiter contained it — zero legitimate user impact. Completely invisible to standard 5xx/latency monitoring.
- **Baseline 5xx rate (3.11%)** produces ~6x more failures than incident 1's excess. The chronic issue outweighs the acute one.
- **LB weighting (50/25/25)** nearly doubles redistribution shock vs equal weighting. Compounding risk factor with six evidence points.
- **Burn-rate alerting doesn't page** for this system's observed failure mode. Acute threshold detection at 5s granularity is required as a complement.
- **SLO targets are bounded (91.4%–96.89%)**, not prescribed. 8 business inputs required for final selection. The data bounds the range; stakeholders pick the point.

## Reproducing

```bash
cd answer
pip install -r requirements.txt
jupyter notebook analysis.ipynb
# Run all cells top to bottom
```

The notebook reads from `../question/telemetry_dataset.csv` and writes figures to `figures/`. Submitted notebook includes pre-computed outputs.

## Methodology

**Phase 0 — Temporal Bootstrap.** Parts 1.3 (performance) and 1.4 (errors) need a baseline, but defining "normal" requires knowing which data is healthy — which requires incident detection from Part 2. This circular dependency is resolved before analysis begins: compute 5xx rate per 30s bin, identify the longest contiguous healthy period (no 503s, no 429s, 5xx < 4%), and establish baseline metrics from that window (18:56:00–19:01:00 UTC, 300s, 45,070 requests). Multi-resolution validation at 1s, 5s, 10s, and 30s lets the data determine the right analysis granularity.

**Incident detection uses a three-step process.** Step 1: pure threshold detection (5xx > 2x baseline for 2+ consecutive 10s bins) catches the service-1 failure. Step 2: detection gap analysis reveals the client burst is completely invisible to 5xx/latency monitoring — the rate limiter contained it so effectively that no downstream metric breached threshold. Step 3: adding a 429-rate channel catches both incidents with different mechanisms.

**Root cause analysis is hypothesis-driven, not checklist-driven.** Each RCA hypothesis is grounded in first principles — queuing theory predicts gradual onset for overload (not observed), container lifecycle predicts sudden onset for deployment (observed), binary LB decisions predict total failure for health check events (observed). Confidence levels (HIGH, MEDIUM-HIGH, LOW) reflect what the data can and cannot confirm.

**SLO framework bounds the viable range instead of prescribing a target.** With 10 minutes of data and zero business context, picking a number is indefensible. The analysis bounds the range (91.4%–96.89%), shows error budget sensitivity across candidate targets, demonstrates that burn-rate alerting is blind to this system's acute failure mode, and lists the 8 business inputs required for final target selection.

**Traceability.** Every recommendation traces to an observed problem. Every conclusion carries an explicit confidence level. Every limitation is stated in the section where it matters. All derived metrics, thresholds, and computed columns are documented in `answer/supporting/derived_metrics.md` for independent verification.

Full decision log: [`answer/PROCESS.md`](answer/PROCESS.md). Mentor-style walkthrough of every analytical choice: [`answer/walkthrough.md`](answer/walkthrough.md).
