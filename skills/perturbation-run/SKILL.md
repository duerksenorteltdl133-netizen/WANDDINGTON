---
name: perturbation-run
description: Design and execute gene perturbation experiments using GEARS, scGPT, scVI, Pertpy, or CPA. Use when the user asks to run, replicate, or benchmark a perturbation experiment.
---

# Perturbation Run

End-to-end execution of gene perturbation prediction experiments.

## When to use

- User asks to run a perturbation experiment ("run GEARS on my data")
- User asks to replicate a paper's experiment ("replicate the GEARS results on Norman et al.")
- User asks to benchmark models ("compare GEARS and scGPT on my dataset")
- User asks to predict what happens when a gene is knocked out

## Step 1: Clarify before running

Before executing, confirm with the user:
1. **Model**: which model to use (GEARS / scGPT / scVI / Pertpy / CPA)?
2. **Dataset**: which `.h5ad` file or GEO dataset?
3. **Perturbations**: specific genes, or evaluate on all available?
4. **Evaluation**: which metrics (Pearson r, top-20 DEG overlap)?
5. **GPU**: available GPU? (`nvidia-smi`)

If any are unclear, ask before writing the plan.

## Step 2: Write the experiment plan

Create `experiments/.plans/<slug>.md`:

```markdown
# Experiment Plan: <slug>

## Objective
<What biological question this experiment addresses>

## Model
- Name: <model>
- Environment: waddington-<model>
- Config: <key hyperparameters>

## Dataset
- Path: workspace/data/<file>.h5ad
- Cell type: <cell_type>
- Perturbation column: <column_name>
- N perturbations: <count>
- Train/test split: <strategy>

## Evaluation
- Metrics: Pearson r of mean expression, top-20 DEG overlap
- Baselines: mean expression baseline, random baseline

## Output
- Script: experiments/<slug>_<model>.py
- Results: experiments/results/<slug>/

## Task ledger
- [ ] Check model installation
- [ ] Inspect dataset
- [ ] Write experiment script
- [ ] Run experiment
- [ ] Parse results
- [ ] Write summary
```

## Step 3: Check model and data

```bash
# Check model is installed
conda env list | grep waddington-<model>

# Check data file exists
ls -lh workspace/data/<file>.h5ad

# Quick data check
conda run -n waddington-scvi python -c "
import scanpy as sc
adata = sc.read_h5ad('workspace/data/<file>.h5ad')
print(adata)
"
```

If model is not installed: delegate to `model-manager` skill first.
If data is not available: help user download it or provide GEO download instructions.

## Step 4: Generate experiment script

Delegate to `bioinfo-runner` subagent to write and execute:

```json
{
  "agent": "bioinfo-runner",
  "task": "Read experiments/.plans/<slug>.md. Write a complete, reproducible experiment script to experiments/<slug>_<model>.py. The script must: load workspace/data/<file>.h5ad, train <model>, evaluate on held-out perturbations, compute Pearson r and top-20 DEG overlap, and save metrics to experiments/results/<slug>/metrics.json. Fix random seed to 42. After writing the script, execute it in the waddington-<model> conda environment and capture the output. Write a structured run log to run-log.md.",
  "output": "run-log.md"
}
```

## Step 5: Monitor and parse results

After the run completes:

```bash
# Check results exist
ls experiments/results/<slug>/

# Show metrics
cat experiments/results/<slug>/metrics.json

# Show last lines of log
tail -50 experiments/results/<slug>/run.log
```

## Model-specific experiment templates

### GEARS on Norman et al. 2019

```python
from gears import PertData, GEARS
import torch

# Load data
pert_data = PertData('./workspace/data')
pert_data.load(data_name='norman')
pert_data.prepare_split(split='simulation', seed=42)
pert_data.get_dataloader(batch_size=32, test_batch_size=128)

# Train
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
gears_model = GEARS(pert_data, device=device)
gears_model.model_initialize(hidden_size=64)
gears_model.train(epochs=20)

# Evaluate
result = gears_model.eval(pert_data.get_eval_targets())
# result contains: pearson_r, top20_deg_overlap per perturbation
```

### Pertpy workflow

```python
import pertpy as pt
import scanpy as sc

adata = sc.read_h5ad('workspace/data/<file>.h5ad')

# Differential expression
de = pt.tl.Augur()  # or use sc.tl.rank_genes_groups
```

## Evaluation metrics

Always compute and report:

| Metric | Description | How to compute |
|--------|-------------|----------------|
| Pearson r (mean) | Correlation of mean predicted vs. observed expression across all genes | `scipy.stats.pearsonr(pred_mean, obs_mean)` |
| Top-20 DEG overlap | Intersection size of top-20 upregulated genes in pred vs. obs | Set intersection |
| R² | Coefficient of determination on held-out perturbations | `sklearn.metrics.r2_score` |
| Mean expression baseline | Use mean expression of control cells as prediction | Floor comparison |

## After the run

Delegate interpretation to `data-analyst` subagent:

```json
{
  "agent": "data-analyst",
  "task": "Read experiments/results/<slug>/metrics.json and the run log. Compare results against published baselines (GEARS: Pearson r ≈ 0.81, mean baseline: ≈ 0.68). Identify the best and worst predicted perturbations. Write an interpretation to analysis.md.",
  "output": "analysis.md"
}
```

Then write the final report to `outputs/<slug>.md`.
