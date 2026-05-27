# Datasets

Data files are **not tracked by Git** (`.h5ad`, `.h5`, `.loom` are gitignored).

## Recommended layout

```
workspace/data/
├── norman2019/
│   └── perturb_processed.h5ad      # Norman et al. 2019 — K562, 131 perturbations
├── replogle2022/
│   └── replogle_k562_essential.h5ad # Replogle et al. 2022 — genome-wide screen
└── <your_dataset>/
    └── <file>.h5ad
```

## How to provide a dataset

**Option 1 — Point to any path at run time**
```
/perturb CEBPE --model gears --data /path/to/your/data.h5ad
```
Waddington accepts any absolute or relative path.

**Option 2 — Place it here (recommended for shared setups)**

Drop your `.h5ad` file into `workspace/data/<dataset_name>/`.
Experiments will reference it as `workspace/data/<dataset_name>/<file>.h5ad`,
which stays consistent across machines as long as the file is placed in the same subdirectory.

**Option 3 — Download automatically**
```
/replicate <paper_url>
```
Waddington will find the GEO accession from the paper and use the `geo-download` skill
to fetch the data into `workspace/data/<dataset_name>/`.

## Known datasets

| Dataset | Source | GEO | Perturbations | Cells |
|---|---|---|---|---|
| Norman 2019 | K562, CRISPR KO + combo | GSE133344 | 131 | ~110k |
| Replogle 2022 | K562 + RPE1, genome-wide | GSE188416 | ~10k | ~2.5M |
| Adamson 2016 | K562, CRISPRi | GSE90546 | 88 | ~65k |

## Notes

- All models in `registry.json` are benchmarked on **Norman 2019** by default.
- If you clone this repo on a new machine, re-download your datasets and place them
  in the same relative paths — no code changes needed.
- Large interim files (processed caches, embeddings) should go into
  `workspace/cache/<model_name>/`, which is also gitignored.
