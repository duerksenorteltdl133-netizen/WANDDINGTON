# Agents

`AGENTS.md` is the repo-level contract for agents working in this repository.

Subagent behavior lives in `.waddington/agents/*.md`. To change how a subagent behaves, edit the file there.

## Subagents

Waddington ships six research subagents:

- `researcher` — gather evidence across bioRxiv, PubMed, GEO, GitHub, and local artifacts
- `reviewer` — computational biology peer review with severity-graded feedback
- `writer` — structured scientific writing from research notes and experiment results
- `verifier` — inline citation verification and source URL checking
- `bioinfo-runner` — experiment execution, conda environment management, result parsing
- `data-analyst` — AnnData inspection, differential expression, result interpretation

## Output conventions

- Research outputs: `outputs/`
- Paper-style drafts: `papers/`
- Session notes: `notes/`
- Experiment scripts: `experiments/`
- Experiment results: `experiments/results/<slug>/`
- Experiment plans: `experiments/.plans/<slug>.md`
- Lab notebook: `CHANGELOG.md`

## File naming

Every workflow derives a short **slug** from the topic/gene/model (lowercase, hyphens, ≤5 words, e.g., `brca1-gears-k562`). All files in a run use that slug as prefix:

- Plan: `experiments/.plans/<slug>.md`
- Scripts: `experiments/<slug>_<model>.py`
- Results: `experiments/results/<slug>/`
- Research: `notes/<slug>-research.md`
- Analysis: `notes/<slug>-analysis.md`
- Final output: `outputs/<slug>.md`
- Provenance: `outputs/<slug>.provenance.md`

Never use generic names like `experiment.py`, `results.md`, `analysis.md`.

## Workspace

```
workspace/
├── models/     # Model code (git clones or pip installs)
├── data/       # h5ad datasets and preprocessed files
├── envs/       # conda environment YAML files per model
└── cache/      # pretrained weight caches
```

## Provenance and verification

- Every output from `/benchmark` and `/design` must include a `.provenance.md` sidecar.
- Never report benchmark numbers (Pearson r, DEG overlap) without tracing to a run result file or original paper.
- Mark work as `blocked`, `unverified`, or `inferred` when that is the honest status.

## Delegation rules

- The lead agent plans, delegates, synthesizes, and delivers.
- Use subagents when the work is meaningfully decomposable.
- Prefer file-based handoffs over dumping large results back into parent context.
- For long-running experiments, always use `bioinfo-runner` with `async: true`.
- `data-analyst` always reads from files — never pass large AnnData contents inline.
