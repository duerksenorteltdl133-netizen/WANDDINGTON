---
name: model-manager
description: Install, update, list, and manage gene perturbation models (GEARS, scGPT, scVI, Pertpy, CPA, SAMS-VAE). Use when the user asks to install a model, check what's available, download weights, or switch between models.
---

# Model Manager

Manage the lifecycle of gene perturbation models in the local workspace.

## Supported models

| Model | Source | Conda env | Install method |
|-------|--------|-----------|----------------|
| **GEARS** | GitHub: snap-stanford/GEARS | `waddington-gears` | pip |
| **scGPT** | GitHub: bowang-lab/scGPT | `waddington-scgpt` | pip |
| **scVI** | PyPI: scvi-tools | `waddington-scvi` | pip |
| **Pertpy** | PyPI: pertpy | `waddington-scvi` (shared) | pip |
| **CPA** | GitHub: facebookresearch/CPA | `waddington-cpa` | pip |
| **SAMS-VAE** | GitHub: insitro/SAMS-VAE | `waddington-sams` | pip |

## Commands

### List installed models
```bash
conda env list | grep waddington
ls workspace/models/
```

### Install a model

**Step 1: Check if already installed**
```bash
conda env list | grep waddington-<model>
ls workspace/models/<model>
```

**Step 2: Create conda environment**
```bash
conda create -n waddington-<model> python=3.10 -y
```

**Step 3: Install the model**
See model-specific instructions below.

**Step 4: Verify installation**
```bash
conda run -n waddington-<model> python -c "import <package>; print('<model> OK')"
```

**Step 5: Write environment YAML**
```bash
conda run -n waddington-<model> conda env export > workspace/envs/<model>.yml
```

## Model-specific installation

### GEARS
```bash
conda run -n waddington-gears pip install torch torchvision torchaudio
conda run -n waddington-gears pip install torch-geometric
git clone https://github.com/snap-stanford/GEARS workspace/models/gears
conda run -n waddington-gears pip install -e workspace/models/gears
# Download pretrained weights
conda run -n waddington-gears python -c "
from gears import PertData, GEARS
pert_data = PertData('./workspace/data')
"
```

### scGPT
```bash
conda run -n waddington-scgpt pip install scgpt
# Download pretrained checkpoint (whole-human or specific)
mkdir -p workspace/models/scgpt/checkpoints
# Checkpoint download URL from scGPT GitHub releases
wget -P workspace/models/scgpt/checkpoints/ \
  https://github.com/bowang-lab/scGPT/releases/download/v0.2.1/whole_human.zip
conda run -n waddington-scgpt python -c "import scgpt; print('scGPT OK')"
```

### scVI + Pertpy (shared environment)
```bash
conda run -n waddington-scvi pip install scvi-tools pertpy scanpy anndata
conda run -n waddington-scvi python -c "import scvi, pertpy, scanpy; print('scVI+Pertpy OK')"
```

### CPA
```bash
git clone https://github.com/facebookresearch/CPA workspace/models/cpa
conda run -n waddington-cpa pip install -e workspace/models/cpa
conda run -n waddington-cpa python -c "import cpa; print('CPA OK')"
```

## Model info command

When user asks about a model, provide:
- GitHub URL and last commit date
- Paper citation (title, authors, venue, DOI)
- Supported perturbation types (single gene KO, combo, drug)
- Benchmark performance on Norman et al. 2019 (if published)
- Known limitations
- Whether pretrained weights are available

## Workspace layout

```
workspace/
├── models/
│   ├── gears/          # git clone of GEARS
│   ├── scgpt/          # pip-installed, + checkpoints/
│   ├── cpa/            # git clone of CPA
│   └── sams-vae/       # git clone of SAMS-VAE
├── envs/
│   ├── gears.yml       # exported conda environment
│   ├── scgpt.yml
│   ├── scvi.yml
│   └── cpa.yml
└── cache/
    ├── scgpt_whole_human/    # pretrained weights
    └── gears_norman2019/     # GEARS pretrained on Norman
```

## Error handling

- If pip install fails due to CUDA mismatch: suggest `conda install pytorch -c pytorch -c nvidia` with the correct CUDA version.
- If git clone fails: try the HTTPS URL directly and check if GitHub is accessible.
- If weight download fails: provide the manual download URL and save path.
- Always record failures in a `workspace/models/<model>/install.log` file.

## After installation

Confirm the installation by running a minimal smoke test:
- For GEARS: `from gears import GEARS`
- For scGPT: `import scgpt`
- For Pertpy: `import pertpy`

Then update `workspace/models/<model>/STATUS.md` with: install date, environment name, and verification status.
