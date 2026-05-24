# GEARS: Predicting Transcriptional Outcomes of Novel Multigene Perturbations
**Roohani, Huang & Leskovec, Nature Biotechnology 2023**

## Paper Metadata
- **Title:** Predicting transcriptional outcomes of novel multigene perturbations with GEARS
- **Authors:** Yusuf Roohani (Biomedical Data Science), Kexin Huang (Computer Science), Jure Leskovec (CS/Biomedical)
- **Institution:** Stanford University
- **Journal:** Nature Biotechnology
- **Published:** August 17, 2023
- **DOI:** https://doi.org/10.1038/s41587-023-01905-6
- **URL:** https://www.nature.com/articles/s41587-023-01905-6

## Biological Problem
Gene perturbation experiments are expensive and limited in scale. Predicting transcriptional outcomes for single-gene and multi-gene perturbations can prioritize experiments and identify synergistic combinations for therapeutic development. Existing methods either rely on incomplete gene regulatory networks or cannot predict non-additive effects.

## Method: GEARS (Graph-Enhanced Gene Activation and Repression Simulator)

### Architecture
- **Core:** Graph neural networks (GNNs) on biological knowledge graphs
- **Gene Representation:** Separate embeddings for gene baseline state and perturbation response
- **Knowledge Integration:**
  - **Gene coexpression graph:** Links genes with correlated baseline expression (Pearson correlation)
  - **Gene Ontology (GO) graph:** Links genes by shared biological pathways (Jaccard similarity)
- **Composition Module:** Sums perturbation embeddings to handle multi-gene perturbations
- **Cross-gene Layer:** Captures transcriptome-wide secondary effects
- **Output:** Gene-specific decoders predict post-perturbation gene expression

### Loss Function
- **Autofocus loss:** Emphasizes differentially expressed genes (exponent 2+γ)
- **Direction-aware loss:** Penalizes sign errors (predicted vs. true direction of change)
- **Uncertainty loss:** Bayesian formulation outputs confidence scores

## Datasets Tested

### Primary Datasets (Paper Tests)
1. **Dixit et al. (GSE90063):** Perturb-seq, K562 cells, ~1,000 single-gene perturbations
2. **Adamson et al. (GSE90546):** UPR (unfolded protein response) knockdowns
3. **Norman et al. (GSE133344):** CRISPRa screens, 102 genes, 131 two-gene perturbations
4. **Replogle et al.:** Genome-scale Perturb-seq, RPE-1 and K562 cells, 1,543+ perturbations
5. **Jost et al., Tian et al., Horlbeck et al.:** Additional validation datasets

## Key Results

### Single-Gene Predictions
- **MSE (top 20 DE genes):** GEARS 30–50% better than baselines (no perturbation, GRN-based)
- **Pearson correlation (all genes):** >2× improvement over baselines (CPA, GRN)
- **Direction accuracy:** Better prediction of sign of change

### Multi-Gene Predictions
- **Three generalization scenarios:**
  - Both genes seen during training (0/2 unseen)
  - One gene unseen (1/2 unseen)
  - Both genes unseen (2/2 unseen)
- **MSE improvement:** 30–53% across all scenarios
- **Highest improvement:** 53% for 2/2 unseen (novel gene combinations)

### Genetic Interaction Detection
GEARS identifies 5 subtypes:
1. **Synergy:** Two genes together > sum of individual effects
2. **Suppression:** Buffering interaction
3. **Neomorphism:** Novel phenotype not predicted by additivity
4. **Redundancy:** Overlapping function
5. **Epistasis:** One gene masks effect of another

**Performance:** Precision@10 improvements:
- Synergy: +40%
- Suppression: +40%
- Redundancy: +90%
- Epistasis: +90%

### Phenotype Prediction
- GEARS predicts all 5,151 pairwise combinations of 102 genes
- Identifies known phenotypes from training + predicts novel phenotypes
- New erythroid-like phenotype not observed in training set

## Strengths

1. **Generalization:** Predicts outcomes for unseen genes using knowledge graphs
2. **Multi-gene handling:** Captures non-additive effects, not just linear combinations
3. **Scalability:** Outperforms GRN-based methods on genome-wide screens
4. **Uncertainty quantification:** Outputs confidence scores for predictions
5. **Biological realism:** Multiple knowledge sources (coexpression + GO terms)
6. **Validation:** Cross-validated on 7+ datasets; real Perturb-seq experiments confirm predictions

## Limitations

1. **Cell-type specific:** Must train on same cell type/condition
2. **Data requirements:** Needs combinatorial perturbation data for accurate multi-gene predictions
3. **Knowledge graph dependence:** Poorly connected genes in GO/coexpression graphs → lower accuracy
4. **Confounders:** Cell cycle effects, editing efficiency, heterogeneity can affect accuracy
5. **No mechanistic insight:** Black-box predictions; doesn't reveal regulatory pathways

## Code & Data

### Availability
- **Paper states:** Code availability to be confirmed (often published on GitHub)
- **Datasets:** All used datasets are public (GEO accessions listed)
  - Dixit: **GSE90063** (this is in your dataset!)
  - Norman: **GSE133344**
  - Replogle: Figshare https://doi.org/10.25452/figshare.plus.20022944

### Implementation
- Deep learning framework likely PyTorch or TensorFlow
- GNN likely uses DGL (Deep Graph Library) or PyTorch Geometric
- Training uses SGD with the autofocus direction-aware loss

## Comparison to Baselines

### Models Compared
1. **No perturbation:** Assumes no change (oracle = baseline)
2. **GRN-based:** SCENIC network inference + linear propagation (adapted from CellOracle)
3. **CPA (Compositional Perturbation Autoencoder):** Deep learning without knowledge graphs

### Results: GEARS wins on all metrics
- MSE, Pearson correlation, direction accuracy, DEG enrichment, genetic interaction prediction

## Clinical/Research Impact

### Applications
- **Drug discovery:** Predict synergistic gene combinations for cancer therapy
- **Cell engineering:** Design multi-gene edits for induced pluripotent stem cells (iPSCs)
- **Immune therapy:** Re-engineer T cells by predicting optimal gene combinations
- **Aging reversal:** Identify reprogramming factor cocktails

### Experimental Design
- Recommend which gene pairs to experimentally validate
- Prioritize high-confidence predictions for experimental follow-up

## Related Work

- **scGen (Lotfollahi et al., 2019):** First deep learning perturbation predictor, single genes only
- **CPA (Lotfollahi et al., 2023):** Compositional approach, no knowledge graphs
- **CellOracle (Kamimoto et al., 2023):** GRN inference + perturbation, linear only
- **Prior screens:** Dixit (2016), Adamson (2016), Norman (2019), Replogle (2022)

## Reproducibility
- **Methods:** Fully described (embedding dimensions, graph construction, loss functions, hyperparameters)
- **Data:** All public (GEO, Figshare)
- **Code:** Expected to be published (confirm on authors' GitHub)
- **Experiments:** Five independent data splits reported; error bars shown

## Next Steps for Replication

1. Load GEARS code (GitHub or pip install if available)
2. Load Dixit dataset (GSE90063) from local zip
3. Preprocess: log-normalize, select variable genes, create knowledge graphs
4. Train on subset of Dixit perturbations
5. Evaluate on held-out test set: MSE, Pearson r, direction accuracy, DEG overlap
6. Compare to paper's reported benchmarks and baselines
7. Test on unseen genes or gene combinations

## Citation
```bibtex
@article{roohani2023gears,
  title={Predicting transcriptional outcomes of novel multigene perturbations with GEARS},
  author={Roohani, Yusuf and Huang, Kexin and Leskovec, Jure},
  journal={Nature Biotechnology},
  volume={42},
  pages={927--935},
  year={2024},
  doi={10.1038/s41587-023-01905-6}
}
```
