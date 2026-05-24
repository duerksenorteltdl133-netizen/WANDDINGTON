# Waddington

**The open source AI agent for single-cell gene perturbation research.**

Named after Conrad Waddington (1905–1975), who introduced the epigenetic landscape — cells as balls rolling across a developmental hillscape. Perturbation experiments reshape that landscape.

---

## What it does

```
"find papers on GEARS and compare it to scGPT"
→ Searches bioRxiv/PubMed, reads the papers, produces a cited comparison report

"analyze my data at workspace/data/norman2019.h5ad"
→ Inspects cell types, perturbation labels, QC metrics, preprocessing status

"run GEARS on workspace/data/norman2019.h5ad for the MAPK1 knockout"
→ Installs GEARS (if needed), writes experiment script, runs it, reports Pearson r

"compare GEARS and scGPT on my dataset"
→ Benchmarks both models, produces a metrics comparison table

"design an experiment to study BRCA1 perturbation in K562 cells"
→ Searches literature, recommends dataset and model, writes experiment plan
```

---

## Workflows

| Command | What it does |
|---------|--------------|
| `/perturb <gene>` | Predict transcriptomic effect of a gene knockout or overexpression |
| `/analyze <path.h5ad>` | Load and describe a single-cell dataset |
| `/benchmark <model1> [model2]` | Compare models on a dataset |
| `/design <question>` | Design an experiment from a biological question |
| `/model install\|list\|info\|update <name>` | Manage perturbation models |

Or just talk naturally — no slash commands required.

---

## Agents

Six bundled research subagents, dispatched automatically:

| Agent | Role |
|-------|------|
| **researcher** | Gather evidence from bioRxiv, PubMed, GEO, GitHub |
| **reviewer** | Computational biology peer review |
| **writer** | Structured scientific writing from research notes |
| **verifier** | Citation verification and source URL checking |
| **bioinfo-runner** | Execute experiments, manage conda environments |
| **data-analyst** | Inspect AnnData objects, run DEG analysis, interpret results |

---

## Supported Models

| Model | Task | Paper |
|-------|------|-------|
| **GEARS** | Single/combo gene KO prediction | Roohani et al., Nat. Biotech. 2024 |
| **scGPT** | Multi-task single-cell foundation model | Cui et al., Nat. Methods 2024 |
| **scVI** | Variational inference, batch correction | Lopez et al., Nat. Methods 2018 |
| **Pertpy** | Perturbation analysis toolkit | scverse, 2023 |
| **CPA** | Drug/gene perturbation autoencoder | Lotfollahi et al., Mol. Syst. Biol. 2023 |
| **SAMS-VAE** | Mechanism-aware perturbation model | Bereket & Karaletsos, 2023 |

---

## Workspace layout

```
workspace/
├── models/     # Downloaded model code and weights
├── data/       # .h5ad datasets
├── envs/       # conda environment YAML files per model
└── cache/      # Pretrained weight caches

experiments/    # Runnable scripts and result logs
outputs/        # Final research reports
papers/         # Paper-style drafts
notes/          # Scratch notes and intermediate analysis
```

---

## Setup

Built on [Pi](https://github.com/badlogic/pi-mono) agent runtime and [Feynman](https://feynman.is) skill architecture.

**Prerequisites:**
- [Feynman](https://feynman.is) installed (`curl -fsSL https://feynman.is/install | bash`)
- conda or mamba available
- (Optional) CUDA-capable GPU for model training

**Install Waddington skills into Feynman:**

```bash
# Copy skills and prompts into your Feynman installation
cp -r skills/* ~/.feynman/agent/skills/
cp -r prompts/* ~/.feynman/agent/prompts/
cp -r .waddington/agents/* ~/.feynman/agent/agents/
cp .waddington/SYSTEM.md ~/.feynman/agent/SYSTEM.md
```

Or clone this repo as your working directory and open it in Feynman:

```bash
git clone <this-repo> waddington
cd waddington
feynman
```

---

## Key datasets

| Dataset | Cell type | Perturbations | GEO |
|---------|-----------|---------------|-----|
| Norman et al. 2019 | K562 | 131 single/combo CRISPRa | GSE133344 |
| Replogle et al. 2022 | K562, RPE1 | Genome-scale Perturb-seq | GSE188836 |
| Adamson et al. 2016 | K562 | ER stress screen | GSE90546 |
| Dixit et al. 2016 | Bone marrow | CRISPR differentiation | GSE90063 |

---

## Contributing

See [AGENTS.md](AGENTS.md) for the agent and output conventions.

Add new perturbation models by:
1. Adding an entry to `skills/model-manager/SKILL.md`
2. Creating a conda env template in `workspace/envs/<model>.yml`
3. Adding install instructions to `prompts/model.md`

---

[MIT License](LICENSE)
