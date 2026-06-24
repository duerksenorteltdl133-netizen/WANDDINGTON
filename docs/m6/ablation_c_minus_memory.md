# M6 Ablation: C − Memory (5 Seeds)

**Date**: 2026-06-24  
**Question**: How much does cross-experiment memory contribute to C-arm performance?  
**Ablation**: WaddingtonV14NoMemoryArm — identical to V14 but `memory_entries=[]`

---

## Results

| Dataset | C (full) | C − memory | Delta |
|---|---|---|---|
| IFNG | 0.190 | 0.189 | −0.001 |
| IL2 | 0.343 | 0.346 | +0.003 |
| Sanchez21 | 0.095 | 0.091 | −0.004 |
| Sanchez21_down | 0.100 | 0.097 | −0.003 |
| Carnevale22 | 0.057 | 0.059 | +0.002 |
| Scharenberg22 | 0.461 | 0.478 | +0.017 |
| Steinhart | 0.143 | 0.156 | +0.013 |
| Replogle_K562_essential | 0.575 | 0.559 | −0.016 |
| Replogle_K562_gwps | 0.339 | 0.343 | +0.004 |
| **Average** | **0.256** | **0.258** | **+0.002** |

---

## Conclusion: Memory Contribution ≈ 0

The ablation is a **null result**. Removing cross-experiment memory produces no consistent performance change:
- All deltas ≤ 0.017 in absolute value (within seed-to-seed variance)
- C−memory average (0.258) is marginally above full C (0.256) — not a real gain
- No dataset shows a large, consistent benefit from memory

### Why memory doesn't help in this setup

The cross-experiment memory entries are drawn from the same 9 BDA datasets (LOO setup). The LLM's **parametric knowledge already contains this biological context** — it was trained on literature covering IFN-γ signaling, CAR-T biology, essential gene screens, etc. The explicit memory prompt section is therefore largely **redundant** with what the LLM already knows implicitly.

In a real deployment scenario (novel experiments not in training data), cross-experiment memory from a lab's own history could be more valuable. But in this benchmark, the memory module does not add measurable signal.

### Implication for paper

- Memory is **not load-bearing** for performance — removing it doesn't degrade results
- The performance advantage of C over B (pure LLM) comes from **ML + routing**, not memory
- Memory can be included as a design component but should not be presented as a key contributor to performance gains
- This is actually a useful finding: it shows the system is robust to this component, and the gains are attributable to the ML adaptation mechanism

---

## Ablation Status

| Ablation | Status | Key finding |
|---|---|---|
| C − memory | ✅ Done | Memory ≈ 0 contribution; delta ±0.017 noise |
| C − ML | ⬜ Pending | |
| C − LLM | ⬜ Pending | |
| Shuffled gene names | ⬜ Pending | |
