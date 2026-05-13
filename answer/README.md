# Telemetry Analysis Case Study — Submission

## Project Structure

```
├── README.md                      # This file — reproduction instructions
├── report.md                      # Analysis Report (primary deliverable)
├── analysis.ipynb                 # Analysis Code (all cells executed, outputs inline)
├── requirements.txt               # Pinned Python dependencies
├── PROCESS.md                     # Decision log — methodology choices and reasoning
├── AI_USAGE.md                    # AI tooling disclosure — prompts, models, collaboration
│
├── run_profiler.py                # One-shot: generate ydata-profiling report
├── triage_profiler.py             # One-shot: extract profiler summary data
├── triage_urls.py                 # One-shot: URL-level error clustering analysis
├── triage_baseline.py             # One-shot: temporal bootstrap and baseline metrics
├── audit_manual.py                # One-shot: manual data audit beyond profiler output
│
├── figures/                       # 9 visualizations (embedded in report.md)
│
└── supporting/                    # Supporting Materials
    ├── data_profile_report.html   # Auto-generated ydata-profiling report (open in browser)
    ├── data_profile_triage.md     # Signal vs. noise evaluation of profiler findings
    ├── slo_definitions.yaml       # Machine-readable SLI/SLO definitions (OpenSLO-style)
    ├── alert_rules.yaml           # Proposed Prometheus/Alertmanager alert rules
    └── derived_metrics.md         # All computed columns, thresholds, and aggregations
```

## Reproducing the Analysis

### Prerequisites

- Python 3.12+
- pip

### Setup

```bash
pip install -r requirements.txt
```

### Running

```bash
jupyter notebook analysis.ipynb
```

Run all cells top to bottom. The notebook reads from `../question/telemetry_dataset.csv` and writes generated figures to `figures/`.

The submitted notebook includes pre-computed outputs — you can review results without re-executing.

## AI Tooling Disclosure

**Model:** Claude Opus 4.6 via Claude Code CLI

**Full disclosure:** See [`AI_USAGE.md`](AI_USAGE.md) for:
- Which portions were AI-assisted vs. human-directed
- Significant prompts used during the analysis
- The collaboration model and division of responsibility

**Process documentation:** See [`PROCESS.md`](PROCESS.md) for the full decision log, including methodology choices, rejected alternatives, and reasoning.
