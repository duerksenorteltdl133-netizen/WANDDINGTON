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
EXP_DIR=/home/duanyu/Python/SKILL/waddington/experiments/$(date +%Y%m%d)_<model>_<dataset>
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
import json, os, sys
from pathlib import Path

CONFIG = json.loads(Path("config.json").read_text())
WORKSPACE_ROOT = Path("/home/duanyu/Python/SKILL/waddington/workspace")
sys.path.insert(0, str(WORKSPACE_ROOT / "evaluation"))

# Model-specific imports and setup
...

# Run and collect predictions
predicted_means: dict[str, np.ndarray]  # {perturbation: mean_expr_vector}
observed_means: dict[str, np.ndarray]

# Standard evaluation (always use this)
from evaluation_engine import build_evaluation_record
metrics = build_evaluation_record(predicted_means, observed_means)

# Save
Path("results/metrics.json").write_text(json.dumps(metrics, indent=2))
```

## Step 4: Execute

```bash
cd $EXP_DIR
export PYTHONPATH=/home/duanyu/Python/SKILL/waddington/workspace/evaluation:$PYTHONPATH
conda run -n <conda_env> python run.py 2>&1 | tee results/run.log
```

## Step 5: Read results

Standard metrics.json schema (from evaluation_engine.py):
```json
{
  "primary_metrics": {
    "pearson": 0.82,
    "pearson_de": 0.71,
    "mse": 0.041,
    "mae": 0.15,
    "r2": 0.67
  },
  "native_metrics": { ... },
  "metadata": {
    "model": "gears",
    "dataset": "norman2019",
    "n_perturbations_evaluated": 105,
    "mode": "safe_smoke_run"
  }
}
```

## Reference benchmarks

Published baselines (Norman et al. 2019, from `workspace/benchmarks/`):

| Model | pearson | pearson_de |
|---|---|---|
| GEARS | ~0.82 | ~0.71 |
| scGPT | ~0.80 | ~0.68 |
| CPA | ~0.75 | ~0.62 |
| Mean baseline | ~0.68 | ~0.50 |

After run: compare against `workspace/benchmarks/<model>_metrics.json`.

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
