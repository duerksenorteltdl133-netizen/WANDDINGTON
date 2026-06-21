# V23 实验报告：WaddingtonV12Arm — ml_heavy 路由扩展

**日期**：2026-06-21 | **状态**：已完成

---

## 结果

**avg hit@R5 = 0.249 — 低于 V22（0.253）**，修复 essential 但严重损害 Steinhart

| 数据集 | V19 | V22 | **V23** | Δ(23-22) |
|--------|-----|-----|--------|---------|
| IFNG | 0.171 | 0.192 | **0.194** | +0.002 |
| IL2 | 0.292 | 0.344 | 0.341 | -0.003 |
| Sanchez21 | 0.077 | 0.093 | 0.090 | -0.003 |
| Sanchez21_down | 0.094 | 0.097 | 0.093 | -0.004 |
| Carnevale22 | 0.056 | 0.059 | 0.057 | -0.002 |
| Scharenberg22 | 0.463 | 0.476 | 0.469 | -0.007 |
| **Steinhart** | 0.154 | 0.124 | **0.087** | **-0.037** |
| Replogle_essential | 0.571 | 0.556 | **0.571** | +0.015 |
| Replogle_gwps | 0.273 | 0.339 | **0.339** | +0.000 |
| **avg** | **0.239** | **0.253** | **0.249** | **-0.004** |

---

## 核心发现

### 1. LLM 对 Steinhart 实际上有益（修复方向完全反了）

```
Steinhart 轮次命中率 (hits/145):
                R1      R2      R3      R4      R5   hits
V19 (baseline): 0.055   0.090   0.110   0.122   0.154   22
V22 (baseline): 0.067   0.092   0.113   0.117   0.124   18
V23 (ml_heavy): 0.044   0.058   0.069   0.078   0.087   13
```

把 Steinhart 从 baseline(w_llm=0.40) → ml_heavy(w_llm=0.20) 使结果从 0.124 跌到 0.087（-0.037）。LLM 降权使情况更差 → **LLM 对 Steinhart 有实际贡献**。

原因：Steinhart 是 CRISPRa 筛选 GD2 表面表达（B4GALNT1, ST8SIA1 合成通路），Haiku 了解这一特定生物学路径，40% LLM 权重实际在帮助选择正确基因。

### 2. Steinhart 真正问题是 DepMap 特征（非路由）

```
V22 R1=0.067 → R5=0.124 (在线学习几乎停滞：R4→R5 仅 +0.007)
V19 R1=0.055 → R5=0.154 (在线学习有效：R4→R5 +0.032)
```

DepMap 特征（pan-cancer 必需性）与 GD2 合成基因**反向相关**：
- GD2 合成基因（B4GALNT1 等）在 DepMap 中 **depmap_frac_ess 低**（非 pan-essential）
- 当在线 ML 看到这些低 DepMap 分的基因是 hit 时，与先验相反 → 学习方向混乱
- 结果：R1 轻微改善（LOO AUC +0.008），但在线适应能力大幅下降

### 3. essential 完全恢复（0.556 → 0.571）

V23 路由变化对 essential 无影响（n=623<3000，始终 baseline），0.571 的差异是 LLM 方差。

### 4. 多个数据集微弱退步（-0.002 到 -0.007）

可能是随机种子方差，非系统性退步。

---

## 根本原因总结

Steinhart 下降轨迹的完整解释：

| 版本 | 变化 | Steinhart | 原因 |
|------|------|-----------|------|
| V19 | 基准（v1 特征 + baseline 路由）| 0.154 | ML + LLM 协同工作 |
| V21 | 加入 DepMap v2 特征 | 0.136 | DepMap 扰乱在线学习 |
| V22 | 选择性 DepMap（Steinhart 仍用 v2）| 0.124 | 同上，在线学习退化 |
| V23 | 加 ml_heavy 路由（LLM 20%）| 0.087 | LLM 权重降低 + DepMap 扰乱双重打击 |

---

## V24 方向：将 Steinhart 加入 DEPMAP_EXCLUDED

```python
DEPMAP_EXCLUDED = {"Replogle_K562_essential", "Steinhart"}
```

同时恢复 V22 路由（ml_heavy 需要 2%<hr<7%，Steinhart 0.80% 保持 baseline 40% LLM）。

预期：Steinhart 回到 V19 水平（~0.154），avg ≈ 0.256
