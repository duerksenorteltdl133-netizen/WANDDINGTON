---
title: "Predicting transcriptional outcomes of novel multigene perturbations with GEARS"
authors: Roohani, Huang, Leskovec
year: 2023
venue: Nature Biotechnology
doi: https://doi.org/10.1038/s41587-023-01905-6
code: https://github.com/snap-stanford/GEARS
model_id: gears
conda_env: gears_env
---

## Method

Graph-based model combining a **gene ontology knowledge graph** with a GNN encoder.
Learns gene-gene interaction structure from the GO graph rather than from perturbation
data alone, enabling generalization to unseen perturbation combinations.

Key components:
- GO graph embedding (pre-trained, frozen)
- Perturbation co-expression graph (learned from data)
- Two-graph GNN that merges both signals
- Predicts mean expression of perturbed cells directly (not delta from control)

## Datasets

| Dataset | Cells | Perturbations | Split |
|---|---|---|---|
| Norman 2019 (K562) | ~110k | 131 single + combo KOs | simulation split |
| Replogle 2022 (K562) | ~2.5M | ~10k single KOs | simulation split |

## Benchmark results (paper-reported, Norman 2019)

| Metric | GEARS | Mean baseline |
|---|---|---|
| pearson (all genes) | ~0.82 | ~0.68 |
| pearson_de (top-20 DEGs) | ~0.71 | ~0.50 |

Local smoke run (safe_smoke_run, Norman 2019): pearson=0.970, mse=0.0099
Note: smoke run numbers are inflated — not comparable to paper's full benchmark.

## Architecture notes

- Input: gene perturbation identity (one-hot or multi-hot for combos)
- Output: predicted mean expression vector (n_genes,)
- No cell-level modeling — predicts condition centroids directly
- Strength: combinatorial generalization without seeing all pairs
- Weakness: no single-cell resolution; requires GO graph download on first run

## Comparison to other models

- vs scGPT: GEARS uses a task-specific GNN; scGPT fine-tunes a foundation model.
  GEARS is faster to train and more interpretable; scGPT may generalize better
  across cell types with its pretrained representations.
- vs CPA: CPA uses a VAE with additive perturbation embeddings; GEARS uses graph
  structure. GEARS outperforms CPA on combinatorial perturbations.
- vs mean baseline (Systema): GEARS achieves +0.21 pearson_de over matching-mean.

## Reproducibility

- Code: publicly available, pip-installable
- Pretrained GO graph: downloaded automatically on first run (~cached to workspace/cache/gears/)
- Data: Norman 2019 available via GEARS data loader (`PertData.load(data_name='norman')`)
- Known issue: dataset mismatch errors if data is preprocessed with different gene sets

## Local workspace

- Source: `workspace/models/gears/`
- Conda env: `gears_env`
- Benchmark results: `workspace/benchmarks/gears_metrics.json`
