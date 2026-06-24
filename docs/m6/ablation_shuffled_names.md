# M6 Ablation: Shuffled Gene Names (5 Seeds)

**Date**: 2026-06-24  
**Question**: Does the LLM use gene-name biological semantics, or does it rely on other signals?  
**Ablation**: WaddingtonV14ShuffledNamesArm — identical to V14 except every gene name shown to
the LLM is replaced with an anonymous identifier (GENE_00001, GENE_00002, ...).

The LLM still sees: biological task context (cell line, phenotype, measurement),
experimental hit/non-hit history as anonymous IDs, ML confidence scores in two-stage shortlists.
The LLM cannot see: real HGNC gene symbols anywhere.

---

## Results

| Dataset | C (full) | Shuffled names | Delta |
|---|---|---|---|
| IFNG | 0.191 | 0.175 | −0.016 |
| IL2 | 0.355 | 0.351 | −0.004 |
| Sanchez21 | 0.093 | 0.080 | −0.013 |
| Sanchez21_down | 0.098 | 0.092 | −0.006 |
| Carnevale22 | 0.056 | 0.059 | +0.003 |
| Scharenberg22 | 0.473 | **0.551** | **+0.078** |
| Steinhart | 0.145 | 0.076 | **−0.069 (−47%)** |
| Replogle_K562_essential | 0.568 | 0.524 | **−0.044** |
| Replogle_K562_gwps | 0.339 | 0.343 | +0.004 |
| **Average** | **0.258** | **0.250** | **−0.008** |

---

## Conclusion: Gene-Name Semantics Drive LLM Value for Pathway-Specific Tasks

C avg=0.258 vs Shuffled avg=0.250 → anonymizing gene names costs **−0.008 on average**, but
the effect is **highly asymmetric** across tasks.

### Gene names are critical (C >> Shuffled)

| Dataset | Route | C | Shuffled | Lost |
|---|---|---|---|---|
| Steinhart | baseline (40% LLM) | 0.145 | 0.076 | **−0.069 (−47%)** |
| essential | baseline (40% LLM) | 0.568 | 0.524 | −0.044 (−8%) |

**Steinhart** drops nearly to zero LLM contribution (0.076 vs C-LLM=0.090).
Without gene names, the LLM cannot identify the GD2 synthesis pathway genes
(B4GALNT1, ST8SIA3, B3GALT4) — it can only guess from meaningless GENE_XXXXX identifiers.
The 47% performance drop confirms that LLM's Steinhart gain is **entirely driven by biological
gene-name knowledge**, not by task context or experimental feedback.

**essential** similarly loses significant performance without gene names.
LLM can't identify known essential genes (RPS*, CDK4, KRAS, MYC) by anonymous IDs.
The remaining 0.524 performance reflects the ML component (60%) plus noise from
random anonymous LLM selections (40%).

### Gene names are harmful for Scharenberg22 (Shuffled >> C)

| Dataset | Route | C | Shuffled | C-LLM | C-ML |
|---|---|---|---|---|---|
| Scharenberg22 | baseline (40% LLM) | 0.473 | **0.551** | 0.592 | 0.433 |

Without gene names, LLM can no longer apply its CAR-T resistance gene knowledge.
This improves performance by +0.078, moving toward the C-LLM level (0.592).
The remaining gap (0.551 vs 0.592) is because shuffled LLM still occupies 40% of the
weight slot with random selections, while C-LLM gives 100% weight to ML.

**Interpretation**: For Scharenberg22, LLM's biological knowledge about CAR-T targets
actively conflicts with the strong ML signal. Removing that knowledge (via name shuffling)
improves performance — the same direction as removing LLM entirely.

### Gene names matter little for large generic screens

| Dataset | Route | C | Shuffled | Delta |
|---|---|---|---|---|
| IFNG | ml_heavy (20% LLM) | 0.191 | 0.175 | −0.016 |
| IL2 | ml_heavy (20% LLM) | 0.355 | 0.351 | −0.004 |
| Sanchez21 | ml_heavy (20% LLM) | 0.093 | 0.080 | −0.013 |
| Carnevale22 | ml_heavy (20% LLM) | 0.056 | 0.059 | ≈0 |
| gwps | two_stage | 0.339 | 0.343 | ≈0 |

For ml_heavy datasets (20% LLM weight), the LLM's semantic contribution is small to begin with
(confirmed by C-LLM ablation). Shuffling names causes proportionally small losses.

**gwps** (two-stage routing) is exactly neutral (+0.004): in the shortlist prompt, the LLM
sees ML confidence scores alongside anonymous GENE_XXXXX names. It picks high-ML-confidence
identifiers → effectively re-ranks by ML score → identical to ML-only selection.
This confirms: **LLM adds no semantic value for gwps beyond what ML scores already encode.**

---

## Cross-Ablation Summary: What Creates LLM Value?

| Dataset | C-LLM (no LLM) | Shuffled (fake names) | C (real names) | LLM gene-name gain |
|---|---|---|---|---|
| Steinhart | 0.090 | 0.076 | 0.145 | **+0.069 (+96%)** |
| essential | 0.476 | 0.524 | 0.568 | **+0.044 (+8%)** |
| Scharenberg22 | **0.592** | 0.551 | 0.473 | −0.078 (harmful) |
| gwps | 0.343 | 0.343 | 0.339 | ≈0 |
| IFNG | 0.190 | 0.175 | 0.191 | +0.016 |

The pattern is clear: **LLM gene-name semantic knowledge is the primary driver of LLM value**
for pathway-specific tasks (Steinhart, essential). For large screens and two-stage retrieval,
ML scores and task context are sufficient — gene names add no signal.

Note: For Steinhart, shuffled (0.076) < C-LLM (0.090). With fake names, LLM random
selections still occupy 40% weight and actively hurt ML signal; removing LLM entirely
(C-LLM) is better than random LLM. This underscores that LLM value is *specifically*
gene-name-driven, not from LLM's "reasoning" about the task context.

---

## Complete Ablation Picture

| Configuration | avg R5 | Notes |
|---|---|---|
| A (Coreset) | 0.134 | Algorithmic baseline |
| B (pure LLM) | 0.220 | LLM parametric knowledge |
| C − ML (static LOO + LLM) | 0.243 | +LOO prior over pure LLM |
| C − LLM (online ML only) | 0.254 | ML dominates; LLM nets +0.005 |
| C − memory (no cross-exp memory) | 0.258 | Memory ≈ 0 contribution |
| C (full) | 0.258 | Online ML + LLM + memory |
| Shuffled gene names | 0.250 | Without gene semantics, LLM costs −0.008 |

---

## Ablation Status: All Complete

| Ablation | Status | Key finding |
|---|---|---|
| C − memory | ✅ Done | Memory ≈ 0 contribution (LLM parametric covers same info) |
| C − LLM | ✅ Done | LLM critical for Steinhart (+70%), essential (+23%); hurts Scharenberg22 (−0.123) |
| C − ML | ✅ Done | Online retraining most consistent contributor: +0.015 avg (+6%) |
| Shuffled gene names | ✅ Done | LLM value is gene-name-driven: Steinhart −47%, Scharenberg22 +16% |
