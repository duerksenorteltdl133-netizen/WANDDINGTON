---
description: Design a rigorous evaluation benchmark for single-cell perturbation prediction models. Clarifies scope, selects metrics, specifies the evaluation protocol, and writes a runnable benchmark checklist.
args: <goal-description>
section: Perturbation Workflows
topLevelCli: true
---
Design a benchmark for: $@

This is a design request. Think carefully, then produce a concrete protocol document.

## Step 1 — Clarify scope

Infer from "$@" (or ask one question if genuinely ambiguous):

- **Models** — all supported backends, or a specific subset?
  Read `workspace/registry.json` for the full list.
- **Dataset** — Norman 2019 / Replogle 2022 / Adamson / sci-Plex / user-provided?
  Check `workspace/data/` for what is available locally.
- **Perturbation type** — single-gene knockouts, combinatorial, dose-response?
- **Biological focus** — DEG recovery, transcriptome-wide accuracy, or both?

State the inferred answers before proceeding.

## Step 2 — Metric selection

Recommend metrics based on the use case, using definitions from `workspace/evaluation/simple_eval.py`:

| Metric | What it measures | When to use |
|---|---|---|
| `pearson` | Overall transcriptome prediction accuracy (centroid-level) | Always include |
| `pearson_de` | Accuracy on top-20 DE genes per condition | Primary metric — headline number |
| `pearson_delta` | Accuracy on perturbation effect (Δ from ctrl) | Strong signal; requires control cells |
| `mse` / `mae` | Magnitude of prediction error | Secondary sanity check |
| `mse_de` | MSE on DE genes only | Focused diagnostic; requires control |

**Mandatory baselines** (always include both):
- `systema_matching_mean` — matching-mean control (non-trivial lower bound)
- `systema_nonctl_mean` — non-control mean (naive baseline)

**Recommended primary metric ranking:** `pearson_de` > `pearson_delta` > `pearson`

## Step 3 — Evaluation protocol

Produce a protocol block:

```
Dataset:        <name> (<N> cells, <M> perturbations)
Split strategy: hold out 20% of perturbations for test (simulation split)
                seed: 1, 2, 3  →  report mean ± std
Test set:       <N_test> perturbations (unseen during training)
Baselines:      systema_matching_mean (required), systema_nonctl_mean (required)
Primary metric: pearson_de   (evaluated via simple_eval.py with ctrl_mean)
Other metrics:  pearson, pearson_delta, mse, mse_de
Seeds:          3 independent runs per model
Stats test:     Wilcoxon signed-rank vs. systema_matching_mean (p < 0.05)
```

## Step 4 — Write the benchmark checklist

Derive a slug from the goal description (lowercase, hyphens, ≤5 words).

Create directory if needed:
```bash
mkdir -p /home/duanyu/Python/SKILL/waddington/experiments/.plans
```

Write `experiments/.plans/<slug>-benchmark.md`:

```markdown
# Benchmark: <goal>
Date: <today>
Dataset: <path>
Primary metric: pearson_de

## Models to run
- [ ] systema_matching_mean  ← required baseline
- [ ] systema_nonctl_mean    ← required baseline
- [ ] gears
- [ ] scgpt
- [ ] cpa
- [ ] txpert
- [ ] scouter
- [ ] state
<!-- add others from registry.json as needed -->

## Per-model tasks
- [ ] safe_smoke_run (verify no errors before committing to full run)
- [ ] full_run seed 1
- [ ] full_run seed 2
- [ ] full_run seed 3

## Results collection
- [ ] Run `/benchmark` to collect all metrics into a comparison table
- [ ] Compute mean ± std across seeds
- [ ] Run Wilcoxon signed-rank vs. systema_matching_mean
- [ ] Write benchmark report

## Notes
- Never compare models run on different datasets or splits.
- Always include ≥2 baseline runs before declaring any model "best".
- Report mean ± std, not a single run.
```

Report the path after writing.

## Step 5 — Offer to start

After writing the protocol:

> Ready to start? I'll run `systema_matching_mean` first to set the baseline, then proceed through the list.
> Use `/perturb --model systema_matching_mean` or `/benchmark systema_matching_mean systema_nonctl_mean` to begin.
