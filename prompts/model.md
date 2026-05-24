---
description: Install, list, update, or get info about gene perturbation models (GEARS, scGPT, scVI, Pertpy, CPA, SAMS-VAE).
args: <install|list|info|update> [model_name]
section: Model Management
topLevelCli: true
---
Model management command: $@

This is an execution request. Begin immediately.

## Parse command

From "$@":
- Subcommand: install / list / info / update
- Model name (if provided): gears / scgpt / scvi / pertpy / cpa / sams-vae

---

## `list` — Show installed models

```bash
echo "=== Installed conda environments ==="
conda env list | grep waddington

echo ""
echo "=== Model directories ==="
ls -la workspace/models/ 2>/dev/null || echo "(workspace/models/ is empty)"

echo ""
echo "=== Environment YAML files ==="
ls workspace/envs/ 2>/dev/null || echo "(workspace/envs/ is empty)"
```

Present as a table:

| Model | Installed | Env | Notes |
|-------|-----------|-----|-------|
| GEARS | ✓ / ✗ | waddington-gears | ... |
| scGPT | ... | ... | ... |
| scVI+Pertpy | ... | waddington-scvi | ... |
| CPA | ... | waddington-cpa | ... |

---

## `install <model>` — Install a model

Run the `model-manager` skill for the specified model.

**Check first:**
```bash
conda env list | grep waddington-<model>
```

If already installed: report the status and skip.

If not installed: follow the model-specific installation steps from `model-manager` skill.

After installation, verify:
```bash
conda run -n waddington-<model> python -c "import <package>; print('<model> ready')"
```

Write `workspace/models/<model>/STATUS.md`:
```markdown
# <model> Status
- Installed: <date>
- Environment: waddington-<model>
- Verification: PASS
- Notes: <any issues or version pins>
```

---

## `info <model>` — Show model details

Present:

```markdown
## <Model Name>

- **Paper:** <title>, <authors>, <venue>, <year>
  - URL: <DOI or arXiv>
- **GitHub:** <URL> (last commit: check)
- **PyPI / conda:** <install command>
- **Perturbation types:** single KO / combo / drug / OE
- **Benchmark (Norman et al. 2019):**
  - Pearson r (mean expression): ~<value> (from paper)
  - Top-20 DEG overlap: ~<value>
- **Pretrained weights:** available / not available
  - Download: <URL if available>
- **Known limitations:**
  - <limitation 1>
  - <limitation 2>
- **Local status:** installed / not installed
```

Only report benchmark numbers that can be traced to the original paper. Mark as "not reported" if not found.

---

## `update <model>` — Update a model

```bash
# Pull latest code
cd workspace/models/<model> && git pull

# Reinstall in environment
conda run -n waddington-<model> pip install -e workspace/models/<model>

# Verify
conda run -n waddington-<model> python -c "import <package>; print('updated OK')"

# Update environment YAML
conda run -n waddington-<model> conda env export > workspace/envs/<model>.yml
```

Update `workspace/models/<model>/STATUS.md` with the new date and version.

---

## Supported models reference

| Model | GitHub | Paper | Env |
|-------|--------|-------|-----|
| GEARS | snap-stanford/GEARS | Roohani et al., Nature Biotechnology 2024 | waddington-gears |
| scGPT | bowang-lab/scGPT | Cui et al., Nature Methods 2024 | waddington-scgpt |
| scVI | scverse/scvi-tools | Lopez et al., Nature Methods 2018 | waddington-scvi |
| Pertpy | scverse/pertpy | Lotfollahi et al., 2023 | waddington-scvi |
| CPA | facebookresearch/CPA | Lotfollahi et al., Molecular Systems Biology 2023 | waddington-cpa |
| SAMS-VAE | insitro/SAMS-VAE | Bereket & Karaletsos, 2023 | waddington-sams |

For unknown model names, search bioRxiv and GitHub before reporting "not supported".
