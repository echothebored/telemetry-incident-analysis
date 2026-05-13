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

The analysis solves a circular dependency: defining "normal" requires incident-free data, but finding incidents requires knowing what's normal. Phase 0 (temporal bootstrap) breaks this cycle by identifying the healthiest contiguous window before analysis begins.

Every recommendation traces to an observed problem. Every conclusion carries an explicit confidence level. Every limitation is stated where it matters.

Full methodology and decision reasoning in `answer/PROCESS.md`.
