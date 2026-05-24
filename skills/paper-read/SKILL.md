---
name: paper-read
description: Read and extract key information from a paper given a URL (arXiv, bioRxiv, PubMed, DOI) or local file path (PDF, HTML). Extracts GitHub links, GEO/dataset accessions, methods, and evaluation protocol. Use whenever the user shares a paper link or file path.
---

# Paper Read

Load a paper from a URL or local path, extract its content, and return structured information relevant to single-cell biology experiments.

## Supported input formats

| Input type | Examples | How to read |
|------------|----------|-------------|
| arXiv URL | `arxiv.org/abs/2306.12345` | `alpha get_paper <id>` |
| bioRxiv URL | `biorxiv.org/content/...` | `fetch_content <url>` (HTML version) |
| PubMed URL | `pubmed.ncbi.nlm.nih.gov/...` | `fetch_content <url>` |
| DOI | `doi.org/10.1038/...` | `fetch_content https://doi.org/<doi>` |
| Local PDF | `/path/to/paper.pdf` | `pi-docparser` |
| Local Markdown/HTML | `/path/to/paper.md` | `read <path>` |

## Step-by-step extraction protocol

### Step 1: Fetch the paper

**For arXiv URLs:**
```
Extract the arXiv ID (e.g., 2306.12345 from arxiv.org/abs/2306.12345)
Use: alpha get_paper 2306.12345
```

**For bioRxiv URLs:**
```
Prefer the HTML version: replace /pdf/ with /content/ in the URL
Use: fetch_content <html_url>
Also try: fetch_content <url>?view=full
```

**For DOI / PubMed / journal URLs:**
```
Use: fetch_content <url>
If paywalled, try: fetch_content https://www.ncbi.nlm.nih.gov/pmc/articles/PMC<id>/
```

**For local PDFs:**
```
Use the pi-docparser package to extract text from the PDF.
If docparser is unavailable, try: bash -c "pdftotext <path> -"
```

### Step 2: Extract structured information

After fetching the content, extract and organize:

#### 2a. Code and repository links

Search the full text for GitHub URLs using these patterns:
- `github.com/[username]/[repo-name]`
- `github.com/[username]/[repo-name]/tree/[branch]`
- "code available at", "implementation available", "source code"

For each GitHub URL found:
- Record the full URL
- Check if the repo is public: `fetch_content https://github.com/[username]/[repo-name]`
- Note the primary language and last updated date from the GitHub page
- Look for: `requirements.txt`, `environment.yml`, `setup.py`, `pyproject.toml`

#### 2b. Dataset accessions

Search for:
- GEO accessions: `GSE\d{5,8}`, `GSM\d{5,8}`, `GDS\d{4,6}`
- SRA accessions: `SRP\d{6,9}`, `SRR\d{6,9}`
- ArrayExpress: `E-MTAB-\d+`
- Zenodo: `zenodo.org/record/\d+`
- Figshare: `figshare.com/articles/\d+`
- PRJNA (BioProject): `PRJNA\d+`

For each accession found, note:
- Accession ID
- Description from paper context
- Cell type(s)
- Number of cells/samples (if stated)

#### 2c. Methods summary

Extract:
- **Model/Method name**: the proposed approach name
- **Architecture**: key design choices (graph NN, transformer, VAE, etc.)
- **Input**: what the model takes as input (gene expression matrix, graph, etc.)
- **Output**: what the model predicts (gene expression, perturbation response)
- **Preprocessing**: normalization, HVG selection, batch correction steps
- **Training details**: loss function, optimizer, learning rate, epochs, batch size
- **Evaluation protocol**: train/test split strategy, held-out perturbations

#### 2d. Key results

Extract reported benchmark numbers:
- Pearson correlation (r) of mean expression
- Top-K DEG overlap (K=20, 50)
- R² on held-out perturbations
- Comparison baselines used
- Dataset(s) used for evaluation

#### 2e. Dependencies and requirements

Look for:
- Python version requirements
- Key package dependencies (torch, scvi-tools, etc.)
- CUDA/GPU requirements
- Installation instructions (pip install, conda, from source)

### Step 3: Output structured summary

```markdown
## Paper: [Title]

**Authors:** [list]
**Venue:** [journal/conference/preprint]
**Year:** [year]
**URL:** [canonical URL]
**Local file:** [path if applicable]

---

### Code & Reproducibility
| Item | Value |
|------|-------|
| GitHub | [URL or "not found"] |
| Repo status | [public/private/404] |
| Last commit | [date if found] |
| License | [license if found] |
| Installation | [pip/conda/source] |
| Requirements file | [filename if found] |

### Datasets
| Accession | Source | Description | Cells | Cell type |
|-----------|--------|-------------|-------|-----------|
| GSExxxxxx | GEO | [context] | [N] | [type] |

### Method Summary
- **Task:** [perturbation prediction / cell type classification / etc.]
- **Input:** [description]
- **Output:** [description]
- **Architecture:** [key design]
- **Preprocessing:** [steps]
- **Training:** [key details]

### Evaluation Protocol
- **Benchmark dataset:** [dataset name + accession]
- **Split strategy:** [simulation_single_combo / random / etc.]
- **Metrics:** [list]
- **Baselines:** [list]

### Reported Results
| Model | Dataset | Metric | Value |
|-------|---------|--------|-------|
| [this model] | [dataset] | Pearson r | [value] |
| [baseline] | [dataset] | Pearson r | [value] |

### Installation Requirements
- Python: [version]
- Key packages: [list]
- GPU: [required/optional/not needed]
- Estimated disk: [size if known]

### Replication Readiness
- Code available: ✓ / ✗ / partial
- Data available: ✓ / ✗ / partial
- Preprocessing script: ✓ / ✗
- Evaluation script: ✓ / ✗
- **Overall:** Ready / Partial / Not reproducible
```

## After extraction

- If the user wants to **discuss** the paper: present the summary and answer questions using the extracted content.
- If the user wants to **replicate**: pass the structured summary to the `paper-to-experiment` skill.
- If the user wants to **install the code**: pass the GitHub URL to the `model-manager` skill's generic install flow.
- If the user wants the **dataset**: pass the GEO/Zenodo accession to the `geo-download` skill.

## Handling failures

- If the paper is paywalled: try PubMed Central (PMC) free full-text version.
- If PDF parsing fails: use the abstract + supplementary materials page.
- If no GitHub link is found: search GitHub directly for the paper title or model name.
- If no dataset accession is found: search GEO using the paper title and authors.
- Always record what was found vs. not found. Never fabricate links or accessions.
