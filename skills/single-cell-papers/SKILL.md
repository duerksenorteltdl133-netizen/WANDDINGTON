---
name: single-cell-papers
description: Search for single-cell biology and gene perturbation papers across bioRxiv, PubMed, and GEO. Use when the user asks to find papers, datasets, or tools related to scRNA-seq, gene perturbation, CRISPR screens, or perturbation modeling.
---

# Single-Cell Papers Search

Search bioRxiv, PubMed, GEO, and arXiv for single-cell biology and gene perturbation literature.

## When to use

- User asks to find papers about a perturbation model (GEARS, scGPT, scVI, CPA, etc.)
- User asks about the state of the art in perturbation prediction
- User wants datasets for a specific cell type or perturbation type
- User asks "what papers exist on X" in single-cell biology

## Search strategy

Always use at least three search angles:

**1. bioRxiv / PubMed (biology-first)**
```
web_search queries:
- "site:biorxiv.org <topic> single-cell"
- "site:ncbi.nlm.nih.gov/pubmed <topic> scRNA-seq"
- "<gene name> perturbation transcriptomics"
```

**2. arXiv / alphaXiv (methods-first)**
```
alpha search: "<topic> perturbation prediction single cell"
alpha search: "<model name> gene expression"
```

**3. GEO for datasets**
```
web_search: "site:ncbi.nlm.nih.gov/geo <cell type> CRISPR perturbation"
```

## Key databases and how to search them

| Source | Best for | Search method |
|--------|----------|---------------|
| bioRxiv | Latest preprints in biology | `web_search` with `site:biorxiv.org` |
| PubMed | Peer-reviewed biology | `web_search` with `site:pubmed.ncbi.nlm.nih.gov` |
| GEO | Raw datasets (h5ad, counts matrix) | `web_search` with `site:ncbi.nlm.nih.gov/geo` |
| arXiv/alphaXiv | ML methods for biology | `alpha search` CLI |
| Zenodo/Figshare | Processed datasets | `web_search` |

## Important datasets in this field

When searching for benchmarking datasets, check these first:
- **Norman et al. 2019** — K562 cells, 131 single/combo CRISPR perturbations (GEO: GSE133344)
- **Replogle et al. 2022** — K562 and RPE1, genome-scale Perturb-seq (GEO: GSE188836)
- **Adamson et al. 2016** — endoplasmic reticulum stress screen (GEO: GSE90546)
- **Dixit et al. 2016** — bone marrow differentiation CRISPR (GEO: GSE90063)

## Output format

Present results as a structured reading list:

```markdown
## Paper Search Results: <topic>

### Highly Relevant
1. **[Title]** — Author et al., Year
   - Venue: Nature Methods / bioRxiv / etc.
   - URL: <direct link>
   - Key contribution: <1 sentence>
   - Dataset: <GEO accession if available>
   - Code: <GitHub URL if available>

### Also Relevant
...

### Datasets Found
| Accession | Description | Cell type | N perturbations | N cells |
|-----------|-------------|-----------|-----------------|---------|
| GSE... | ... | ... | ... | ... |
```

Every entry must have a direct URL. No URL = not included.

## After search

- If the user asks to discuss a specific paper, read it using `alpha get_paper` or `fetch_content` on the full URL.
- If the user asks to download a dataset, use the `model-manager` skill or direct `wget`/`curl` to the GEO FTP.
- If the user asks to replicate a paper, pass to the `perturbation-run` skill.
