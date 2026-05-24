---
name: cell-visualization
description: Generate single-cell visualizations including UMAP plots, heatmaps, volcano plots, DEG summaries, and perturbation comparison charts. Use when the user asks to visualize data, results, or model predictions.
---

# Cell Visualization

Generate publication-quality visualizations for single-cell and perturbation data.

## When to use

- User asks for a UMAP plot, heatmap, or volcano plot
- User wants to visualize model predictions vs. observed expression
- User wants to compare perturbation conditions
- User asks to "show" or "plot" any aspect of the data or results

## Available visualization types

| Plot type | Best for | Tool |
|-----------|----------|------|
| UMAP | Cell type / perturbation clustering | scanpy |
| Heatmap | Gene expression across conditions | seaborn / scanpy |
| Volcano plot | Differential expression | matplotlib / pertpy |
| Scatter (pred vs. obs) | Model evaluation | matplotlib |
| Violin plot | Gene expression distribution | scanpy / seaborn |
| Bar chart | Metric comparison across models | pi-charts |
| Mermaid diagram | Data processing pipeline | pi-mermaid |

## Environment

Always run visualization code in the appropriate conda environment:
```bash
conda run -n waddington-scvi python <script_path>
```

## UMAP plot

```python
import scanpy as sc
import matplotlib.pyplot as plt

adata = sc.read_h5ad("workspace/data/<file>.h5ad")

# Compute UMAP if not already done
if "X_umap" not in adata.obsm:
    sc.pp.highly_variable_genes(adata, n_top_genes=2000)
    sc.pp.pca(adata)
    sc.pp.neighbors(adata)
    sc.tl.umap(adata)

# Color by perturbation
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
sc.pl.umap(adata, color="perturbation", ax=axes[0], show=False, title="By perturbation")
sc.pl.umap(adata, color="cell_type", ax=axes[1], show=False, title="By cell type")

plt.tight_layout()
plt.savefig("outputs/<slug>_umap.png", dpi=150, bbox_inches="tight")
print("Saved: outputs/<slug>_umap.png")
```

## Volcano plot (DEG)

```python
import scanpy as sc
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

adata = sc.read_h5ad("workspace/data/<file>.h5ad")

# Run DE
sc.tl.rank_genes_groups(
    adata, groupby="perturbation",
    groups=["<perturbation>"], reference="ctrl",
    method="wilcoxon"
)

# Extract results
result = sc.get.rank_genes_groups_df(adata, group="<perturbation>")
result["-log10_pval"] = -np.log10(result["pvals_adj"] + 1e-300)

fig, ax = plt.subplots(figsize=(8, 6))
colors = result["logfoldchanges"].apply(
    lambda x: "red" if x > 0.5 else ("blue" if x < -0.5 else "gray")
)
ax.scatter(result["logfoldchanges"], result["-log10_pval"], c=colors, alpha=0.5, s=10)
ax.axhline(-np.log10(0.05), color="black", linestyle="--", alpha=0.5)
ax.axvline(0.5, color="gray", linestyle="--", alpha=0.5)
ax.axvline(-0.5, color="gray", linestyle="--", alpha=0.5)
ax.set_xlabel("Log2 fold change")
ax.set_ylabel("-log10(adjusted p-value)")
ax.set_title(f"Volcano plot: <perturbation> vs ctrl")

# Label top genes
top_genes = result.nlargest(5, "-log10_pval")
for _, row in top_genes.iterrows():
    ax.annotate(row["names"], (row["logfoldchanges"], row["-log10_pval"]), fontsize=8)

plt.tight_layout()
plt.savefig("outputs/<slug>_volcano.png", dpi=150, bbox_inches="tight")
print("Saved: outputs/<slug>_volcano.png")
```

## Prediction vs. observation scatter plot

For evaluating model predictions:

```python
import json
import numpy as np
import matplotlib.pyplot as plt
import anndata as ad
from scipy.stats import pearsonr

# Load predictions and observations
pred = ad.read_h5ad("experiments/results/<slug>/predictions.h5ad")
obs = ad.read_h5ad("workspace/data/<file>.h5ad")

# Mean expression per perturbation
pred_mean = pred[pred.obs["perturbation"] == "<pert>"].X.mean(axis=0)
obs_mean = obs[obs.obs["perturbation"] == "<pert>"].X.mean(axis=0)

r, _ = pearsonr(pred_mean, obs_mean)

fig, ax = plt.subplots(figsize=(6, 6))
ax.scatter(obs_mean, pred_mean, alpha=0.3, s=5)
ax.set_xlabel("Observed mean expression")
ax.set_ylabel("Predicted mean expression")
ax.set_title(f"<model> on <perturbation>\nPearson r = {r:.3f}")

# Add diagonal
lims = [min(obs_mean.min(), pred_mean.min()),
        max(obs_mean.max(), pred_mean.max())]
ax.plot(lims, lims, "r--", alpha=0.5, label="y=x")
ax.legend()

plt.tight_layout()
plt.savefig("outputs/<slug>_pred_vs_obs.png", dpi=150, bbox_inches="tight")
```

## Heatmap of top DEGs across perturbations

```python
import scanpy as sc
import seaborn as sns
import matplotlib.pyplot as plt

adata = sc.read_h5ad("workspace/data/<file>.h5ad")

# Get top 20 DEGs for each perturbation
sc.tl.rank_genes_groups(adata, groupby="perturbation", reference="ctrl", method="wilcoxon")
top_genes = []
for group in adata.obs["perturbation"].unique()[:10]:
    if group == "ctrl":
        continue
    df = sc.get.rank_genes_groups_df(adata, group=group)
    top_genes.extend(df.head(5)["names"].tolist())
top_genes = list(dict.fromkeys(top_genes))[:50]  # unique, max 50

sc.pl.heatmap(
    adata,
    var_names=top_genes,
    groupby="perturbation",
    figsize=(16, 8),
    show=False,
    save=f"outputs/<slug>_heatmap.png"
)
```

## Model comparison bar chart (via pi-charts)

When comparing metrics across models, use the pi-charts package to generate an embeddable chart in the report.

## Output conventions

- Save all plots to `outputs/<slug>_<type>.png`
- Always print the save path so the parent agent can reference it
- Include the plot in the final report with a descriptive caption
- Caption format: `**Figure N.** <Description>. Data: <source file>. n=<cells>. Method: <brief>`

## After generating plots

Add plots to the report:
```markdown
![UMAP colored by perturbation](outputs/<slug>_umap.png)
**Figure 1.** UMAP of <n> cells colored by perturbation condition. 
Data: <file>.h5ad. Cell type: <cell_type>.
```

Preview the final report: `waddington preview outputs/<slug>.md`
