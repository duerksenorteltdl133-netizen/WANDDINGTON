---
description: Load and analyze a local AnnData (.h5ad) file. Describes cell types, perturbation labels, QC metrics, and expression summary.
args: <path/to/data.h5ad>
section: Data Analysis
topLevelCli: true
---
Analyze the AnnData file at: $@

This is an execution request. Begin immediately with tool calls. Do not describe the protocol.

## Step 1: Verify file

```bash
ls -lh "$@"
```

If file doesn't exist, tell the user the exact path was not found and ask to check the path.

## Step 2: Derive slug from filename

Extract the base name without extension: `<basename>`.

## Step 3: Quick inspection

Run immediately:

```bash
conda run -n waddington-scvi python - << 'PYEOF'
import scanpy as sc, warnings, json
warnings.filterwarnings("ignore")

adata = sc.read_h5ad("$@")
info = {
    "shape": list(adata.shape),
    "obs_columns": list(adata.obs.columns),
    "var_columns": list(adata.var.columns),
    "obsm_keys": list(adata.obsm.keys()),
    "uns_keys": list(adata.uns.keys()),
    "X_range": [float(adata.X.min()), float(adata.X.max())],
}
print(json.dumps(info, indent=2))

# Perturbation column detection
for col in ["perturbation","condition","gene","pert_gene","cond_name","guide_id","treatment"]:
    if col in adata.obs.columns:
        print(f"\n[PERTURBATION COLUMN]: '{col}'")
        print(adata.obs[col].value_counts().head(20).to_string())
        break

# Cell type detection
for col in ["cell_type","celltype","leiden","louvain","cluster","batch"]:
    if col in adata.obs.columns:
        print(f"\n[CELL TYPE COLUMN]: '{col}'")
        print(adata.obs[col].value_counts().to_string())
        break
PYEOF
```

## Step 4: Full analysis via data-analyst subagent

Spawn for detailed report:

```json
{
  "agent": "data-analyst",
  "task": "Inspect the AnnData file at $@. Follow the full inspection protocol: shape, obs/var columns, cell type distribution, perturbation label distribution, QC metrics (if available), expression matrix check (normalized? log-transformed?). Identify the perturbation column and list unique perturbations. Write a complete Dataset Summary with QC Status table to notes/<slug>-analysis.md.",
  "output": "notes/<slug>-analysis.md"
}
```

## Step 5: Deliver

Summarize in chat:
- File: `$@`
- Shape: N cells × M genes
- Perturbation column: `<col>` with K unique perturbations
- Cell types: (top 5 with counts)
- Preprocessing status: normalized / not normalized
- **Recommended next step**: which model to run, or what preprocessing is needed

Also mention the full analysis at `notes/<slug>-analysis.md`.
