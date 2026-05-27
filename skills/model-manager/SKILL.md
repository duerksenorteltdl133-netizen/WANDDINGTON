---
name: model-manager
description: Install, update, list, and manage gene perturbation models. Use when the user asks to install a model, check what's available, run a model, or compare model results.
---

# Model Manager

Manage single-cell perturbation model backends for Waddington.

## Registry

```
workspace/registry.json          — master backend list (11 backends)
workspace/models/<name>/         — workspace directory per backend
workspace/evaluation/            — shared evaluation utilities (simple_eval.py, dataparser.py)
```

All paths in `registry.json` are **relative to the repository root** (the directory that contains `workspace/`).
Resolve them at runtime with:

```python
from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parent  # or locate via git
registry = json.loads((REPO_ROOT / "workspace" / "registry.json").read_text())
for backend in registry["backends"]:
    workspace_dir = REPO_ROOT / backend["workspace_dir"]   # e.g. workspace/models/gears
    readme        = REPO_ROOT / backend["readme"]
```

Or in bash (from repo root):
```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
WORKSPACE_DIR="$REPO_ROOT/$(jq -r '.backends[] | select(.model_id=="gears") | .workspace_dir' workspace/registry.json)"
```

## Registered Backends

| model_id | display_name | conda_env | has run_task | has results |
|---|---|---|---|---|
| gears | GEARS | gears_env | ✓ | ✓ |
| scgpt | scGPT | scgpt_env | ✓ | ✓ |
| cpa | CPA | cpa_env | ✓ | ✓ |
| txpert | TxPert | txpert_env | ✓ | ✓ |
| scouter | Scouter | scouter_env | ✓ | ✓ |
| state | STATE | state_env | ✓ | ✓ |
| systema_matching_mean | Systema (matching mean) | systema_env | ✓ | ✓ |
| systema_nonctl_mean | Systema (non-ctrl mean) | systema_env | ✓ | ✓ |
| scpram | scPRAM | scpram_env | ✓ | — |
| perturbgraph | PerturbGraph | sc_env | ✓ | ✓ |

Always read `workspace/registry.json` first to get exact paths and conda env names.

## Running a Backend

Every `run_task.py` was written for the old project and has two hardcoded dependencies:
1. `PROJECT_ROOT = Path("/home/duanyu/Python/Myproject/single_cell_agent")`
2. `from sc_agent.tools.evaluation_engine import ...`

Set PYTHONPATH to fix the import before running:

```bash
WADDINGTON_WS=/home/duanyu/Python/SKILL/waddington/workspace
export PYTHONPATH="$WADDINGTON_WS/evaluation:$PYTHONPATH"

cd $WADDINGTON_WS/models/<name>_workspace
conda run -n <conda_env> python run_task.py
```

For a different dataset, generate a new run script rather than modifying `run_task.py`.

## Reading Existing Results

```bash
cat workspace/models/<name>_workspace/results/<name>_metrics.json
```

Key fields in every metrics JSON:
- `primary_metrics.pearson` — mean Pearson r across all perturbations
- `primary_metrics.pearson_de` — Pearson r on top-20 DEGs
- `primary_metrics.mse` / `mae` / `r2`
- `native_metrics` — model-specific raw metrics

## Comparing Models

Read all available `results/*.json` files and produce a Markdown table sorted by `pearson_de` descending. Include: model_id, pearson, pearson_de, mse, r2.

## Installing a New Model

1. Clone repo to `workspace/models/<name>_workspace/`
2. Detect environment from `environment.yml` / `requirements.txt` / `pyproject.toml`
3. Create conda env: `conda create -n <env> python=3.10 -y`
4. Install: `conda run -n <env> pip install -e .`
5. Smoke test: `conda run -n <env> python -c "import <pkg>; print('OK')"`
6. Add entry to `workspace/registry.json`
7. Write `run_task.py` for the new backend (see existing ones as templates)
