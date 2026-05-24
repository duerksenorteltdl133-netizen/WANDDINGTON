---
name: geo-download
description: Download single-cell datasets from GEO, Zenodo, Figshare, or direct URLs. Converts raw files to AnnData (.h5ad) format and saves to workspace/data/. Use when the user wants to download a dataset or when paper replication requires data.
---

# GEO Download

Download and convert single-cell datasets from public repositories to AnnData format.

## Supported sources

| Source | Accession format | Download method |
|--------|-----------------|-----------------|
| GEO | `GSExxxxxx` | GEO FTP or GEOparse |
| SRA | `SRPxxxxxx`, `SRRxxxxxx` | SRA toolkit (fasterq-dump) |
| Zenodo | `zenodo.org/record/xxxxxx` | Direct URL download |
| Figshare | `figshare.com/articles/xxxxxx` | Direct URL download |
| ArrayExpress | `E-MTAB-xxxxx` | BioStudies API |
| Direct URL | any `.h5ad`, `.h5`, `.loom`, `.csv.gz` URL | wget/curl |

## Step 1: Identify the dataset

Given an accession or URL, determine the source and fetch the file manifest:

**For GEO accessions:**
```bash
# Get file list from GEO
curl -s "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSExxxxxx&targ=self&form=text&view=quick" | grep "^!Series_supplementary_file"
```

Or use the GEO FTP:
```bash
# GEO FTP structure: ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSExxxxxx/suppl/
ACCESSION="GSExxxxxx"
PREFIX="${ACCESSION:0:-3}nnn"
curl -s "ftp://ftp.ncbi.nlm.nih.gov/geo/series/${PREFIX}/${ACCESSION}/suppl/" | grep -o '[^ ]*\.gz'
```

**For Zenodo:**
```bash
# Zenodo API
curl -s "https://zenodo.org/api/records/RECORD_ID" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for f in data['files']:
    print(f['links']['self'], f['key'], f['size'])
"
```

## Step 2: Download the files

```bash
DEST="workspace/data/<accession>/"
mkdir -p "$DEST"

# For GEO h5ad files (most common for processed single-cell data)
wget -P "$DEST" "ftp://ftp.ncbi.nlm.nih.gov/geo/series/<prefix>/<accession>/suppl/<filename>.h5ad.gz"
gunzip "$DEST/<filename>.h5ad.gz"

# For GEO raw count matrices (GSM files)
# Will need to reconstruct AnnData (see Step 3)
wget -P "$DEST" "ftp://ftp.ncbi.nlm.nih.gov/geo/series/<prefix>/<accession>/suppl/<filename>_matrix.mtx.gz"
wget -P "$DEST" "ftp://ftp.ncbi.nlm.nih.gov/geo/series/<prefix>/<accession>/suppl/<filename>_barcodes.tsv.gz"
wget -P "$DEST" "ftp://ftp.ncbi.nlm.nih.gov/geo/series/<prefix>/<accession>/suppl/<filename>_genes.tsv.gz"
```

Always show download progress and verify file size after download:
```bash
ls -lh "$DEST"
```

## Step 3: Convert to AnnData (.h5ad)

**If downloaded file is already .h5ad:**
```python
import scanpy as sc
adata = sc.read_h5ad("workspace/data/<accession>/<file>.h5ad")
print(adata)
# Done — save to canonical location
adata.write_h5ad("workspace/data/<accession>.h5ad")
```

**If raw 10x MTX format:**
```python
import scanpy as sc

adata = sc.read_10x_mtx(
    "workspace/data/<accession>/",
    var_names="gene_symbols",
    cache=False
)
adata.var_names_make_unique()
print(f"Loaded: {adata.shape}")
adata.write_h5ad("workspace/data/<accession>.h5ad")
```

**If CSV/TSV count matrix:**
```python
import pandas as pd
import scanpy as sc

counts = pd.read_csv("workspace/data/<accession>/counts.csv.gz", index_col=0)
adata = sc.AnnData(X=counts.T)  # genes × cells → cells × genes
adata.write_h5ad("workspace/data/<accession>.h5ad")
```

**If Seurat RDS (requires R):**
```bash
conda run -n waddington-scvi Rscript - << 'EOF'
library(Seurat)
library(SeuratDisk)
obj <- readRDS("workspace/data/<accession>/<file>.rds")
SaveH5Seurat(obj, filename="workspace/data/<accession>/<file>.h5seurat")
Convert("workspace/data/<accession>/<file>.h5seurat", dest="h5ad")
EOF
```

## Step 4: Add perturbation metadata

Many GEO datasets store perturbation labels in a separate metadata file. After loading:

```python
import scanpy as sc
import pandas as pd

adata = sc.read_h5ad("workspace/data/<accession>.h5ad")

# Look for metadata file
# Common patterns: metadata.csv, cell_metadata.tsv, obs.csv
meta = pd.read_csv("workspace/data/<accession>/metadata.csv", index_col=0)

# Align indices
common = adata.obs_names.intersection(meta.index)
adata = adata[common]
adata.obs = adata.obs.join(meta.loc[common])

print("Perturbation column:", adata.obs.get("perturbation", adata.obs.get("condition", "NOT FOUND")))
adata.write_h5ad("workspace/data/<accession>.h5ad")
```

## Step 5: Verify the download

Run a quick inspection after conversion:
```bash
conda run -n waddington-scvi python - << 'EOF'
import scanpy as sc
adata = sc.read_h5ad("workspace/data/<accession>.h5ad")
print(f"Shape: {adata.shape}")
print(f"obs: {list(adata.obs.columns)}")
# Check for perturbation column
for col in ["perturbation", "condition", "gene", "pert_gene"]:
    if col in adata.obs.columns:
        print(f"Perturbation column '{col}': {adata.obs[col].nunique()} unique values")
        break
EOF
```

## Known datasets and download commands

### Norman et al. 2019 (K562, 131 CRISPRa perturbations)
```bash
# GEARS downloads this automatically
conda run -n waddington-gears python -c "
from gears import PertData
pd = PertData('./workspace/data')
pd.load(data_name='norman')
"
# Or manual GEO: GSE133344
```

### Replogle et al. 2022 (K562 + RPE1, genome-scale)
```bash
# Available via Pertpy
conda run -n waddington-scvi python -c "
import pertpy as pt
adata = pt.dt.replogle_2022_rpe1()
adata.write_h5ad('workspace/data/replogle2022_rpe1.h5ad')
"
# Or manual GEO: GSE188836
```

### Adamson et al. 2016 (K562 ER stress)
```bash
# GEO: GSE90546
wget -P workspace/data/adamson2016/ \
  "ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE90nnn/GSE90546/suppl/GSE90546_RAW.tar.gz"
```

## After download

- Confirm the final h5ad path: `workspace/data/<accession>.h5ad`
- Run `/analyze workspace/data/<accession>.h5ad` to inspect
- Update `notes/<slug>-paper.md` with the dataset location
- The dataset is now ready for `/perturb`, `/benchmark`, or `/replicate`
