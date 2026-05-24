---
description: Benchmark one or more perturbation models on a dataset. Produces a comparison table of metrics and a report.
args: <model1> [model2 ...] [--data path/to/data.h5ad] [--perturbations GENE1,GENE2]
section: Perturbation Workflows
topLevelCli: true
---
Benchmark perturbation models: $@

This is an execution request. Execute the workflow. Do not describe the protocol.

## Step 1: Parse arguments

From "$@":
- Models to benchmark (comma-separated or space-separated)
- Data path (default: most recent h5ad in workspace/data/)
- Target perturbations (default: all available in dataset)

Derive slug from model names and dataset: e.g., `gears-scgpt-norman2019`.

## Step 2: Write benchmark plan

Create `experiments/.plans/<slug>-benchmark.md`:

```markdown
# Benchmark Plan: <slug>

## Models
<list>

## Dataset
- Path: <data_path>
- N perturbations to evaluate: <count>
- Train/test split: simulation_single_combo

## Metrics (per model)
- Pearson r of mean expression (all genes)
- Top-20 DEG overlap
- R² on held-out perturbations
- Mean expression baseline (control)

## Task ledger
<per model: [ ] install, [ ] run, [ ] parse>
```

## Step 3: Check all models are installed

For each model:
```bash
conda env list | grep waddington-<model>
```

Install any missing models first using `model-manager` skill.

## Step 4: Run each model

For each model, spawn a separate `bioinfo-runner` subagent in parallel (if GPU allows) or sequentially:

```json
{
  "tasks": [
    {
      "agent": "bioinfo-runner",
      "task": "Read experiments/.plans/<slug>-benchmark.md. Run GEARS on <data_path> using the simulation split. Save metrics to experiments/results/<slug>/gears/metrics.json. Script: experiments/<slug>_gears.py.",
      "output": "run-log-gears.md"
    },
    {
      "agent": "bioinfo-runner",
      "task": "Read experiments/.plans/<slug>-benchmark.md. Run scGPT perturbation mode on <data_path>. Save metrics to experiments/results/<slug>/scgpt/metrics.json. Script: experiments/<slug>_scgpt.py.",
      "output": "run-log-scgpt.md"
    }
  ],
  "concurrency": 1,
  "failFast": false
}
```

## Step 5: Compute mean expression baseline

Always compute the floor:
```python
import scanpy as sc
import numpy as np
from scipy.stats import pearsonr

adata = sc.read_h5ad("<data_path>")
ctrl = adata[adata.obs["perturbation"] == "ctrl"]
ctrl_mean = np.array(ctrl.X.mean(axis=0)).flatten()

# Use control mean as prediction for all perturbations
baseline_pearson_values = []
for pert in test_perturbations:
    obs = adata[adata.obs["perturbation"] == pert]
    obs_mean = np.array(obs.X.mean(axis=0)).flatten()
    r, _ = pearsonr(ctrl_mean, obs_mean)
    baseline_pearson_values.append(r)

print(f"Mean expression baseline Pearson r: {np.mean(baseline_pearson_values):.3f}")
```

## Step 6: Compile results

Delegate to `data-analyst` subagent:

```json
{
  "agent": "data-analyst",
  "task": "Read all metrics files in experiments/results/<slug>/*/metrics.json. Build a comparison table: model vs. Pearson r (mean ± std), top-20 DEG overlap (mean ± std), R². Include the mean expression baseline. Rank models. Identify the best and worst predicted perturbations across models. Write the analysis to analysis-<slug>.md.",
  "output": "analysis-<slug>.md"
}
```

## Step 7: Deliver

Write `outputs/<slug>-benchmark.md`:

```markdown
# Benchmark: <models> on <dataset>

## Summary
<Winner and margin>

## Results Table

| Model | Pearson r (mean) | Top-20 DEG | R² |
|-------|-----------------|------------|-----|
| GEARS | ... | ... | ... |
| scGPT | ... | ... | ... |
| Mean expr. baseline | ... | ... | ... |

## Per-perturbation breakdown
<table of best/worst>

## Discussion
<interpretation, caveats>

## Reproducibility
Scripts: experiments/<slug>_*.py
Results: experiments/results/<slug>/
Seed: 42
```

Verify `outputs/<slug>-benchmark.md` exists. Final response: comparison table in chat + link to report.
