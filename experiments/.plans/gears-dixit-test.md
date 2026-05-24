# Experiment Plan: Test GEARS on Dixit Dataset

**Slug:** `gears-dixit-test`  
**Dataset:** Dixit et al. Perturb-seq (GSE90063)  
**Model:** GEARS (Graph-Enhanced Gene Activation and Repression Simulator)  
**Paper:** Roohani, Huang & Leskovec, Nature Biotechnology 2023  

---

## Dataset Summary

**File:** `/home/duanyu/Python/Myproject/single_cell_agent/data/raw/dixit/dixit/perturb_processed.h5ad`

- **Cells:** 44,735
- **Genes:** 5,012 (sparse expression matrix, float32)
- **Perturbations:** 19 single-gene + 1 control (20 conditions total)
- **Control cells:** 12,042
- **Perturbed cells:** 32,693

**Perturbation genes (19):**
ELK1, ELF1, CEP55, OGG1, CREB1, EGR1, CIT, YY1, NR2C2, GABPA, CENPE, E2F4, AURKC, IRF1, ECT2, AURKB, RACGAP1, TOR1AIP1, AURKA

**Gene Ontology file:**
- 1.3M edges (source → target gene with importance score)
- Can build knowledge graph for GEARS embedding

---

## Experimental Design

### Objective
Validate GEARS model performance on Dixit dataset and compare to:
1. Paper's reported benchmarks (MSE, Pearson r, DEG detection)
2. Baseline methods (no perturbation, additive)
3. Other deep learning approaches (CPA if available)

### Train-Test Split Strategy

**Option A: Leave-One-Out Gene (Conservative)**
- Train: Use all cells from 18 genes
- Test: Hold out 1 gene completely
- Repeat 5 times with different test genes
- Tests pure generalization to unseen genes

**Option B: Held-Out Cells from Training Genes (Paper Protocol)**
- Train: 80% of cells from all 19 genes
- Test: 20% held-out cells from same genes
- Measures performance on seen genes with unseen cells
- Easier task but validates core model

**Option C: Mixed (Recommended)**
- Phase 1: Leave-one-gene-out evaluation (harder)
- Phase 2: Cross-validation within genes (standard)
- Matches paper's evaluation protocol

### Preprocessing Pipeline

1. **Load data** → Filter sparse matrix to dense
2. **Log normalization** → log(X + 1)
3. **Gene filtering:**
   - Keep genes with >0 expression in ≥10 cells
   - Select ~2,000-3,000 HVGs (highly variable genes)
   - Ensures numerical stability
4. **Batch effects:** Check for and correct if present
5. **Knowledge graph construction:**
   - Pearson correlation from control cell baselines
   - GO graph from provided go.csv file
   - Top-K neighbors: H_gene=20, H_pert=20 (GEARS defaults)

### Evaluation Metrics

**Primary (from paper):**
1. **MSE on top 20 DE genes** (normalized to no-perturbation baseline)
2. **Pearson correlation** across all genes
3. **Direction accuracy** (sign agreement for top DE genes)

**Secondary:**
4. **MAE (Mean Absolute Error)** for per-gene predictions
5. **R² coefficient of determination**
6. **Jaccard similarity** of predicted vs. true top-20 DEG lists
7. **Spearman rank correlation** (robustness to outliers)

**Baseline comparisons:**
- **No perturbation:** Predict zero change (oracle = 1.0 MSE normalized)
- **Additive:** sum(effect_gene_A, effect_gene_B) for combinations
- **GRN method:** SCENIC + linear propagation (if time permits)

---

## Implementation Roadmap

### Phase 1: Setup & Data Preparation (Day 1)
- [ ] Load Dixit h5ad file
- [ ] Parse gene/cell metadata
- [ ] Construct knowledge graphs (coexpression + GO)
- [ ] Prepare training/test splits
- [ ] Save preprocessed data to `data/gears_dixit_processed.h5ad`

### Phase 2: GEARS Installation & Baseline Implementation (Day 1-2)
- [ ] Search for GEARS GitHub (likely at: https://github.com/yhr91/GEARS)
- [ ] Install via pip or from source
- [ ] Verify imports and GPU availability
- [ ] Implement baseline models (no-pert, additive)
- [ ] Create evaluation framework

### Phase 3: Model Training (Day 2-3)
- [ ] Train GEARS on Dixit (leave-one-gene-out or cross-validation)
- [ ] Tune hyperparameters if needed:
  - Learning rate, batch size
  - Knowledge graph connectivity (H_gene, H_pert)
  - Loss weights (autofocus γ, direction λ)
- [ ] Track training curves (loss, validation metrics)
- [ ] Save trained models to `models/gears_dixit_*.pt`

### Phase 4: Evaluation (Day 3-4)
- [ ] Run predictions on held-out test set
- [ ] Compute all metrics (MSE, Pearson, direction, DEG overlap)
- [ ] Compare GEARS vs. baselines + paper benchmarks
- [ ] Generate visualizations:
  - Scatter plots (predicted vs. true expression)
  - Boxplots (metric distributions)
  - Bar plots (DEG overlap)
- [ ] Save results to `experiments/results/gears-dixit-test/`

### Phase 5: Analysis & Reporting (Day 4-5)
- [ ] Write methods summary
- [ ] Generate results tables and figures
- [ ] Identify best/worst predictions
- [ ] Discuss discrepancies from paper
- [ ] Propose next steps (multi-gene predictions, cell-type specific)

---

## Expected Outputs

### Artifacts
```
experiments/
├── .plans/
│   └── gears-dixit-test.md                    [This file]
├── gears_dixit_train.py                       [Training script]
├── gears_dixit_eval.py                        [Evaluation script]
└── results/gears-dixit-test/
    ├── metrics.csv                            [Aggregate results]
    ├── predictions_per_gene.csv               [Gene-level predictions]
    ├── predictions_per_cell.csv               [Full prediction matrix]
    ├── figures/
    │   ├── predicted_vs_true.png              [Scatter plot]
    │   ├── metric_comparison.png              [Bar plot: GEARS vs baselines]
    │   ├── deg_overlap.png                    [Jaccard similarity heatmap]
    │   └── training_curves.png                [Loss over epochs]
    └── models/
        └── gears_dixit_fold*.pt               [Trained weights]
```

### Data Format

**metrics.csv:**
```
gene_holdout, mse_normalized, pearson_r, direction_acc, deg_jaccard, mae
ELK1, 0.45, 0.72, 0.89, 0.65, 0.123
...
```

**predictions_per_gene.csv:**
```
gene, n_cells, mse, r, direction_acc, top_degs_predicted, top_degs_true, overlap
ELK1, 4721, 0.42, 0.74, 0.91, "gene1,gene2,...", "gene1,gene3,...", 15/20
```

---

## Success Criteria

### Hard Targets (from paper)
- [ ] MSE improvement: ≥30% vs. no-perturbation baseline
- [ ] Pearson r: ≥0.70 (average across genes)
- [ ] Direction accuracy: ≥85% on top 20 DE genes

### Soft Targets (context-dependent)
- [ ] Predictions correlate with ground truth Pearson r > 0.60
- [ ] DEG overlap (Jaccard) > 0.50
- [ ] Performance consistent across genes (low CV in metrics)

### Failure Modes
- [ ] MSE improvement <10%: model not learning
- [ ] Pearson r < 0.40: poor overall fit
- [ ] Direction accuracy < 60%: predicting wrong sign of effect

---

## Computational Requirements

- **CPU:** 4+ cores
- **GPU:** NVIDIA (CUDA 11.x+) recommended but not required
- **Memory:** 16 GB RAM minimum (32 GB recommended for full 5K genes)
- **Storage:** ~5 GB for data + models
- **Time:** ~24 hours total (preprocessing + training + eval)

---

## References

### Code & Papers
- **GEARS Paper:** https://www.nature.com/articles/s41587-023-01905-6
- **GEARS GitHub:** https://github.com/yhr91/GEARS (expected)
- **Dixit et al.:** https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE90063

### Related Methods
- **CPA:** https://github.com/facebookresearch/CPA
- **scGen:** https://github.com/theislab/scGen
- **CellOracle:** https://github.com/morris-lab/CellOracle

---

## Notes

- This is the **exact dataset** used in GEARS paper (Dixit et al., GSE90063)
- Paper reports ~50% MSE improvement on this dataset
- Single-gene only (no multi-gene combos in original Dixit)
- K562 cell line (human erythroleukemia)
- Should be reproducible with published code
