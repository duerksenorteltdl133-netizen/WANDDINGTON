# V18 计划：WaddingtonV7Arm — 三桶路由 + gwps 两步策略

**日期**：2026-06-21 | **状态**：计划中

---

## 背景

V17 最大残余 gap：Replogle_gwps (-0.036 vs V12=0.290)。
- V12 用 ML shortlist + LLM：0.290（gwps 历史最高）
- V17 用自由 LLM：0.254

Replogle_gwps（9193 genes, 10.1% hit rate）适合 ML 先过滤高密度 hit 基因，再让 LLM 在候选池中精选。

---

## V18 设计：三桶路由

```python
def _classify(n_genes, n_hits):
    hr = n_hits / n_genes
    if n_genes > 15000 and 0.02 < hr < 0.07:   return "ml_heavy"   # 0.80/0.20
    if 3000 < n_genes <= 15000 and hr > 0.08:   return "two_stage"  # ML缩窄→LLM
    return "baseline"                                                  # 0.60/0.40

```

| 数据集 | 分类 | 策略 |
|--------|------|------|
| IFNG, IL2, Sanchez21, Sanchez21_down, Carnevale22 | ml_heavy | 加权集成 0.80/0.20 |
| **Replogle_gwps** | **two_stage** | **ML top-512 → LLM 精选** |
| Scharenberg22, Steinhart, Replogle_essential | baseline | 加权集成 0.60/0.40 |

---

## two_stage 详细流程

```
Round r：
  1. ML ranked_candidates(512, exclude=selected)
     → 返回 [(gene, ml_score), ...]，按 ML 分从高到低

  2. 构建含候选池的 LLM prompt：
     - 任务描述 + 跨实验记忆 + 历史反馈
     - "ML候选池（共 512 个，按置信度排序）：
         GENE1 (score 0.823), GENE2 (score 0.791), ..."
     - 指令：优先从候选池中选，也可提名候选池外的基因

  3. LLM（temperature=0）输出 batch_size=128 个基因

  4. 匹配 + 填充：
     - 先收集 LLM 提名且在完整 gene pool 中的基因
     - 不足时从 ML 候选池顺序填充
```

**Shortlist size=512** = 4×batch_size，占 gwps 总基因池的 5.6%；
期望 ML recall@512 ≈ 35-50%（即 shortlist 中含 330-460 个真实 hit），
LLM 在此高质量候选池中选择，精度大幅提升。

---

## 实现

### 修改 `llm_reasoning_arm.py`

添加 `select_with_shortlist(round_idx, shortlist)` 方法：构建含 shortlist 的 prompt，调用 LLM，解析返回基因。

### 新增 `waddington_v7_arm.py`

```python
class WaddingtonV7Arm(BaseArm):
    SHORTLIST_SIZE = 512

    def select(self, round_idx, revealed):
        if self._route == "two_stage":
            return self._select_two_stage(round_idx, revealed)
        else:
            return self._select_weighted(round_idx, revealed)

    def _select_two_stage(self, round_idx, revealed):
        candidates = self._online.ranked_candidates(self.SHORTLIST_SIZE, exclude=self._selected)
        llm_picks = self._llm.select_with_shortlist(round_idx, candidates)
        return self._match_and_fill(llm_picks, candidates)

    def _select_weighted(self, round_idx, revealed):
        # 同 V17（加权集成）
        ...
```

---

## 预期性能

| 数据集 | V17 | V18 预期 | delta |
|--------|-----|---------|-------|
| Replogle_gwps | 0.254 | **~0.285** | +0.031 |
| 其他 8 个 | 同 V17 | 同 V17 | 0 |
| **avg** | **0.237** | **~0.240** | **+0.003** |

Replogle_gwps 预期达到 V12（0.290）的 95%（因为 V18 还有 temperature=0 和跨实验记忆优势，但 V12 的 shortlist=384 可能恰好是 gwps 的最优点）。
