# V9 计划：A 臂 — Coreset 采集函数（WADDINGTON_PLAN M2）

**日期**：2026-06-20 | **状态**：进行中 | **目标**：接入第一个自适应采集函数

---

## 背景

V8 建立了序贯 Oracle 评估框架，并用 StaticRankerArm（V7 LightGBM）作为验证。但 StaticRankerArm 是**非自适应**的：第 0 轮之后无论实验反馈如何，排名都不变。

WADDINGTON_PLAN 的 M2 要求接入 **A 臂（纯算法，不使用生物学先验）**，GeneDisco 的 Coreset 是标准选择。Coreset 完全靠特征空间覆盖度做决策，不用任何生物学知识，代表"只靠数据结构"的基线。

---

## Coreset 算法

**贪心 k-center（greedy farthest-point）**：

给定已选集合 S 和候选池 P：
1. 计算每个候选基因到 S 中最近点的距离：`d[g] = min_{s ∈ S} dist(g, s)`
2. 重复 batch_size 次：
   - 选 `g* = argmax_{g ∈ P} d[g]`（距离已选集最远的基因）
   - 将 g* 加入选择
   - 更新 `d[g] = min(d[g], dist(g, g*))` for all 剩余 g

**直觉**：每次选离已测基因"最不像"的基因，确保每轮实验覆盖特征空间中的新区域。

**初始化（第 0 轮，S 为空）**：选特征空间中离全局重心最远的基因作为第一个点，再用 k-center 选剩余 batch_size-1 个。

---

## 特征空间

使用 `lgbm_training_data.csv` 中已有的 9 个特征（无需重新计算）：

```
g1_ppi_score, hub_score_norm, archs4_coexpr, ppi_score_sum, kegg_overlap,
pli_score, string_degree_norm, kegg_pathway_count_norm, reactome_pathway_count_norm
```

使用 Euclidean 距离，特征已归一化（均在 [0,1]），无需额外缩放。

**关键问题**：Coreset 的特征空间来自训练数据（含锚点特异性特征），但 Coreset 本身不使用标签，也不使用生物学先验——纯粹是几何覆盖。

---

## 新增文件

```
workspace/agent/arms/coreset_arm.py   # CoresetArm：贪心 k-center
```

更新 `run_sequential.py`：添加 `--arms coreset` 选项。

---

## 预期结果

| 方法 | 原理 | 预期 hit@R5 avg |
|------|------|----------------|
| Random | 随机 | ~0.066 |
| **Coreset** | 特征空间覆盖（无生物先验） | ~0.080–0.120（不确定） |
| StaticRanker | V7 生物学先验（非自适应） | 0.217 |

**核心假设**：Coreset 在"通用多样性"上会比 Random 好，但因为没有生物学先验，应该显著低于 StaticRanker（尤其在前几轮）。这也是 WADDINGTON_PLAN 的核心论点：**冷启动时知识先验 > 纯算法**。

若 Coreset 接近 StaticRanker，说明特征本身已经携带了足够的几何结构信息，生物学先验的附加价值有限。

---

## 与 WADDINGTON_PLAN 的关系

| 里程碑 | 状态 |
|--------|------|
| M1 骨架 + Oracle | ✅ V8 完成 |
| **M2 A臂（Coreset）** | **V9（本版本）** |
| M3 PerTurboAgent 复现 | V10 |
| M4 B臂（通用 LLM） | V11 |
| M5 ★ 跨实验记忆 | V12 |
| M6 全面实验 + 消融 | V13 |
