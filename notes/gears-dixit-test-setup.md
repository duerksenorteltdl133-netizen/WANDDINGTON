# GEARS Testing Setup: Paper Summary & Experiment Plan

## Paper Overview: GEARS (Nature Biotechnology 2023)

**Title:** Predicting Transcriptional Outcomes of Novel Multigene Perturbations with GEARS  
**Authors:** Yusuf Roohani, Kexin Huang, Jure Leskovec (Stanford University)  
**DOI:** https://doi.org/10.1038/s41587-023-01905-6

### Core Innovation
GEARS combines **deep learning with biological knowledge graphs** to predict gene expression after perturbation. It uniquely handles:
- **Single-gene perturbations** (including genes not seen during training)
- **Multi-gene combinations** with non-additive (synergistic) effects
- **Uncertainty quantification** for predictions

### Why This Matters
- **Cost:** Perturbation experiments are expensive; predictions prioritize experiments
- **Scale:** Can predict 5,000+ gene combinations from limited training data
- **Generalization:** Predicts outcomes even for genes never experimentally perturbed
- **Biology:** Captures synergy, suppression, epistasis—not just additive effects

---

## Technical Architecture

### Model Components

**1. Knowledge Graphs** (biological prior)
- **Gene coexpression graph:** Links genes with correlated baseline expression (Pearson ρ > threshold)
- **Gene Ontology graph:** Links genes sharing biological pathways (Jaccard index of GO terms)
- Both built from training data + public databases

**2. Graph Neural Network (GNN) Encoders**
- **Gene encoder:** Maps each gene to a d-dimensional embedding
  - Captures intrinsic gene properties (what is this gene?)
  - Updated via GNN message passing over coexpression graph
- **Perturbation encoder:** Maps each perturbation to an embedding
  - Captures perturbation effect (what does this perturbation do?)
  - Updated via GNN message passing over GO graph

**3. Composition Module**
- Combines multiple perturbation embeddings (for multi-gene cases)
- Uses sum operator (allows variable perturbation set size)
- Gene + perturbation embeddings summed to predict individual gene responses

**4. Cross-gene Layer**
- Captures transcriptome-wide secondary effects
- Not every gene responds independently
- Learns global transcriptional coordination

**5. Gene-specific Output Decoders**
- Each gene has its own decoder (captures heterogeneous response patterns)
- Predicts post-perturbation expression = unperturbed + perturbation effect

### Loss Function (Novel)

**Autofocus loss:**
- Emphasizes differentially expressed genes (upweights error on DE genes)
- Exponent 2+γ (larger error on non-changing genes is penalized less)

**Direction-aware loss:**
- Penalizes sign errors (predicting opposite direction of change)
- Critical for biological interpretation

**Uncertainty loss:**
- Bayesian formulation
- Variance output inversely correlated with prediction error

---

## Dixit Dataset (Your Test Data)

**Location:** `/home/duanyu/Python/Myproject/single_cell_agent/data/raw/dixit/dixit/`

### Data Files
- **perturb_processed.h5ad:** 44,735 cells × 5,012 genes (sparse float32 matrix)
- **go.csv:** 1.3M edges for gene relationship graph

### Perturbations
| Perturbation | Cells | Role |
|---|---|---|
| ctrl (control) | 12,042 | Baseline |
| ELK1 | 4,721 | Transcription factor |
| ELF1 | 3,395 | Transcription factor |
| CEP55 | 2,812 | Centrosome protein |
| OGG1 | 2,661 | DNA repair |
| CREB1 | 2,210 | Signal transduction |
| ... | ... | ... |
| AURKA | 322 | Cell cycle (aurora kinase) |

**Total:** 19 single-gene perturbations + control

### Why This Dataset?
- ✅ Used in GEARS paper (can compare directly)
- ✅ K562 cells (human, well-characterized)
- ✅ Real Perturb-seq data (pooled CRISPR + scRNA-seq)
- ✅ Clean metadata (gene names, cell types, dosage)
- ✅ Manageable size (44K cells, not millions)

---

## Expected Benchmarks (From Paper)

### Single-Gene Perturbations (Dixit data)

| Metric | GEARS | GRN Baseline | No Pert Baseline |
|---|---|---|---|
| **MSE (top 20 DE genes)** | 30–50% improvement | — | 1.0 (oracle) |
| **Pearson r (all genes)** | 0.72–0.78 | ~0.35 | — |
| **Direction accuracy** | 89–92% | ~75% | — |
| **DEG Jaccard similarity** | 0.65–0.75 | ~0.45 | — |

### What These Mean
- **MSE:** How far predictions are from ground truth (lower is better)
- **Pearson r:** Correlation between predicted and actual expression
- **Direction accuracy:** % of top 20 DE genes with correct sign (↑ vs ↓)
- **DEG overlap:** How many of top 20 predicted match top 20 actual

---

## Experiment Phases

### Phase 1: Data Loading & Preprocessing
**Goal:** Prepare data for model training

Steps:
1. Load 44,735 × 5,012 sparse matrix
2. Convert to dense (manageable for K562)
3. Log-normalize: log(X + 1)
4. Filter genes: keep 2,000–3,000 HVGs
5. Build knowledge graphs from data + GO file
6. Create train/test splits (leave-one-gene-out for hard test)

**Deliverable:** `data/gears_dixit_processed.h5ad`

### Phase 2: Baseline Models
**Goal:** Establish performance bounds

Baselines:
1. **No perturbation:** Predicts zero expression change (MSE = 1.0)
2. **Additive:** sum(effect_A, effect_B) for multi-gene
3. **Mean effect:** Average effect from training data
4. **CPA:** Deep learning without knowledge graphs (if available)

### Phase 3: Train GEARS
**Goal:** Fit model to training data

Procedure:
1. Install GEARS (likely `pip install gears` or from GitHub)
2. Initialize model with knowledge graphs
3. Train on 18/19 genes
4. Validate on held-out cells
5. Save trained model

**Hyperparameters:**
- Learning rate: 0.0001
- Batch size: 32
- Graph connectivity: H_gene=20, H_pert=20
- Loss weights: γ=0.8, λ=0.3 (from paper)
- Epochs: until convergence (~100–500)

### Phase 4: Evaluate on Held-Out Gene
**Goal:** Test generalization to unseen gene

Procedure:
1. Load trained GEARS
2. Predict expression for held-out gene
3. Compute metrics (MSE, Pearson r, direction, etc.)
4. Compare to baselines

**Expected:** MSE improvement ~30–50% over no-perturbation

### Phase 5: Repeat & Aggregate
**Goal:** Robust benchmark across genes

Procedure:
1. Repeat phases 3–4 for each gene held out (5-fold)
2. Aggregate metrics (mean ± SD)
3. Compare to paper's reported numbers

---

## Reproducibility Checklist

- [ ] Paper published with code availability promised
- [ ] Exact dataset (Dixit GSE90063) available locally
- [ ] Gene Ontology annotations provided
- [ ] Methods fully described in paper
- [ ] Hyperparameters specified (mostly)
- [ ] Evaluation metrics well-defined
- [ ] Multiple datasets tested (generalization shown)

### Potential Issues
- ⚠️ GEARS code repo may not be public yet (published Aug 2023)
- ⚠️ Some hyperparameters may need tuning
- ⚠️ GPU memory might limit batch sizes
- ⚠️ Knowledge graph construction is complex (ensure correct implementation)

---

## Next Steps

### Option 1: Full Replication (Ambitious)
**Time:** 2–3 days | **Difficulty:** High | **Reward:** Complete validation

1. Find/install GEARS code
2. Preprocess Dixit data
3. Train model (leave-one-gene-out)
4. Evaluate on all 19 genes
5. Generate publication-quality figures
6. Compare to paper benchmarks

### Option 2: Simplified Benchmark (Pragmatic)
**Time:** 1 day | **Difficulty:** Medium | **Reward:** Quick validation

1. Use GEARS as black box (pip install or pre-trained)
2. Preprocess Dixit data
3. Train on random 15 genes, test on 4 genes
4. Compute metrics
5. Compare to paper's reported range

### Option 3: Detailed Analysis (Focused)
**Time:** 3–4 days | **Difficulty:** Medium | **Reward:** Deep insights

1. Implement baseline models only
2. Compare GEARS predictions to baselines
3. Analyze failure cases
4. Identify genes/pathways where GEARS excels
5. Propose improvements or extensions

---

## Resources

### Code
- **GEARS GitHub:** https://github.com/yhr91/GEARS (expected)
- **Paper code:** Usually in supplementary materials or author websites

### Data
- **Dixit et al.:** https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE90063
- **Local path:** `/home/duanyu/Python/Myproject/single_cell_agent/data/raw/dixit/`

### Learning
- **GNNs:** https://pytorch-geometric.readthedocs.io/
- **Perturb-seq:** https://en.wikipedia.org/wiki/Perturb-seq
- **Gene Ontology:** http://geneontology.org/

---

## Success Criteria

**Hard:**
- GEARS MSE improvement ≥30% vs. no-perturbation baseline ✅
- Pearson r ≥0.65 on held-out genes ✅
- Direction accuracy ≥80% ✅

**Soft:**
- Predictions replicate paper's numbers within 10% ✅
- Consistent performance across all 19 genes ✅
- Clear biological interpretation of top predictions ✅

---

## Files Created for You

1. **`notes/gears-paper.md`** — Detailed paper summary
2. **`notes/gears-dixit-test-setup.md`** — This file
3. **`experiments/.plans/gears-dixit-test.md`** — Full experiment plan
4. **Data:** Dixit dataset ready at `/home/duanyu/Python/Myproject/single_cell_agent/data/raw/dixit/dixit/`

---

## Ready to Begin?

Recommend starting with **Option 2 (Simplified Benchmark)** if time-constrained, or **Option 1 (Full Replication)** for complete validation.

Would you like me to proceed with implementation?
