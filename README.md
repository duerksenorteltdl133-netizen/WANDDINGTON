# Waddington

**Open-source AI agent for single-cell gene perturbation research.**

Named after Conrad Waddington (1905–1975), who introduced the epigenetic landscape — cells as balls rolling across a developmental hillscape. Perturbation experiments reshape that landscape.

---

## What it does

```
"find papers on GEARS and compare it to scGPT"
→ Queries PubMed (MeSH), Semantic Scholar citation graph, reads papers, produces cited comparison

"analyze my dataset at /data/norman2019.h5ad"
→ Inspects cell types, perturbation labels, QC metrics, gene coverage

"run GEARS on my dataset for the CEBPE knockout"
→ Sets up conda env, writes experiment script, executes, reports Pearson r vs benchmark

"compare GEARS and scGPT on my dataset"
→ Runs both models, produces a side-by-side metrics table

"replicate the GEARS paper"
→ Downloads Norman 2019 from GEO, installs model, runs full benchmark
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/perturb <gene>` | Predict transcriptomic effect of a gene knockout or overexpression |
| `/analyze <path.h5ad>` | Inspect and describe a single-cell dataset |
| `/benchmark` | Run one or more models and compare metrics |
| `/benchmark-design` | Design a rigorous benchmark from a biological question |
| `/replicate <paper>` | Reproduce a published perturbation model end-to-end |
| `/discuss <url\|path>` | Read and discuss a paper, save to knowledge base |
| `/paper-audit <url\|path>` | Audit reproducibility: data, code, metrics |
| `/downstream` | Post-experiment analysis of the most recent result |
| `/model install\|list\|info <name>` | Manage perturbation model installations |
| `/design <question>` | Design an experiment from a biological question |

Natural language works too — no slash commands required.

---

## Supported Models

| Model | Description | Paper |
|-------|-------------|-------|
| **GEARS** | GO-graph GNN for single/combo KO prediction | [Roohani et al., Nat. Biotech. 2023](https://doi.org/10.1038/s41587-023-01905-6) |
| **scGPT** | Foundation model (33M cells) fine-tuned for perturbation | [Cui et al., Nat. Methods 2024](https://doi.org/10.1038/s41592-024-02201-0) |
| **CPA** | Compositional VAE for drug/gene perturbations | [Lotfollahi et al., Mol. Syst. Biol. 2023](https://doi.org/10.15252/msb.202211517) |
| **TxPert** | Transcriptomic perturbation model | — |
| **Scouter** | Perturbation effect prediction | — |
| **STATE** | State-space perturbation model | — |
| **Systema** | Matching-mean and non-ctrl-mean baselines | — |
| **scPRAM** | Single-cell perturbation response model | — |
| **PerturbGraph** | Graph-based perturbation prediction | — |

---

## Subagents

Six specialized subagents dispatched automatically:

| Agent | Role |
|-------|------|
| **researcher** | PubMed E-utilities, GEO dataset discovery, Semantic Scholar citation graph, bioRxiv/arXiv |
| **reviewer** | Peer-level critique of methods, experimental design, and paper claims |
| **writer** | Structured scientific writing from research notes |
| **verifier** | Citation verification and dead-link detection |
| **bioinfo-runner** | Execute experiments, manage conda environments, parse results |
| **data-analyst** | Inspect AnnData objects, DEG analysis, statistical interpretation |

---

## Evaluation

All experiments produce standardized metrics via `workspace/evaluation/simple_eval.py`:

| Metric | Definition |
|--------|------------|
| `pearson` | Pearson r of predicted vs observed mean expression (all genes) |
| `pearson_de` | Pearson r on top-20 differentially expressed genes (by \|obs − ctrl\|) |
| `pearson_delta` | Pearson r of predicted vs observed expression change from control |
| `mse` | Mean squared error across all genes |
| `mae` | Mean absolute error across all genes |

Published baselines (Norman 2019, full benchmark):

| Model | pearson | pearson_de |
|-------|---------|------------|
| GEARS | ~0.82 | ~0.71 |
| scGPT | ~0.80 | ~0.68 |
| Mean baseline | ~0.68 | ~0.50 |

---

## Key Datasets

| Dataset | Cell type | Perturbations | GEO |
|---------|-----------|---------------|-----|
| Norman et al. 2019 | K562 | 131 single/combo CRISPRa | [GSE133344](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE133344) |
| Replogle et al. 2022 | K562, RPE1 | Genome-scale Perturb-seq | [GSE188416](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE188416) |
| Adamson et al. 2016 | K562 | ER stress CRISPR screen | [GSE90546](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE90546) |

---

## Workspace Layout

```
workspace/
├── models/          # Downloaded model source code
├── data/            # .h5ad datasets (not tracked by git)
├── envs/            # Conda environment YAML files per model
├── cache/           # Pretrained weight caches (not tracked)
├── evaluation/      # simple_eval.py — standardized metrics
├── benchmarks/      # Published benchmark reference numbers
└── papers/          # Structured paper summaries (accumulated on demand)

experiments/
├── <YYYYMMDD>_<model>_<dataset>/
│   ├── config.json  # Experiment parameters
│   ├── run.py       # Self-contained experiment script
│   └── results/
│       ├── metrics.json
│       └── run.log
├── analyses/        # Post-hoc analysis scripts
└── .plans/          # Benchmark design plans

notes/               # Scratch notes (not tracked)
```

---

## Setup

Built on the [Pi](https://github.com/earendil-works/pi-mono) agent runtime.

**Prerequisites:**
- conda or mamba available in PATH
- (Optional) CUDA-capable GPU for model training

**Clone and open:**

```bash
git clone https://github.com/Luiyun/Waddington waddington
cd waddington
npx @earendil-works/pi-coding-agent
```

**Sync agent configuration (if running a custom Pi installation):**

```bash
cp -r .waddington/agents/* ~/.waddington/agent/agents/
cp .waddington/SYSTEM.md ~/.waddington/SYSTEM.md
```

---

## Paper Knowledge Base

Papers are accumulated on demand in `workspace/papers/`. Currently indexed:

- [GEARS](workspace/papers/gears.md) — Roohani et al. 2023
- [scGPT](workspace/papers/scgpt.md) — Cui et al. 2024

Use `/discuss <url>` to read and add any new paper. Use `/paper-audit` to assess reproducibility.

---

## License

[MIT](LICENSE)
