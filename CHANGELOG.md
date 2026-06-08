# Lab Notebook

This file is the chronological lab notebook for Waddington research sessions.
Append entries after meaningful progress, failed approaches, verification results, or blockers.
Each entry should identify the active slug or objective and end with the next recommended step.

---

<!-- Entries go below, newest first -->

## 2026-06-01 — gpo-vae-paper-install
- Parsed local PDF from Zotero storage: `NH2PX6X3/Baek 等 - 2025 - GPO-VAE ... .pdf` (arXiv:2501.18973v1) and extracted the linked code repository `https://github.com/dmis-lab/GPO-VAE`.
- Cloned the repository into `workspace/models/gpo_vae` at commit `4e7c3ad`.
- Saved the environment specification as `workspace/envs/gpo_vae.yml` and verified the existing `gpo_vae_env` conda environment can import core dependencies (`torch`, `pytorch_lightning`, `scanpy`, `anndata`, `pyro`, `ot`) plus the local `gpo_vae` package from repo root.
- Added `gpo_vae` to `workspace/registry.json` for future model management.
- Next step: download the authors' released datasets from the README Google Drive links and write a `run_task.py` wrapper if we want benchmarked runs inside this workspace.

## 2026-06-01 — cebpe-gears
- Executed a GEARS `safe_smoke_run` for *CEBPE* on `workspace/data/norman2019/perturb_processed.h5ad` using seed 42.
- Created a local symlink for the requested Norman dataset path, wrote `experiments/cebpe-gears_gears.py`, and saved outputs under `experiments/results/cebpe-gears/`.
- Result summary: high genome-wide centroid correlation (`pearson=0.9702`) but poor DE-focused performance for *CEBPE* (`pearson_de=-0.2043`, top-20 DEG overlap `3/20`).
- Wrote final report to `outputs/cebpe-gears.md` with plots.
- Next step: run a heavier *CEBPE* holdout with more epochs / larger split to test whether DE recovery improves.
