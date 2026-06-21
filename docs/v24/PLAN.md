# V24 计划：WaddingtonV13Arm — 将 Steinhart 加入 DEPMAP_EXCLUDED

**日期**：2026-06-21 | **状态**：计划中

## 改动

DEPMAP_EXCLUDED = {"Replogle_K562_essential", "Steinhart"}
→ Steinhart 使用 v1 特征（无 DepMap），保持 baseline 路由（w_llm=0.40）

路由恢复 V22 风格（ml_heavy 需要 2%<hr<7%）。

## 预期

Steinhart 回到 V19 水平（~0.154），avg ≈ 0.256
