---
description: Downstream biological analysis of perturbation results. Describe a method or analysis you want (e.g. DEG overlap, pathway enrichment, gene ranking), and Waddington will generate and run a self-contained analysis script against an experiment's results.
args: <analysis-request> [--experiment <exp-dir>] [--model <model-id>]
section: Analysis
topLevelCli: true
---
Perform downstream analysis: $@

This is an execution request. Execute the analysis with tools. Do not describe the protocol.

## Step 1 — Find the experiment results

Parse "$@" for `--experiment <exp-dir>` or `--model <model-id>`.

If neither given, list `experiments/` and pick the most recent directory:
```bash
ls -t /home/duanyu/Python/SKILL/waddington/experiments/ | head -5
```

The results file to analyze is `experiments/<dir>/results/metrics.json`.
The dataset path is in `experiments/<dir>/config.json` under `"dataset_path"`.

## Step 2 — Understand the requested analysis

Derive from "$@":
- **Analysis name**: short snake_case id (e.g. `deg_overlap`, `pathway_enrichment`, `gene_ranking`)
- **Biological question**: what does this analysis answer?
- **Inputs required**: `metrics.json` only, `.h5ad` dataset, or both
- **Core algorithm**: what computation produces the output?
- **Output format**: ranked table, gene list, summary statistics, etc.

If the request references a paper or method name, search for its definition:
```
web_search: "<method name> single cell perturbation analysis algorithm"
```

Synthesize in ≤100 words before proceeding.

## Step 3 — Check for an existing analysis script

```bash
ls /home/duanyu/Python/SKILL/waddington/experiments/analyses/ 2>/dev/null
```

If a matching script exists (`<analysis_name>.py`), skip to Step 5.

## Step 4 — Generate the analysis script

Write a complete, runnable script to `experiments/analyses/<analysis_name>.py`.

Rules:
1. Read inputs from env vars:
   - `SC_RESULT_PATH` — path to `results/metrics.json` (required)
   - `SC_DATASET_PATH` — path to `.h5ad` file (optional)
2. All output to stdout as plain Markdown. No `plt.show()`. No file writes unless `SC_OUTPUT_DIR` is set.
3. Self-contained: all imports at the top, no relative imports.
4. Handle missing env vars: print a clear error and `sys.exit(1)`.
5. Only use packages available in standard scientific conda envs: `numpy`, `scipy`, `pandas`, `anndata`, `scanpy`, `sklearn`, `statsmodels`.

Template:
```python
# experiments/analyses/<analysis_name>.py
import json, os, sys
from pathlib import Path

SC_RESULT_PATH  = os.environ.get("SC_RESULT_PATH", "")
SC_DATASET_PATH = os.environ.get("SC_DATASET_PATH", "")

if not SC_RESULT_PATH or not Path(SC_RESULT_PATH).exists():
    print("Error: SC_RESULT_PATH not set or file not found.")
    sys.exit(1)

result = json.loads(Path(SC_RESULT_PATH).read_text())

# --- analysis logic here ---

print("# <Analysis Title>")
# ... Markdown output ...
```

Fill every placeholder with real logic — not pseudocode.

## Step 5 — Execute

```bash
mkdir -p /home/duanyu/Python/SKILL/waddington/experiments/analyses

SC_RESULT_PATH=<metrics.json path> \
SC_DATASET_PATH=<h5ad path or empty> \
conda run -n <conda_env from config.json, or sc_env> \
  python /home/duanyu/Python/SKILL/waddington/experiments/analyses/<analysis_name>.py
```

Print the output directly. If execution fails, show the traceback and fix the script.

## Step 6 — Interpret

After output is printed:
- Explain what the numbers mean biologically (2–3 sentences).
- Flag anything unexpected (e.g. suspiciously high/low values).
- Suggest one follow-up analysis if relevant.
