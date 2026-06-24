# M6 Ablation: C − LLM (5 Seeds)

**Date**: 2026-06-24  
**Question**: How much does the LLM component contribute to C-arm performance?  
**Ablation**: WaddingtonV14NoLLMArm — pure online adaptive ML with V14 DepMap feature routing, no LLM voting

---

## Results

| Dataset | C (full) | C − LLM | Delta |
|---|---|---|---|
| IFNG | 0.191 | 0.190 | −0.001 |
| IL2 | 0.348 | 0.349 | +0.001 |
| Sanchez21 | 0.090 | 0.098 | +0.008 |
| Sanchez21_down | 0.096 | 0.093 | −0.003 |
| Carnevale22 | 0.057 | 0.051 | −0.006 |
| Scharenberg22 | 0.469 | **0.592** | **+0.123** |
| Steinhart | 0.153 | 0.090 | **−0.063** |
| Replogle_K562_essential | 0.584 | 0.476 | **−0.108** |
| Replogle_K562_gwps | 0.339 | 0.343 | +0.004 |
| **Average** | **0.259** | **0.254** | **−0.005** |

---

## Key Finding: LLM is dataset-specific, not universally beneficial

The aggregate picture (C avg=0.259 > C−LLM avg=0.254, +0.005) understates the real story.
The LLM's contribution is **highly dataset-dependent**:

### LLM is critical (C >> C−LLM)

| Dataset | C | C−LLM | LLM gain |
|---|---|---|---|
| Steinhart | 0.153 | 0.090 | **+0.063 (+70%)** |
| essential | 0.584 | 0.476 | **+0.108 (+23%)** |

**Why**: These datasets involve well-characterized biology where LLM's parametric knowledge provides targeted prior knowledge that ML features (PPI/pathway/DepMap) cannot capture:
- **Steinhart**: GD2 synthesis pathway (B4GALNT1, ST8SIA3, B3GALT4) — not encoded in PPI networks, but well-known in the LLM's training literature
- **essential**: Core essential genes (MYC, KRAS, CDK4, RPS...) — LLM knows these precisely from curated databases cited in its training

### LLM provides NO benefit on large screens

| Dataset | C | C−LLM | LLM gain |
|---|---|---|---|
| IFNG | 0.191 | 0.190 | ≈0 |
| IL2 | 0.348 | 0.349 | ≈0 |
| gwps | 0.339 | 0.343 | ≈0 |
| Sanchez21_down | 0.096 | 0.093 | ≈0 |

**Why**: On large genome-wide datasets (n>15000), the online ML component accumulates sufficient statistical signal from revealed hits to outperform LLM's static prior. The 20% LLM weight in ml_heavy routing adds noise rather than signal.

Notably, **gwps (two_stage routing)** also shows no LLM benefit: removing LLM from the ML→LLM pipeline gives 0.343 vs 0.339. The ML pre-filter step does all the work; the LLM reranking of the top-384 adds nothing.

### LLM actively hurts Scharenberg22

| Dataset | C | C−LLM | C−only ML |
|---|---|---|---|
| Scharenberg22 | 0.469 | **0.592** | — |

**Why**: Scharenberg22 has extremely high ML LOO AUC (0.825 with v3 K562 features). The ML model alone is very accurate for CAR-T screen hits. Adding LLM weight (0.40 in baseline routing) dilutes the strong ML signal with the LLM's less accurate biological prior, degrading performance by −0.123.

This is the only dataset where removing LLM gives a large positive gain.

---

## Reconciliation with Three-Arm Comparison

In the three-arm comparison, B (pure LLM) at 0.461 nearly matched C at 0.441 for Scharenberg22 (with different seed variance). Here C−LLM reaches 0.592. This reveals the architecture:
- B arm uses StaticRanker LOO prior as fallback (not online adaptive ML)
- C−LLM uses **online adaptive ML with v3 DepMap K562 features** — much stronger for Scharenberg22
- The combined C arm (0.469) is pulled DOWN from 0.592 by LLM's 0.40 weight

---

## Ablation Summary: What Each Component Does

| Component | Role | Key datasets |
|---|---|---|
| Online ML (DepMap+PPI) | Main engine on large screens | IFNG, IL2, gwps, Sanchez21 |
| LLM prior | Critical for pathway-specific tasks | Steinhart (+70%), essential (+23%) |
| LLM can hurt | When ML is very accurate | Scharenberg22 (−0.123) |
| Memory | No consistent benefit | All datasets (±noise) |

---

## Ablation Status

| Ablation | Status | Key finding |
|---|---|---|
| C − memory | ✅ Done | Memory ≈ 0 contribution |
| C − LLM | ✅ Done | LLM critical for Steinhart (+70%), essential (+23%); hurts Scharenberg22 (−0.123) |
| C − ML | ⬜ Pending | |
| Shuffled gene names | ⬜ Pending | |
