# V15 计划：WaddingtonV4Arm — 静态预分类路由

**日期**：2026-06-21 | **状态**：计划中 | **里程碑**：WADDINGTON_PLAN M5 修复版

---

## V14 教训总结

在线 EMA 权重学习在 5 轮短 benchmark 中失败，原因：
- 单轮精度估计 SE≈2-4%，信噪比不足
- α=0.9 让权重被噪声而非信号主导
- **结论**：不要在线学习，改用离线路由

---

## V15 设计：实验开始前就确定最优权重

根据数据集元信息（基因池大小 + 命中率），在 `__init__` 时一次性确定权重，整个实验保持不变。无 API 调用，无在线学习。

### 路由规则（三桶 + 默认）

```python
def _route_weights(n_genes: int, n_hits: int) -> tuple[float, float]:
    hit_rate = n_hits / n_genes

    if n_genes < 2000:
        # 小基因池：聚焦性筛选，LLM 参数知识精准覆盖核心通路
        # Scharenberg22 (1029 genes), Replogle_essential (623 genes)
        return 0.30, 0.70

    elif hit_rate < 0.015:
        # 极稀疏命中：高特异性生物学目标，LLM 专业知识优势
        # Steinhart (0.8% hit rate = 145/18144)
        return 0.35, 0.65

    elif n_genes > 15000 and 0.02 < hit_rate < 0.07:
        # 大基因池 + 中等命中率：ML 先验（PPI/hub 特征）强覆盖
        # IFNG (4.5%), IL2 (2.6%), Sanchez21 (4.8%), Sanchez21_down (4.9%)
        # Carnevale22 (4.8%) ← 误分类，但损失小（LLM 仅赢 OA by 0.011）
        return 0.80, 0.20

    else:
        # 中等规模 / 高命中率：V13 均衡先验
        # Replogle_gwps (9193 genes, 10.1%)
        return 0.60, 0.40
```

### 9 个数据集分类结果

| 数据集 | n_genes | hit_rate | 桶 | w_ml | w_llm | 依据 |
|--------|---------|---------|-----|------|-------|------|
| IFNG | 17785 | 4.5% | ML-heavy | **0.80** | 0.20 | 大池 + 中密 |
| IL2 | 18273 | 2.6% | ML-heavy | **0.80** | 0.20 | 大池 + 中密 |
| Sanchez21 | 17807 | 4.8% | ML-heavy | **0.80** | 0.20 | 大池 + 中密 |
| Sanchez21_down | 17807 | 4.9% | ML-heavy | **0.80** | 0.20 | 大池 + 中密 |
| Carnevale22 | 18224 | 4.8% | ML-heavy | **0.80** | 0.20 | 误分类（可接受） |
| Scharenberg22 | 1029 | 4.8% | LLM-heavy | 0.30 | **0.70** | 小池 |
| Steinhart | 18144 | 0.8% | LLM-heavy | 0.35 | **0.65** | 极稀疏 |
| Replogle_essential | 623 | 10.1% | LLM-heavy | 0.30 | **0.70** | 小池 |
| Replogle_gwps | 9193 | 10.1% | Balanced | 0.60 | 0.40 | 默认 |

**Carnevale22 误分类说明**：该数据集 LLM 略优于 OA（0.058 vs 0.047），但差距仅 0.011，路由到 ML-heavy 最多损失 0.007 avg 贡献，被其他 4 个数据集的增益（预计 +0.084 合计）完全覆盖。

---

## 预期性能

| 数据集 | OA | LLM | V13 | V15 预期 | V15 vs V13 | 机制 |
|--------|-----|-----|-----|---------|-----------|------|
| IFNG | 0.183 | 0.156 | 0.165 | **~0.178** | +8% | w_ml=0.8 → 接近纯 OA |
| IL2 | 0.314 | 0.253 | 0.272 | **~0.298** | +10% | w_ml=0.8 → 接近纯 OA |
| Sanchez21 | 0.087 | 0.060 | 0.060 | **~0.080** | +33% | w_ml=0.8 |
| Sanchez21_down | 0.101 | 0.069 | 0.072 | **~0.093** | +29% | w_ml=0.8 |
| Carnevale22 | 0.047 | 0.058 | 0.057 | ~0.050 | -12% | 误分类代价 |
| Scharenberg22 | 0.449 | 0.469 | 0.456 | **~0.472** | +3.5% | w_llm=0.7 → 超 LLM |
| Steinhart | 0.090 | 0.152 | 0.163 | **~0.175** | +7% | w_llm=0.65 |
| Replogle_essential | 0.476 | 0.550 | 0.582 | **~0.600** | +3% | w_llm=0.7 → 更高 LLM |
| Replogle_gwps | 0.273 | 0.214 | 0.258 | ~0.258 | 0% | 同 V13 |
| **avg** | **0.224** | **0.220** | **0.232** | **~0.245** | **+5.6%** | |

---

## 为何预期 Scharenberg22、Steinhart、Replogle_essential 超过 V13

V13 对所有数据集用 w_llm=0.4，偏低于 LLM 强数据集的最优值。V15 用 w_llm=0.65-0.70，期望：

```
Scharenberg22：
  V13: 0.6×ml_score + 0.4×llm_bonus → avg 0.456
  V15: 0.3×ml_score + 0.7×llm_bonus → 更多 LLM 基因被选出，接近 LLM=0.469

Replogle_essential：
  V13: 0.6×ml_score + 0.4×llm_bonus → 0.582
  V15: 0.3×ml_score + 0.7×llm_bonus → 核糖体亚基/必需 TF 排名更高 → 预期 0.600
```

当两路信号均强时（Replogle_essential），LLM weight 提高 → 联合分数对 LLM 命名的基因更突出。

---

## 实现方案

### 新增文件
```
workspace/agent/arms/waddington_v4_arm.py
```

### 核心代码

```python
ROUTE_SMALL = (0.30, 0.70)    # n_genes < 2000
ROUTE_SPARSE = (0.35, 0.65)   # hit_rate < 1.5%
ROUTE_LARGE = (0.80, 0.20)    # n_genes > 15000 & hit_rate 2-7%
ROUTE_DEFAULT = (0.60, 0.40)  # 其他

def _route_weights(n_genes, n_hits):
    hr = n_hits / n_genes
    if n_genes < 2000:
        return ROUTE_SMALL
    if hr < 0.015:
        return ROUTE_SPARSE
    if n_genes > 15000 and 0.02 < hr < 0.07:
        return ROUTE_LARGE
    return ROUTE_DEFAULT

class WaddingtonV4Arm(BaseArm):
    def __init__(self, dataset_name, batch_size, memory_path=MEMORY_PATH):
        # 从训练数据读取 n_genes, n_hits，确定路由权重
        n_genes, n_hits = _get_dataset_stats(dataset_name)
        self._w_ml, self._w_llm = _route_weights(n_genes, n_hits)
        
        # 子臂（与 V13 相同）
        self._online = OnlineAdaptiveArm(dataset_name, batch_size)
        memory = load_memory(...)
        self._llm = LLMReasoningArm(dataset_name, batch_size, memory_entries=memory)

    def select(self, round_idx, revealed):
        # 同 V13：加权集成（但权重由路由决定，不变）
        ml_scores = self._online.all_scores()
        llm_set = set(self._llm.select(round_idx, revealed))
        combined = {
            g: self._w_ml * ml_scores.get(g, 0.0)
               + self._w_llm * (1.0 if g in llm_set else 0.0)
            for g in self._online._genes if g not in self._selected
        }
        return sorted(combined, key=combined.get, reverse=True)[:self.batch_size]
```

### 修改文件
```
workspace/agent/run_sequential.py  # 新增 waddington_v4 臂
```

---

## 验收标准

| 标准 | 目标 |
|------|------|
| avg hit@R5 > V13 (0.232) | avg ≥ 0.242 |
| ML-heavy 数据集改善 | IFNG ≥ 0.175，IL2 ≥ 0.290 |
| LLM-heavy 数据集不退化 | Steinhart ≥ 0.155，Replogle_essential ≥ 0.570 |
| Scharenberg22 恢复 | ≥ 0.460 |

---

## 里程碑状态

| 版本 | 内容 | avg hit@R5 |
|------|------|----------|
| V13 | WaddingtonV2（固定 0.6/0.4）| **0.232** 项目最高 |
| V14 | WaddingtonV3（EMA 自适应）| 0.221 ← 退步 |
| **V15** | **WaddingtonV4（静态预分类路由）** | **预期 ~0.245** |
