---
name: adata-workspace
description: Load, inspect, and describe AnnData (.h5ad) files. Use when the user provides a local h5ad path or asks to explore a single-cell dataset. Runs the data-analyst subagent for detailed analysis.
---

# AnnData Workspace

Load and inspect single-cell datasets in AnnData (.h5ad) format.

## When to use

- User provides a file path ending in `.h5ad`, `.loom`, or `.h5`
- User asks "what's in this dataset", "how many cells", "what cell types", "what perturbations"
- User wants to understand a dataset before running a model on it
- User asks to preprocess or filter a dataset

## Step 1: Verify the file exists

```bash
ls -lh <path>
file <path>
```

If the file doesn't exist, ask the user to check the path. Do not proceed.

## Step 2: Quick inspection (without subagent)

For a quick look, run directly:

```bash
conda run -n waddington-scvi python - << 'EOF'
import scanpy as sc
import warnings
warnings.filterwarnings("ignore")

adata = sc.read_h5ad("<path>")
print(f"Shape: {adata.shape[0]:,} cells × {adata.shape[1]:,} genes")
print(f"\nobs columns: {list(adata.obs.columns)}")
print(f"var columns: {list(adata.var.columns)}")
print(f"obsm keys: {list(adata.obsm.keys())}")
print(f"\nX range: [{adata.X.min():.2f}, {adata.X.max():.2f}]")

# Detect perturbation column
for col in ["perturbation", "condition", "gene", "pert_gene", "cond_name", "guide_id"]:
    if col in adata.obs.columns:
        n = adata.obs[col].nunique()
        print(f"\nPerturbation column: '{col}' ({n} unique values)")
        print(adata.obs[col].value_counts().head(10).to_string())
        break

# Cell type column
for col in ["cell_type", "celltype", "leiden", "louvain", "cluster"]:
    if col in adata.obs.columns:
        print(f"\nCell type column: '{col}'")
        print(adata.obs[col].value_counts().to_string())
        break
EOF
```

## Step 3: Full analysis (via data-analyst subagent)

For detailed analysis, spawn the `data-analyst` subagent:

```json
{
  "agent": "data-analyst",
  "task": "Inspect the AnnData file at <path>. Run the full inspection protocol: shape, obs/var columns, cell type counts, perturbation label distribution, QC metrics, and expression matrix check. Write a complete Dataset Summary to <slug>-analysis.md.",
  "output": "<slug>-analysis.md"
}
```

## Common AnnData patterns in perturbation datasets

| Pattern | Typical column name | Example values |
|---------|---------------------|----------------|
| Perturbation gene | `perturbation`, `gene`, `pert_gene` | `BRCA1`, `ctrl`, `MAPK1+EGFR` |
| Control label | usually `ctrl`, `control`, `non-targeting` | varies |
| Cell type | `cell_type`, `leiden` | `K562`, `RPE1` |
| Batch | `batch`, `library_id` | `batch_1` |

## Preprocessing checks

Before running any model, verify:

```bash
conda run -n waddington-scvi python - << 'EOF'
import scanpy as sc
import numpy as np

adata = sc.read_h5ad("<path>")

print("Preprocessing status:")
print(f"  Normalized: {bool(adata.X.max() < 50)}")   # log-normalized max ~13
print(f"  Has raw: {'raw' in dir(adata) and adata.raw is not None}")
print(f"  Has UMAP: {'X_umap' in adata.obsm}")
print(f"  Has PCA: {'X_pca' in adata.obsm}")

if "n_genes_by_counts" in adata.obs.columns:
    print(f"  n_genes: {adata.obs['n_genes_by_counts'].describe().to_string()}")
EOF
```

## Saving a filtered version

If the user wants to subset or preprocess:

```python
import scanpy as sc

adata = sc.read_h5ad("<path>")

# Filter low-quality cells
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)

# Remove high-MT cells (if mt column exists)
if "pct_counts_mt" in adata.obs.columns:
    adata = adata[adata.obs["pct_counts_mt"] < 20]

# Normalize
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

adata.write_h5ad("workspace/data/<slug>_preprocessed.h5ad")
print(f"Saved: {adata.shape}")
```

## Output

After inspection, summarize:
1. File size and location
2. Shape (cells × genes)
3. Perturbation column name and unique perturbation count
4. Cell type distribution (if available)
5. Whether preprocessing looks complete
6. Recommended next step (run a model, preprocess first, etc.)
