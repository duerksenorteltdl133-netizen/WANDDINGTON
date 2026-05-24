---
description: Predict the transcriptomic effect of knocking out or overexpressing one or more genes using a perturbation model.
args: <gene> [gene2] [--model gears|scgpt|cpa] [--data path/to/data.h5ad]
section: Perturbation Workflows
topLevelCli: true
---
Run a gene perturbation prediction for: $@

This is an execution request. Execute the workflow immediately. Do not describe the protocol.

## Step 1: Parse arguments

Extract from "$@":
- Target gene(s): one or more gene symbols (e.g., BRCA1, MAPK1+EGFR for combo)
- Model: default to GEARS if not specified
- Data: check `workspace/data/` for h5ad files if not specified

If no data is found and no path given, ask the user to provide an h5ad file or a GEO accession to download.

## Step 2: Derive slug

Create a slug from the gene name(s) and model: `<gene>-<model>` (lowercase, hyphens). Example: `mapk1-egfr-gears`.

## Step 3: Check prerequisites

```bash
conda env list | grep waddington-<model>
ls workspace/data/
```

If model not installed: run the model-manager skill to install it first.

## Step 4: Inspect data

Quick AnnData inspection using the `adata-workspace` skill to confirm:
- Perturbation column exists and contains the target gene(s)
- Data is preprocessed (normalized + log1p)

## Step 5: Execute

Delegate to `bioinfo-runner` subagent:

Write experiment plan to `experiments/.plans/<slug>.md`, then spawn:

```json
{
  "agent": "bioinfo-runner",
  "task": "Read experiments/.plans/<slug>.md. Write and execute an experiment script to predict the transcriptomic effect of <gene(s)> using <model> on the dataset at <data_path>. Save: experiments/<slug>_<model>.py, experiments/results/<slug>/metrics.json, experiments/results/<slug>/predictions.h5ad. Fix seed=42. Return a one-line status.",
  "output": "run-log.md",
  "clarify": false,
  "async": false
}
```

## Step 6: Visualize

After run completes:
1. Scatter plot: predicted vs. observed mean expression
2. Top 10 upregulated and downregulated genes in prediction
3. If observed data exists: compute Pearson r and top-20 DEG overlap

## Step 7: Deliver

Write `outputs/<slug>.md`:
- Perturbation: gene(s), model, dataset
- Key metrics (Pearson r vs. baseline)
- Top predicted DEGs (table)
- Embedded plots
- Caveats and next steps

Verify `outputs/<slug>.md` exists on disk before responding.
Final response: brief summary + link to the output file.
