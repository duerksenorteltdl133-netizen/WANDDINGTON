---
description: Compare a single-cell perturbation paper's claims against its public codebase to find mismatches and reproducibility issues. Produces a structured audit report.
args: <paper-id-or-url> [--repo <github-url>]
section: Paper Workflows
topLevelCli: true
---
Audit paper and codebase for: $@

This is an execution request. Execute the audit with tools. Do not describe the protocol.

Derive a short slug from the paper title or ID (lowercase, hyphens, ≤5 words).

## Step 1 — Plan

Create `workspace/research/audits/<slug>-audit-plan.md` with:
```markdown
# Audit Plan: <paper title>
- Paper: <URL or ID>
- Repo: <to be found>
- Claims to audit: <to be filled>
- Checklist: [ ] fetch paper  [ ] find code  [ ] inspect code  [ ] compare  [ ] score
```

Continue immediately without waiting for confirmation.

## Step 2 — Fetch paper

Use web fetch or web search to retrieve the paper. Target: abstract, methods, architecture description, results table.

Extract and list:
- **Architectural claims** — model design, layer counts, key components
- **Hyperparameters** — learning rate, batch size, optimizer, epochs, loss function
- **Dataset & preprocessing** — which dataset, how cells/genes were filtered, normalization
- **Evaluation protocol** — train/test split strategy, metric definitions
- **Headline numbers** — from the main results table (pearson, pearson_de, etc.)

## Step 3 — Find the code repository

If `--repo` was given, use it directly.

Otherwise:
1. Check the paper abstract and author notes for a GitHub link.
2. Try web search: `"<paper title>" github site:github.com`
3. Check Papers With Code: `web_fetch https://paperswithcode.com/paper/<slug>`

If no public code found: note `Code: not publicly available`. Skip Steps 4–5. Proceed to Step 6 with reduced scope.

## Step 4 — Inspect the code

Fetch and read key files from the repository:
- Model definition file (e.g. `model.py`, `network.py`)
- Training script (e.g. `train.py`, `main.py`)
- Evaluation script or metrics file
- Config file (e.g. `config.yaml`, `args.py`, `hparams.py`)

For each paper claim extracted in Step 2, locate the corresponding code section.

```bash
# If the repo is cloned locally under workspace/models/<name>/
grep -rn "<key term>" /home/duanyu/Python/SKILL/waddington/workspace/models/<name>/
```

## Step 5 — Compare claims to code

For each claim, assign a status:
- ✅ **Consistent** — code matches the paper (cite file and line range)
- ⚠️ **Discrepancy** — code differs (describe exactly how: paper says X, code does Y)
- ❓ **Unverifiable** — relevant code section is missing or unclear
- ❌ **Missing** — paper claims X but no corresponding code exists

Common discrepancy types to check:
- Hyperparameters: paper value vs. actual default in config
- Architecture: stated layer count / dimension vs. code
- Loss function: stated formula vs. implementation
- Data split: random vs. stratified, seed value
- Metric: paper definition vs. how it is computed in evaluation code
- Regularization / normalization: described in paper but absent in code?

## Step 6 — Reproducibility scores

Rate each dimension 1–5:

| Dimension | Score | Rationale |
|---|---|---|
| Code availability | /5 | 5=full training code, 1=no code |
| Documentation | /5 | 5=README with full reproduce steps, 1=no docs |
| Hyperparameter completeness | /5 | 5=all params reported, 1=major params missing |
| Data availability | /5 | 5=public download link, 1=not available |
| Evaluation reproducibility | /5 | 5=metric code matches paper, 1=evaluation code absent |

**Overall reproducibility** = average, rounded to nearest 0.5.

## Step 7 — Write report

Save to `workspace/research/audits/<slug>-audit.md`:

```markdown
# Audit: <paper title>
Date: <today>

## Summary
<3 sentences: paper, repo, overall verdict>

## Claim comparison table
| Claim | Status | Evidence |
|---|---|---|
...

## Discrepancy details
<one paragraph per discrepancy>

## Reproducibility scores
<table from Step 6>

## Verdict
**Reproducible** / **Partially reproducible** / **Not reproducible**

## Sources
- Paper: <URL>
- Repository: <URL>
```

Create `workspace/research/audits/` if it doesn't exist. Verify the file was written. Report the path.

## Standards

- Never mark a claim "consistent" without reading the relevant code.
- Distinguish "paper doesn't say" from "code doesn't implement it".
- Be specific in discrepancies: quote the paper's exact claim and the code's actual behaviour.
- If repo is private or unavailable, write a blocked audit with a clear reason.
