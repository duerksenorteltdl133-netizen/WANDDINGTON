# V22 计划：WaddingtonV11Arm — 选择性 DepMap 特征

**日期**：2026-06-21 | **状态**：计划中

## 修改

V21 发现 Replogle_essential 用 DepMap 特征后 hit@R5 下降 -0.089。

V22 仅改一处：对 Replogle_essential 使用 v1 训练数据（无 DepMap），
其他 8 个数据集继续使用 v2 训练数据（含 DepMap）。

DEPMAP_EXCLUDED = {"Replogle_K562_essential"}

## 预期

理论 avg ≈ (V21 总和 - 0.482 + 0.571) / 9 = 2.298/9 ≈ **0.255**
