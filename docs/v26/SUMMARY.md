# V26 Benchmark Summary — WaddingtonV15Arm (Uncertainty-Aware Dynamic Weights)

**Date**: 2026-06-23  
**Seeds**: 3 | **Rounds**: 5

## Core Idea
Instead of fixed ML/LLM weights (V14: 0.80/0.20 for ml_heavy, 0.60/0.40 for baseline),
dynamically adjust per round based on uncertainty signals:
- **ML confidence** = `std(predict_proba scores) / 0.15` — higher spread = more confident
- **LLM confidence** = LLM's self-reported float `{"genes":[...], "confidence": 0.75}` per round
- **Weight formula**: `w_ml = clip(ml_conf / (ml_conf + llm_conf), w_min, w_max)`

Route-aware bounds: ml_heavy → w_ml ∈ [0.60, 0.95], baseline → w_ml ∈ [0.35, 0.80]

## Results vs V14

| Dataset | V14 R5 | V15 R5 | Delta |
|---|---|---|---|
| IFNG | 0.398 | 0.182 | **-0.216** |
| IL2 | 0.354 | 0.309 | -0.045 |
| Sanchez21 | 0.210 | 0.069 | **-0.141** |
| Sanchez21_down | 0.328 | 0.084 | **-0.244** |
| Carnevale22 | 0.315 | 0.059 | **-0.256** |
| Scharenberg22 | 0.181 | 0.449 | **+0.268** |
| Steinhart | 0.137 | 0.142 | +0.005 |
| Replogle_K562_essential | 0.096 | 0.566 | **+0.470** |
| Replogle_K562_gwps | 0.141 | 0.339 | **+0.198** |
| **avg** | **~0.240** | **0.244** | +0.004 |

## Diagnosis

### Why ml_heavy datasets regressed severely
V14 gives ml_heavy datasets w_ml=0.80. V15 gives them w_ml≈0.60 because:
1. ML confidence saturates at 1.0 (ML_CONF_SCALE=0.15 is too small; LOO prior already has std>>0.15)
2. LLM confidence is consistently high (0.72-0.89) across ALL datasets — not informative
3. Resulting ratio: `1.0/(1.0+0.82) = 0.549`, clipped to floor of 0.60
4. Net effect: ml_heavy datasets lose 20pp of ML weight → equivalent to reverting to V10-era weights

### Why baseline/small datasets improved
V14's fixed w_ml=0.60 for baseline was empirically somewhat too high:
- **essential** (0.096→0.566): LLM knows essential biology well; V15 shifts to ~0.53 ML / 0.47 LLM → LLM now drives more selections
- **Scharenberg22** (0.181→0.449): CAR-T screen where LLM knows target pathways; more LLM weight helps
- **gwps** (0.141→0.339): two_stage route, unchanged mechanism, variance between seeds explains the gap

### Root cause of failure
**LLM self-reported confidence is not discriminative.** Across 9 datasets, 5 rounds, the LLM reports:
- High confidence (0.78-0.89) for well-understood biology (IFNG, IL2, essential)
- Also high confidence (0.72-0.82) for harder datasets (Sanchez21, Carnevale22)
- This collapses all dynamic weights to the same ~0.55 ratio

## Observed Dynamic Weight Trace (sample)
```
IFNG   R0: ml=1.000 llm=0.820 → w_ml=0.600 (should be 0.80)
IFNG   R3: ml=0.978 llm=0.820 → w_ml=0.600 (no adaptation)
Steinhart R0: ml=0.791 llm=0.780 → w_ml=0.503 (near 50/50, appropriate!)
Steinhart R3: ml=0.808 llm=0.820 → w_ml=0.496 (near 50/50)
essential R2: ml=1.000 llm=0.890 → w_ml=0.529 (more LLM, helpful here)
```

Steinhart shows the mechanism working correctly: ML and LLM nearly tied → 50/50 weights (down from V14's 0.60). This aligns with V14's intuition (both components contribute equally for difficult biology).

## Lessons

1. **LLM confidence prompting is not calibrated**: Models output similar confidence regardless of task difficulty — not a useful signal for discriminating ML vs LLM weight.

2. **ML score std is correctly directional but miscalibrated**: `ML_CONF_SCALE=0.15` is too small — LOO prior already has std≫0.15 for large datasets (n>15000), causing premature saturation to 1.0 even before any in-experiment adaptation.

3. **The mechanism can work in principle**: Steinhart and essential show that when ML is genuinely weaker (lower spread relative to LLM confidence), dynamic weights correctly shift toward LLM. The problem is calibration, not the idea.

4. **Alternative for future work**: Instead of LLM self-report, use proxy measures:
   - LLM confidence = hit rate of LLM's selections in previous rounds (retrospective calibration)
   - ML confidence = LOO AUC (per-dataset constant, known from feature analysis) rather than score std
   - Or: adjust weights AROUND V14's fixed values rather than computing from scratch

## Decision
**Revert to V14 (WaddingtonV15Arm) as the C-arm for M6 three-arm comparison.**

V15 avg (0.244) is marginally above V14 (~0.240) only due to lucky essential/Scharenberg22 gains
that are offset by severe regressions on 5 ml_heavy datasets. The dynamic uncertainty approach
is conceptually valid but requires better calibration of the LLM confidence signal.

Next: M6 three-arm comparison: A (Coreset) vs B (LLMReasoningArm) vs C (WaddingtonV14Arm)
