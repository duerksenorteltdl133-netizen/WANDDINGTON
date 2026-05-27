# Paper Knowledge Base

Curated summaries of key single-cell perturbation prediction papers.
Each file is one paper. Agent reads these before going to the web.

Papers are added on demand — when a user explicitly asks, or after a
`/discuss` / `/replicate` / `/paper-audit` session produces new insight worth keeping.

## Index

| File | Model / Method | Year | Dataset | pearson_de | Code |
|---|---|---|---|---|---|
| [gears.md](gears.md) | GEARS | 2023 | Norman 2019 | ~0.71 | [snap-stanford/GEARS](https://github.com/snap-stanford/GEARS) |
| [scgpt.md](scgpt.md) | scGPT | 2024 | Norman 2019 | ~0.68 | [bowang-lab/scGPT](https://github.com/bowang-lab/scGPT) |

## How to add a paper

After reading a paper with `/discuss` or `/replicate`, ask:
> "把这篇论文加进知识库"

Waddington will create `workspace/papers/<slug>.md` and add a row to this index.

## Search tips (for agents)

```bash
# Find papers by model name or topic
grep -rl "combinatorial" workspace/papers/
grep -rl "pearson_de" workspace/papers/

# List all indexed papers
grep "^\|" workspace/papers/README.md | grep -v "^| File\|^|---"
```
