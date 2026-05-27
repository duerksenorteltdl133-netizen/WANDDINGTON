# Model Workspace

This directory contains the source code for all perturbation prediction backends.
Each model has its own subdirectory with a `README.md` explaining imports, usage, and notes.

## Quick reference

| Directory | Model | Conda env | Example script | Benchmark Pearson |
|---|---|---|---|---|
| `gears/` | GEARS | `gears_env` | `example_run.py` | 0.970 |
| `scgpt/` | scGPT | `scgpt_env` | `example_run.py` | needs re-run |
| `cpa_workspace/` | CPA | `cpa_env` | — | needs re-run |
| `txpert/` | TxPert | `txpert_env` | `example_run.py` | 1.000* (smoke only) |
| `scouter/` | Scouter | `scouter_env` | `example_run.py` | 0.165 (abnormal) |
| `state/` | STATE | `state_env` | `example_run.py` | needs re-run |
| `systema/` | Systema baselines | `systema_env` | `example_run_all.sh` | 0.985–0.988 |
| `scpram_workspace/` | scPRAM | `scpram_env` | — | no results |
| `perturbgraph_workspace/` | PerturbGraph | `sc_env` | — | see benchmarks/ |

*TxPert Pearson=1.000 is from a tiny smoke run — do not trust without full benchmark.

## How to run an experiment

1. Read `workspace/registry.json` for the model's `conda_env` and `workspace_dir`
2. Read the model's `README.md` for key imports and usage pattern
3. Read `example_run.py` (if present) as a reference template
4. Generate a new `run.py` in `experiments/<date>_<model>_<dataset>/`
5. Set PYTHONPATH: `export PYTHONPATH=workspace/evaluation:$PYTHONPATH`
6. Execute: `conda run -n <conda_env> python run.py 2>&1 | tee results/run.log`
7. Output goes to `experiments/<dir>/results/metrics.json`

## Shared evaluation engine

`workspace/evaluation/simple_eval.py` — self-contained, no old-project dependencies.

```python
from simple_eval import evaluate_perturbation, save_metrics
metrics = evaluate_perturbation(predicted_means, observed_means, model="gears", dataset="norman2019", mode="safe_smoke_run")
save_metrics(metrics, "results/metrics.json")
```

Output keys: `primary_metrics.pearson`, `primary_metrics.pearson_de`, `primary_metrics.mse`, `primary_metrics.mae`, `primary_metrics.r2`.

## Reference benchmarks

Past run results in `workspace/benchmarks/*.json` — use for comparison.
