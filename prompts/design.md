---
description: Design a gene perturbation experiment from a natural language description. Produces an experiment plan, suggests appropriate models and datasets, and optionally executes.
args: <experiment idea or biological question>
section: Perturbation Workflows
topLevelCli: true
---
Design a perturbation experiment for: $@

This is a design + optional execution request. Begin with a research pass, then produce a concrete experiment plan.

## Step 1: Clarify the biological question

Parse "$@" for:
- Target gene(s) or pathway
- Cell type (if specified)
- Perturbation type (KO / OE / drug / combinatorial)
- Goal (understand mechanism / predict response / validate model / replicate paper)

If ambiguous, ask ONE clarifying question before proceeding.

## Step 2: Literature search

Spawn `researcher` to find relevant prior work:

```json
{
  "agent": "researcher",
  "task": "Search bioRxiv, PubMed, and arXiv for papers on: $@. Focus on: (1) papers that studied the same gene(s) or pathway in single-cell perturbation experiments, (2) existing datasets (GEO accessions), (3) which computational models were used and their reported performance. Write findings to notes/<slug>-design-research.md.",
  "output": "notes/<slug>-design-research.md"
}
```

## Step 3: Produce experiment design

After literature search, write `experiments/.plans/<slug>-design.md`:

```markdown
# Experiment Design: <title>

## Biological Question
<What we want to learn from this experiment>

## Background
<Relevant prior work from literature search — citations only>

## Proposed Approach

### Option A: <simplest approach>
- Model: <model>
- Dataset: <existing dataset or new experiment>
- Expected runtime: <estimate>
- Pros: <why>
- Cons: <why not>

### Option B: <more comprehensive approach>
- Model: <model>
- Dataset: <dataset>
- ...

## Recommended Dataset
- Name: <dataset name>
- GEO accession: <GSExxxxxxx> (if existing)
- Why: <why this dataset fits the question>
- Preprocessing needed: <yes/no, what>

## Recommended Model
- Primary: <model> — because <reason>
- Alternative: <model> — if <condition>

## Evaluation Protocol
- Train/test split: <strategy>
- Metrics: Pearson r, top-20 DEG overlap
- Baseline: mean expression of control cells
- Held-out perturbations: <how selected>

## Estimated Compute
- GPU: <required/optional>
- RAM: ~<estimate> GB
- Runtime: ~<estimate> hours

## Next Steps
1. [ ] Download dataset (if needed)
2. [ ] Install model (if needed)
3. [ ] Run `/perturb <gene> --model <model> --data <path>`
   OR run `/benchmark <models> --data <path>`

## Open Questions
<What we don't know yet that the experiment might answer>
```

## Step 4: Present and offer to execute

Summarize the design in chat:
- Biological question
- Recommended approach (1-2 sentences)
- Recommended dataset and model
- Estimated runtime
- Key uncertainty to resolve

Ask: "Should I proceed with this experiment plan? I can run it now with `/perturb` or `/benchmark`, or you can adjust the design first."

Do not execute automatically — wait for confirmation before running the experiment.

## Step 5: If user confirms execution

Run the recommended workflow:
- Single gene: `perturb` prompt workflow
- Multiple models: `benchmark` prompt workflow

## Sources

Every dataset recommendation must include a GEO accession or DOI.
Every model recommendation must include a GitHub URL and paper citation.
Never recommend a model or dataset you haven't verified exists.
