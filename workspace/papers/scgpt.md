---
title: "scGPT: toward building a foundation model for single-cell multi-omics using generative AI"
authors: Cui, Wang, Maan, Pang, Luo, Duan, Wang
year: 2024
venue: Nature Methods
doi: https://doi.org/10.1038/s41592-024-02201-0
code: https://github.com/bowang-lab/scGPT
model_id: scgpt
conda_env: scgpt_env
---

## Method

**Foundation model** (transformer) pretrained on 33M human single cells via generative
masked-gene modeling, then fine-tuned for perturbation prediction.

Key components:
- Gene expression tokenizer (bins continuous expression into discrete tokens)
- Transformer encoder with gene-level attention (not cell-level)
- Perturbation fine-tuning head predicts post-perturbation expression
- Pretrained checkpoint: `whole_human` (~200MB, from scGPT GitHub releases)

## Datasets

| Dataset | Used for | Notes |
|---|---|---|
| 33M cells (mixed) | Pretraining | CellXGene corpus |
| Norman 2019 (K562) | Fine-tuning + benchmark | 131 single + combo KOs |

## Benchmark results (paper-reported, Norman 2019)

| Metric | scGPT | GEARS |
|---|---|---|
| pearson (all genes) | ~0.80 | ~0.82 |
| pearson_de (top-20 DEGs) | ~0.68 | ~0.71 |

Local run: errored (dataset mismatch on full benchmark run — needs re-run).

## Architecture notes

- Input: gene tokens + perturbation token injected into sequence
- Output: predicted expression per gene after perturbation
- Requires pretrained checkpoint — cannot train from scratch easily
- Strength: cross-cell-type transfer; benefits from foundation model pretraining
- Weakness: slower training; checkpoint dependency; tokenization is gene-set sensitive

## Comparison to other models

- vs GEARS: scGPT uses a general foundation model approach; GEARS uses domain-specific
  GO graph structure. GEARS outperforms on perturbation-specific benchmarks but scGPT
  has broader applicability (annotation, integration, etc.).
- vs CPA: scGPT models gene interactions via attention; CPA assumes additive perturbation
  effects in latent space. scGPT generally outperforms CPA.

## Reproducibility

- Code: publicly available
- Pretrained checkpoint: available from GitHub releases (~200MB)
  Also check: `workspace/cache/scgpt/whole_human/` if previously downloaded
- Fine-tuning script: `workspace/models/scgpt/example_run.py`
- Known issue: dataset preprocessing must match the gene vocabulary of the checkpoint

## Local workspace

- Source: `workspace/models/scgpt/`
- Conda env: `scgpt_env`
- Checkpoint location: `workspace/cache/scgpt/whole_human/` (download separately)
- Benchmark results: `workspace/benchmarks/scgpt_metrics.json` (run errored — outdated)
