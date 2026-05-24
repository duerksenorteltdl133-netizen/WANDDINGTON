---
description: Fully automatic paper replication pipeline. Given a paper URL or local path, finds the GitHub code, installs the environment, downloads the dataset, runs the experiment, and compares results to the paper's claims.
args: <paper_url_or_path> [--data path/to/your/data.h5ad] [--gpu] [--dry-run]
section: Paper Workflows
topLevelCli: true
---
Replicate the paper at: $@

This is an execution request. Begin immediately. Do not describe the protocol — execute it.

## Parse arguments

From "$@":
- Paper source: URL (arXiv/bioRxiv/DOI) or local file path
- `--data <path>`: use this dataset instead of the paper's dataset (optional)
- `--gpu`: require GPU for training (default: use if available)
- `--dry-run`: plan only, do not execute

Derive slug from paper title or URL slug: lowercase, hyphens, ≤5 words.
Example: `gears-2023-perturbation` or `scgpt-nature-methods`.

## Step 0: Write the replication plan

Create `experiments/.plans/<slug>-replicate.md` immediately:

```markdown
# Replication Plan: <slug>

## Source
- Paper: $@
- Slug: <slug>

## Task ledger
- [ ] Extract paper info (GitHub, dataset, methods)
- [ ] Clone repository
- [ ] Parse environment requirements
- [ ] Create conda environment
- [ ] Verify installation
- [ ] Download dataset
- [ ] Generate experiment script
- [ ] Run baseline script
- [ ] Run main experiment
- [ ] Parse results
- [ ] Compare to paper claims
- [ ] Write replication report

## Status: planning
```

## Step 1: Read the paper

Apply `paper-read` skill to $@ and extract:
- GitHub URL(s)
- Dataset accession(s)
- Method name and architecture
- Preprocessing protocol
- Training config (epochs, LR, batch size)
- Evaluation protocol and split strategy
- Reported metrics

Save to `notes/<slug>-paper.md`. Update the task ledger.

If user specified `--data`: skip dataset download, use `--data` path directly.

## Step 2: Set up code and environment

Apply the `paper-to-experiment` skill (Phase 2):
- Clone the GitHub repo to `workspace/models/`
- Detect environment file (environment.yml / requirements.txt / setup.py)
- Create conda environment: `waddington-<slug>`
- Install dependencies
- Verify imports

Update plan: mark code setup tasks complete or note failures.

If `--dry-run`: stop here. Show the plan and what would run.

## Step 3: Get the data

If no `--data` flag:
  Apply `geo-download` skill for each dataset accession found in Step 1.

If `--data` was specified:
  Apply `adata-workspace` skill to inspect the provided file.
  Note any domain differences from the paper's training data.

Update plan: mark data tasks complete.

## Step 4: Generate and run the experiment

Apply `paper-to-experiment` skill (Phases 4–5):
- Generate `experiments/<slug>_<model>.py` from paper's protocol + repo examples
- Generate `experiments/<slug>_baseline.py` (mean expression baseline)
- Spawn `bioinfo-runner` to execute both scripts

Monitor progress. Update plan with run status.

## Step 5: Compare and deliver

Apply `paper-to-experiment` skill (Phase 6):
- Read `experiments/results/<slug>/metrics.json`
- Compare to paper's reported numbers from `notes/<slug>-paper.md`
- Write `outputs/<slug>-replication.md` with the comparison table

Verify `outputs/<slug>-replication.md` exists on disk before responding.

## Final response

Present in chat:

```
## Replication: <Paper Title>

| Metric | Paper | Ours | Status |
|--------|-------|------|--------|
| Pearson r | X.XX | X.XX | ✓ / ⚠ / ✗ |
| Top-20 DEG | X | X | ... |
| Baseline | X.XX | X.XX | ... |

**Verdict:** [Replicated / Partially replicated / Failed]

Full report: outputs/<slug>-replication.md
Scripts: experiments/<slug>_<model>.py
Results: experiments/results/<slug>/
```

If any phase failed, summarize what failed and what was still accomplished.
