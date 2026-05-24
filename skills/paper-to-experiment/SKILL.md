---
name: paper-to-experiment
description: Full automatic pipeline from a paper to a running experiment. Given a paper URL or local path, automatically finds the GitHub code, installs the environment, downloads the dataset, generates an experiment script following the paper's protocol, runs it, and reports results vs. paper's claims. Use when the user wants to replicate or extend a paper.
---

# Paper to Experiment (Auto-Replication Pipeline)

Given a paper, automatically execute the full pipeline:

```
Paper URL / PDF
  → Extract: GitHub URL + dataset accession + methods + eval protocol
  → Clone repo → parse requirements → create conda env → install
  → Download dataset → convert to h5ad → verify
  → Generate experiment script (following paper's protocol exactly)
  → Execute experiment in background
  → Parse results → compare to paper's reported numbers
  → Write replication report
```

## When to use

- User says "replicate this paper", "run this", "verify the results", "test this model"
- User shares a paper and asks "can we try this on my data?"
- User wants to extend a paper's experiment to a new dataset or perturbation

## Phase 1: Extract information from paper

Apply the `paper-read` skill to extract:
- GitHub repository URL(s)
- Dataset accession(s) (GEO, Zenodo, etc.)
- Method/model name
- Preprocessing protocol
- Training configuration (epochs, learning rate, batch size, seed)
- Evaluation protocol (split strategy, metrics, baselines)
- Reported benchmark results

Save to `notes/<slug>-paper.md`.

If any critical information is missing:
- **No GitHub link:** search GitHub for the paper title / model name / first author
  ```
  web_search: "github.com <model_name> single cell perturbation"
  web_search: "github.com <first_author> <year> <model_name>"
  ```
- **No dataset:** search GEO using paper title and cell type
- **No training details:** look in supplementary materials or the GitHub repo README

## Phase 2: Set up the code

### 2a. Clone the repository

```bash
REPO_URL="<github_url>"
REPO_NAME="$(basename $REPO_URL .git)"
MODEL_DIR="workspace/models/$REPO_NAME"

if [ -d "$MODEL_DIR/.git" ]; then
  echo "Repo already exists, pulling latest..."
  git -C "$MODEL_DIR" pull
else
  git clone "$REPO_URL" "$MODEL_DIR"
fi

ls "$MODEL_DIR"
```

### 2b. Detect environment specification

Scan the repo for environment files (in priority order):

```bash
REPO="workspace/models/$REPO_NAME"
for f in \
  "$REPO/environment.yml" \
  "$REPO/environment.yaml" \
  "$REPO/requirements.txt" \
  "$REPO/setup.py" \
  "$REPO/pyproject.toml" \
  "$REPO/setup.cfg"; do
  if [ -f "$f" ]; then
    echo "Found: $f"
    cat "$f"
  fi
done
```

### 2c. Determine Python version and key dependencies

From the environment file, extract:
- Python version (prefer 3.10 if not specified)
- PyTorch version (critical for CUDA compatibility)
- Key packages: `torch`, `scvi-tools`, `scanpy`, `anndata`, etc.

Check local CUDA version:
```bash
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null || echo "No GPU found"
python3 -c "import torch; print('CUDA:', torch.version.cuda)" 2>/dev/null || echo "PyTorch not available globally"
```

### 2d. Create conda environment

Generate a safe environment name: `waddington-<repo_name_slug>` (max 30 chars, lowercase, hyphens).

**If environment.yml exists:**
```bash
# Edit the env name before creating
ENV_FILE="workspace/models/$REPO_NAME/environment.yml"
ENV_NAME="waddington-<slug>"
# Replace the name field
sed "s/^name:.*/name: $ENV_NAME/" "$ENV_FILE" > "workspace/envs/<slug>.yml"
conda env create -f "workspace/envs/<slug>.yml"
```

**If only requirements.txt:**
```bash
conda create -n waddington-<slug> python=3.10 -y
conda run -n waddington-<slug> pip install -r workspace/models/$REPO_NAME/requirements.txt
```

**If setup.py / pyproject.toml:**
```bash
conda create -n waddington-<slug> python=3.10 -y
conda run -n waddington-<slug> pip install -e workspace/models/$REPO_NAME/
```

**Always add base bio packages if missing:**
```bash
conda run -n waddington-<slug> pip install scanpy anndata numpy scipy pandas scikit-learn matplotlib seaborn 2>/dev/null || true
```

### 2e. Verify installation

```bash
conda run -n waddington-<slug> python - << 'EOF'
# Try to import the main package
import sys, importlib

# Detect main package from setup.py or __init__.py
packages_to_try = ["<detected_package_name>", "scanpy", "anndata", "torch"]
for pkg in packages_to_try:
    try:
        m = importlib.import_module(pkg)
        print(f"✓ {pkg} {getattr(m, '__version__', 'ok')}")
    except ImportError as e:
        print(f"✗ {pkg}: {e}")
EOF
```

If any critical import fails, try alternative install methods before reporting failure.

### 2f. Record installation

Write `workspace/models/<repo_name>/STATUS.md`:
```markdown
# <Model Name> — Installation Status

- **Source:** <github_url>
- **Installed:** <date>
- **Conda env:** waddington-<slug>
- **Environment file:** workspace/envs/<slug>.yml
- **Python:** <version>
- **PyTorch:** <version> (CUDA: <version>)
- **Verification:** PASS / PARTIAL / FAIL
- **Notes:** <any issues>
```

## Phase 3: Get the data

### 3a. Use the dataset from the paper

Apply the `geo-download` skill for each accession found in Phase 1:
- Download raw files
- Convert to h5ad
- Verify perturbation labels match what the paper describes

### 3b. If user provides their own dataset

```bash
ls workspace/data/*.h5ad
```

Apply the `adata-workspace` skill to verify:
- Perturbation column exists
- Cell type matches the model's training domain
- Expression matrix is normalized (or note if raw counts are needed)

Flag any domain mismatch: e.g., "GEARS was trained on K562 cells — applying to a different cell type may reduce accuracy."

## Phase 4: Generate experiment script

This is the most critical step. The script must follow the paper's protocol exactly.

### 4a. Study the repo's example scripts

```bash
find workspace/models/<repo>/ -name "*.py" | xargs grep -l "train\|eval\|main" | head -10
ls workspace/models/<repo>/examples/ 2>/dev/null
ls workspace/models/<repo>/tutorials/ 2>/dev/null
cat workspace/models/<repo>/README.md
```

Read the most relevant example script and use it as a template.

### 4b. Generate the experiment script

Write `experiments/<slug>_<model>.py` following this structure:

```python
#!/usr/bin/env python
"""
Replication experiment: <Paper Title>
Source: <GitHub URL>
Paper: <URL>
Dataset: <GEO accession> → workspace/data/<file>.h5ad
Perturbations: <list or 'all available'>
Eval protocol: <from paper>
Seed: 42

Generated by Waddington from paper extraction.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch

# ── reproducibility ──────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

# ── paths ────────────────────────────────────────────────────────────────────
WORKSPACE = Path("workspace")
MODEL_DIR = WORKSPACE / "models" / "<repo_name>"
DATA_PATH = WORKSPACE / "data" / "<dataset>.h5ad"
OUT_DIR   = Path("experiments/results/<slug>")
OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(MODEL_DIR))

# ── load data ────────────────────────────────────────────────────────────────
# [Adapted from paper's preprocessing protocol]
import scanpy as sc
adata = sc.read_h5ad(DATA_PATH)

# Preprocessing (match paper exactly)
# <INSERT: normalization, HVG selection, etc. from paper>

# Train/test split (match paper's evaluation protocol)
# <INSERT: split strategy from paper>

# ── model ─────────────────────────────────────────────────────────────────────
# <INSERT: model initialization, training, evaluation from repo examples>

# ── evaluate ─────────────────────────────────────────────────────────────────
from scipy.stats import pearsonr
import numpy as np

def pearson_r_mean(pred, obs):
    """Pearson r of mean expression across all genes."""
    pred_mean = np.array(pred.mean(0)).flatten()
    obs_mean  = np.array(obs.mean(0)).flatten()
    r, _ = pearsonr(pred_mean, obs_mean)
    return float(r)

def top_k_deg_overlap(pred, obs, k=20):
    """Intersection of top-k upregulated genes in pred vs. obs."""
    pred_top = set(np.argsort(pred.mean(0))[-k:].tolist())
    obs_top  = set(np.argsort(obs.mean(0))[-k:].tolist())
    return len(pred_top & obs_top)

# ── save results ──────────────────────────────────────────────────────────────
metrics = {
    "model": "<model_name>",
    "paper": "<paper_url>",
    "dataset": str(DATA_PATH),
    "seed": SEED,
    "n_perturbations_evaluated": 0,  # fill in
    "pearson_r_mean": 0.0,           # fill in
    "top20_deg_overlap": 0.0,        # fill in
    "paper_reported_pearson_r": "<value_from_paper>",
    "delta_from_paper": 0.0,         # fill in after computing
}
(OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
```

The placeholders `<INSERT: ...>` must be filled from the actual paper/repo code — never leave them empty. If a protocol detail is unclear, add a `# NOTE: assumed from paper context` comment and make a reasonable choice.

### 4c. Baseline script

Always also generate `experiments/<slug>_baseline.py`:
- Predict the mean expression of control cells for every perturbation
- Compute the same metrics as the main model
- This gives the floor comparison

## Phase 5: Run the experiment

Delegate to `bioinfo-runner` subagent:

```json
{
  "agent": "bioinfo-runner",
  "task": "Read experiments/.plans/<slug>-replicate.md. Execute experiments/<slug>_<model>.py in the waddington-<slug> conda environment. Also execute experiments/<slug>_baseline.py in waddington-scvi. Capture all output. Write structured run log to run-log-<slug>.md including: exit code, key metrics from metrics.json, last 50 lines of stderr if failed.",
  "output": "run-log-<slug>.md",
  "clarify": false
}
```

## Phase 6: Compare and report

After run completes, write `outputs/<slug>-replication.md`:

```markdown
# Replication Report: <Paper Title>

**Paper:** <URL>
**Code:** <GitHub URL>
**Dataset:** <accession> → workspace/data/<file>.h5ad
**Date:** <date>
**Seed:** 42

## Results vs. Paper Claims

| Metric | Paper Reports | Our Replication | Δ | Status |
|--------|--------------|-----------------|---|--------|
| Pearson r (mean expr.) | <paper_value> | <our_value> | <delta> | ✓ Match / ⚠ Gap / ✗ Diverge |
| Top-20 DEG overlap | <paper_value> | <our_value> | <delta> | ... |
| Mean expr. baseline | <paper_value or N/A> | <our_value> | <delta> | ... |

## Replication Verdict

- **Overall:** Replicated / Partially replicated / Failed
- **Key differences:** <list any discrepancies>
- **Possible causes:** <different CUDA version, different random seed behavior, etc.>

## Scripts

- Main experiment: `experiments/<slug>_<model>.py`
- Baseline: `experiments/<slug>_baseline.py`
- Run log: `run-log-<slug>.md`
- Results: `experiments/results/<slug>/`

## Extending to Your Data

To run this model on a different dataset:
```
/perturb <gene> --model <model_name> --data workspace/data/<your_file>.h5ad
```

Note: This model was trained/evaluated on <cell_type>. Performance on other cell types may differ.
```

## Failure handling

At each phase, if something fails:

1. **Repo not found:** Search GitHub for alternative repos. If none, report "code not available."
2. **Installation fails:** Try alternative package versions, skip optional dependencies, document what failed.
3. **Data unavailable:** Use the closest available benchmark dataset and note the substitution.
4. **Script generation incomplete:** Write the script with clearly marked TODOs rather than skipping it. Run what can run.
5. **Experiment crashes:** Capture the error, suggest a fix, and offer to retry.

Never report "replication complete" unless `experiments/results/<slug>/metrics.json` exists and was read. Always compare to paper's numbers if they were extracted.
