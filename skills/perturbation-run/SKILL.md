---
name: perturbation-run
description: Run gene perturbation prediction experiments. Use when the user asks to run, replicate, or benchmark a model on a dataset.
---

# Perturbation Run

When a user asks to run a model on a dataset, Waddington generates a clean experiment
script and executes it in an isolated directory under `experiments/`.

## Directory layout

```
experiments/
└── <YYYYMMDD>_<model>_<dataset>/
    ├── config.json      ← experiment parameters
    ├── run.py           ← generated script (self-contained)
    └── results/
        ├── metrics.json ← standardized evaluation output
        └── run.log      ← stdout/stderr from the run

workspace/
├── data/                ← central dataset storage (shared across experiments)
├── evaluation/          ← evaluation_engine.py, dataparser.py
├── benchmarks/          ← reference metrics from past runs
└── registry.json        ← model backend info (conda env, install notes)
```

## Step 1: Confirm parameters

Before generating the script, confirm:
1. **Model** — which backend? (read `workspace/registry.json` for available options)
2. **Dataset** — path to `.h5ad` file, or ask to download
3. **Mode** — `safe_smoke_run` (fast, subset) or `full_benchmark` (full dataset)
4. **GPU** — check `nvidia-smi` first

## Step 2: Create experiment directory

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
EXP_DIR=$REPO_ROOT/experiments/$(date +%Y%m%d)_<model>_<dataset>
mkdir -p $EXP_DIR/results
```

Write `config.json`:
```json
{
  "model_id": "<model_id>",
  "dataset_path": "/path/to/data.h5ad",
  "mode": "safe_smoke_run",
  "seed": 42,
  "conda_env": "<conda_env from registry>",
  "created": "<timestamp>"
}
```

## Step 3: Generate run.py

Delegate to `bioinfo-runner` to write a self-contained `run.py`. Requirements:
- No hardcoded absolute paths except dataset and eval engine
- Load dataset from `config["dataset_path"]`
- Set `PYTHONPATH` to include `workspace/evaluation/` for the evaluation engine
- Save output to `results/metrics.json` with standard schema (see below)
- Save stdout+stderr to `results/run.log`

Template structure:
```python
import json, sys, numpy as np
from pathlib import Path

CONFIG = json.loads(Path("config.json").read_text())
# repo root = two levels up from experiments/<slug>/
REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT / "workspace"
sys.path.insert(0, str(WORKSPACE_ROOT / "evaluation"))

# Model-specific imports and setup
...

# Run and collect predictions
# Both dicts must share the same perturbation keys
predicted_means: dict[str, np.ndarray]  # {perturbation_name: mean_expr_vector (n_genes,)}
observed_means:  dict[str, np.ndarray]  # {perturbation_name: mean_expr_vector (n_genes,)}

# Standard evaluation — use simple_eval (no old-project dependencies)
from simple_eval import evaluate_perturbation, save_metrics
metrics = evaluate_perturbation(
    predicted_means,
    observed_means,
    model=CONFIG["model_id"],
    dataset=CONFIG.get("dataset", "unknown"),
    mode=CONFIG.get("mode", "unknown"),
)
save_metrics(metrics, "results/metrics.json")
```

## Step 4: Execute

```bash
cd $EXP_DIR
REPO_ROOT=$(git rev-parse --show-toplevel)
export PYTHONPATH=$REPO_ROOT/workspace/evaluation:$PYTHONPATH
conda run -n <conda_env> python run.py 2>&1 | tee results/run.log
```

## Step 5: Read and interpret results

### Output schema (`results/metrics.json`)

```json
{
  "primary_metrics": {
    "pearson":       0.82,
    "pearson_de":    0.71,
    "pearson_delta": 0.65,
    "mse":           0.041,
    "mse_de":        0.11,
    "mae":           0.15
  },
  "per_perturbation": {
    "GENE1+ctrl":    {"pearson": 0.91, "pearson_de": 0.85, "pearson_delta": 0.80, "mse": 0.01, "mse_de": 0.03, "mae": 0.08},
    "GENE2+GENE3":   {"pearson": 0.73, "pearson_de": 0.61, "pearson_delta": null, "mse": 0.06, "mse_de": null,  "mae": 0.19}
  },
  "metadata": {
    "model":                     "gears",
    "dataset":                   "norman2019",
    "n_perturbations_evaluated": 105,
    "n_de_genes":                20,
    "ctrl_available":            true,
    "mode":                      "safe_smoke_run"
  }
}
```

### Metric definitions

All metrics operate on **per-condition centroids** (mean expression vectors averaged over
cells), not individual cells. This matches the scGPT / GGE paper convention.

#### `pearson` — primary overall metric
```
For each test perturbation condition c:
    r_c = Pearson( pred_centroid_c, obs_centroid_c )   # over all n_genes
pearson = mean( r_c )  over all conditions
```
Interpretation: how well the predicted mean expression profile matches the true profile.
Range [-1, 1]; higher is better. Published benchmarks: GEARS ~0.82, scGPT ~0.80.

#### `pearson_de` — primary DE-gene metric (main benchmark number)
```
DE genes per condition c = top-20 genes by |obs_centroid_c − ctrl_mean|
    (deviation from control; falls back to top-20 by |obs_centroid_c| if no ctrl)

pearson_de_c = Pearson( pred_centroid_c[DE_c], obs_centroid_c[DE_c] )
pearson_de   = mean( pearson_de_c )  over all conditions
```
Interpretation: whether the model correctly captures the **direction and magnitude** of
the strongest transcriptional changes. This is the headline metric in the field.
Published benchmarks: GEARS ~0.71, scGPT ~0.68.

#### `pearson_delta` — delta (fold-change) metric (requires control)
```
delta_obs_c  = obs_centroid_c  − ctrl_mean      # deviation from unperturbed state
delta_pred_c = pred_centroid_c − ctrl_mean
pearson_delta_c = Pearson( delta_pred_c, delta_obs_c )
pearson_delta   = mean( pearson_delta_c )
```
Interpretation: how well the model captures the **perturbation effect** (not absolute
expression). Null when no control cells are available.

#### `mse` — centroid reconstruction error
```
mse_c = mean( (pred_centroid_c − obs_centroid_c)^2 )   # over all genes
mse   = mean( mse_c )  over all conditions
```
Lower is better. Sensitive to scale of expression values; compare within same dataset.

#### `mse_de` — MSE on DE genes (requires control)
```
mse_de_c = mean( (pred_centroid_c[DE_c] − obs_centroid_c[DE_c])^2 )
mse_de   = mean( mse_de_c )
```
More diagnostic than headline `mse`; focuses error measurement on the biologically
meaningful genes. Null when no control cells available.

#### `mae` — mean absolute error
```
mae_c = mean( |pred_centroid_c − obs_centroid_c| )
mae   = mean( mae_c )
```
Less sensitive to outliers than MSE. Lower is better.

### Null values
`pearson_delta`, `mse_de` are `null` when `ctrl_available: false` in metadata.
Individual per-perturbation values may also be `null` if a condition has constant
predicted or observed vectors (degenerate case).

### Passing control cells to the evaluator

When the dataset has identifiable control cells (typically `condition == "ctrl"`):
```python
import anndata as ad
import numpy as np

adata = ad.read_h5ad(CONFIG["dataset_path"])
ctrl_mask = adata.obs["condition"] == "ctrl"
ctrl_mean = np.array(adata[ctrl_mask].X.mean(axis=0)).flatten()

metrics = evaluate_perturbation(
    predicted_means, observed_means,
    ctrl_mean=ctrl_mean,
    model=CONFIG["model_id"], dataset="norman2019", mode=CONFIG["mode"],
)
```

## Reference benchmarks

### Local benchmark runs (Norman 2019, `workspace/benchmarks/`)

These are results from previous experiment runs. Most used `safe_smoke_run` mode
(a small subset of the data), so numbers are NOT directly comparable to published papers.

| Model | mode | pearson | pearson_de | mse | notes |
|---|---|---|---|---|---|
| GEARS | safe_smoke | 0.970 | — | 0.0099 | pearson_de not in native output |
| Systema (match-mean) | safe_smoke | 0.988 | — | 0.0039 | baseline (matching mean ctrl) |
| Systema (non-ctrl mean) | safe_smoke | 0.984 | — | 0.0051 | baseline (non-ctrl mean) |
| TxPert | safe_smoke | ~1.000 | — | 0.0051 | **artifact**: overfit on tiny smoke subset |
| Scouter | safe_smoke | 0.165 | 0.204 | 36.2 | **abnormal**: model may not have converged |
| STATE | safe_smoke | — | — | — | metrics not captured in run output |
| scGPT | full | — | — | — | run errored (dataset mismatch) |

### Published paper numbers (Norman 2019, full dataset)

Use these as the gold standard for comparison on a full benchmark run.

| Model | pearson | pearson_de | source |
|---|---|---|---|
| GEARS | ~0.82 | ~0.71 | Nature Biotech 2023 |
| scGPT | ~0.80 | ~0.68 | Nature Methods 2024 |
| CPA | ~0.75 | ~0.62 | Mol Sys Bio 2023 |
| Mean baseline | ~0.68 | ~0.50 | — |

After run: compare against `workspace/benchmarks/<model>_metrics.json` and the paper numbers above.

## Model-specific notes

### GEARS
- conda_env: `gears_env`
- Key imports: `from gears import PertData, GEARS`
- Data prep: requires `PertData` object; use `norman` as `data_name` for Norman 2019

### scGPT
- conda_env: `scgpt_env`
- Needs pretrained checkpoint; check `workspace/cache/scgpt/` first

### CPA
- conda_env: `cpa_env`
- Code in `workspace/models/cpa_workspace/`
- Key import: `import cpa`

### TxPert / Scouter / STATE
- Check `workspace/registry.json` for conda env
- These models are in the original project; reference their `run_task.py` as a template
  but write a fresh script under `experiments/`
