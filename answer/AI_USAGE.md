# AI Tooling Usage Disclosure

## Tools and Models

| Tool | Model | Purpose |
|------|-------|---------|
| Claude Code (Anthropic CLI) | Claude Opus 4.6 | Sparring partner: methodology design, code generation, adversarial review |

## How AI Was Used

Claude generated code and stress-tested conclusions. I drove methodology, scope decisions, and analytical judgment. The prompts below show moments where I redirected the analysis — but the collaboration was bidirectional. Claude's contributions that I adopted without pushback: the nested hypothesis structure for RCA (mechanism → trigger, not competing alternatives), multi-resolution validation as a standard practice before committing to a bin size, and the self-challenge passes that caught 50 issues across 8 reviews of the notebook.

## AI-Assisted Portions

| Portion | Type of Assistance |
|---------|-------------------|
| analysis.ipynb code cells | Code generation + review (each cell reviewed before inclusion) |
| report.md | Human-directed, AI-drafted prose, human-reviewed |
| PROCESS.md | Co-authored (decisions are mine, documentation collaborative) |
| Supporting materials (YAML, derived metrics) | Co-authored from analysis findings |

## Significant Prompts

Exchanges that redirected the analysis, in chronological order.

### Methodology before analysis

```
This is a principal-level engineering case study. I need you to challenge 
everything, only offer things when you can actually back it up with facts.
```

```
Before we jump directly into it, don't we need a good structure, foundation? 
Isn't analysis of the data a later step?
```

Established the working standard: structure first, evidence-based reasoning, no shortcuts.

### Report structure follows the evaluator's rubric

```
Our tree should be close to the parts they declared and answering each line clearly.
```

Mirroring the case study's own structure means the jury checks off each item without searching.

### Error classification — not all non-200s are errors

```
Context matters. What if there are edge cases where a certain amount of error is 
expected? Or there is an acceptable bug in production approved by the product team? 
We also don't know the error budget. Do you think you considered all possible angles?
```

Led to the error classification framework: 429s and 404s are the system working correctly, only 5xx counts against SLOs. Error analysis requires an interpretive framework, not arithmetic.

### 200s are the system's heartbeat

```
Why are we totally excluding 200 from our analysis? They are the sign of something 
going exactly as expected, which directly correlates to the anatomy of the product 
we are analyzing. Aren't they the best indicator of what the system is?
```

Led to: 200-only latency baseline, degraded success concept (200 with extreme latency = functional failure), 200 rate as the availability mirror.

### SLO targets are business decisions

```
We are not looking at this decision holistically. We can't ascertain many aspects 
of this to drive a proper conclusion.
```

Reframed from prescribing a target (96.5%) to building a framework: bound the viable range with data, list 8 business inputs required for the final target, state the unknowns explicitly.

### LB weighting — conviction over diplomacy

```
I see no plausible reason to choose this weight distribution while the system ends 
up underutilized and triggers incidents. It's against all proper scaling principles 
and destructive.
```

Changed the recommendation from "consider reviewing" to a direct "equalize to 33/33/33" backed by six evidence points.

### Audience awareness

```
Imagine that what we are presenting is going to be read by someone who doesn't 
already know the answers to this question. This is another common pitfall — we make 
assumptions about the audience and blindly craft the work, while we should be making 
sure that our work can stand on its own and clearly communicate as per the rubric.
```

Eight integrity passes on the notebook. 50 issues found and fixed across data consistency, narrative flow, and raw data verification.
