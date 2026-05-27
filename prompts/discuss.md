---
description: Load and discuss a single-cell biology paper from a URL (arXiv, bioRxiv, PubMed, DOI) or local file path. Extracts code links, datasets, and methods, then opens an interactive discussion.
args: <url_or_path>
section: Paper Workflows
topLevelCli: true
---
Load and discuss the paper at: $@

This is an execution request. Begin immediately by reading the paper.

## Step 1: Read the paper

Apply the `paper-read` skill to extract structured information from: $@

- If this is a URL: fetch using the appropriate method (alpha CLI for arXiv, fetch_content for bioRxiv/PubMed/DOI)
- If this is a local path: read the file directly (PDF via docparser, text/markdown via read)
- Extract: GitHub links, dataset accessions, methods summary, reported results

Save the extracted structured summary to `notes/<slug>-paper.md` where slug is derived from the paper title.

## Step 2: Present the paper

After reading, present a concise summary to the user:

```
## [Paper Title] ([Year])

**TL;DR:** [1–2 sentence summary of the biological question and key contribution]

**Method:** [model name and key idea in 1 sentence]

**Key result:** [primary benchmark metric vs. baseline]

**Code:** [GitHub URL or "not found"]
**Data:** [GEO accession(s) or "not specified"]
**Replication:** [Ready / Partial / Not reproducible]

Full notes saved to: notes/<slug>-paper.md
```

## Step 3: Open discussion

After presenting, ask:

> "What would you like to explore? For example:
> - Discuss the method design or experimental setup
> - Understand a specific figure or table
> - Compare this approach to [GEARS / scGPT / CPA / another model]
> - Replicate the experiments (I can run them automatically)
> - Download the data and run on your own dataset"

## Discussion modes

**Method deep-dive:**
When the user asks about the method, explain the architecture, loss function, and training procedure using the extracted content. Connect it to related work (GEARS, scGPT, etc.) that you know.

**Figure/table interpretation:**
When the user asks about a specific figure or result, locate the relevant passage in the paper, quote it directly, and interpret it in biological terms.

**Comparison to other models:**
When asked to compare, list similarities and differences in: model architecture, evaluation protocol, dataset, performance metrics. Flag if the comparison is not apples-to-apples.

**Replication request:**
When the user wants to replicate, run the `/replicate` workflow directly with the extracted GitHub URL, dataset accession, and methods summary — no need to re-read the paper.

## Saving to the knowledge base

After discussion, if the paper is about perturbation prediction and not already indexed,
offer to save it:

> "要把这篇论文加进知识库吗？我可以整理成 `workspace/papers/<slug>.md` 供以后检索。"

If the user agrees, create `workspace/papers/<slug>.md` with this structure:

```markdown
---
title: "<full title>"
authors: <surname list>
year: <year>
venue: <journal/conference>
doi: <DOI URL>
code: <GitHub URL or "not available">
model_id: <model_id from registry.json if applicable, else omit>
conda_env: <env name if applicable, else omit>
---

## Method
[Architecture, key components, training approach — 3–5 sentences]

## Datasets
[Table: dataset name, cell count, perturbation count, split strategy]

## Benchmark results (paper-reported)
[Table: metric, this model, baseline(s)]

## Architecture notes
[Inputs, outputs, strengths, weaknesses — bullet points]

## Comparison to other models
[How does this compare to GEARS, scGPT, CPA, etc.]

## Reproducibility
[Code availability, data availability, known issues]

## Local workspace (if applicable)
[workspace_dir, conda_env, benchmark file path]
```

Then add a row to `workspace/papers/README.md` index table.

Before creating, check `workspace/papers/README.md` — if the paper is already indexed,
skip creation and just point to the existing file.

## Integrity rules

- Quote the paper directly when interpreting results. Do not paraphrase in ways that change the meaning.
- If the paper claims something that seems surprising, note it explicitly and suggest verification.
- If a figure or table was not extractable (paywalled, image-only), say so explicitly.
- Never invent benchmark numbers. Use only what was extracted from the paper.
