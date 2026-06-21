# V19 计划：WaddingtonV8Arm — gwps shortlist 修复

**日期**：2026-06-21 | **状态**：计划中

---

## 背景

V18 的 two-stage 策略（ML top-512 → LLM）只取得 gwps=0.277，
而 V12（ML top-384 → LLM，无记忆，temp=0.5）达到 0.290。

根本原因：V18 的 `_build_shortlist_prompt` 截断 `shortlist[:80]`，
LLM 只能看到 512 个候选中的前 80 个，其余 432 个被 "... (432 more)"
一笔带过。LLM 无法从隐藏的候选中做有意义的选择。

```
V18 prompt（有问题）:
  ML-RANKED CANDIDATE POOL:
    GENE1 (0.823)
    GENE2 (0.791)
    ...
    GENE80 (0.621)  ← LLM能看到的最后一个
    ... (432 more candidates)  ← LLM完全不知道这些是谁
```

有效 shortlist 对 LLM 来说只有 80 个基因，不是 512 个。

---

## V19 修改（两处，均在 two-stage 路径）

### 修改 1：展示完整 shortlist

```python
# V18（有问题）
cand_lines = [f"  {g} (ML confidence: {s:.3f})" for g, s in shortlist[:80]]
if len(shortlist) > 80:
    cand_lines.append(f"  ... ({len(shortlist) - 80} more candidates)")

# V19（修复）
cand_lines = [f"  {g} (ML confidence: {s:.3f})" for g, s in shortlist]
```

### 修改 2：SHORTLIST_SIZE 512 → 384

```python
SHORTLIST_SIZE = 384   # 3 × batch_size，恢复 V12 的尺寸
```

理由：
- 384 完整展示 vs 512 截断后显示 80 → 前者信息量更大
- V12 用 384 全展示达到 0.290，这是当前最优基准
- 384 × ~30 chars/行 ≈ 12KB 附加 token，可接受

---

## 路由不变（仅 two_stage 受影响）

| 数据集 | 路由 | V19 变化 |
|--------|------|---------|
| IFNG, IL2, Sanchez21, Sanchez21_down, Carnevale22 | ml_heavy | 无 |
| **Replogle_gwps** | **two_stage** | **shortlist 512→384 且完整展示** |
| Scharenberg22, Steinhart, Replogle_essential | baseline | 无 |

---

## 预期

| 数据集 | V18 | V19 预期 | 理由 |
|--------|-----|---------|------|
| Replogle_gwps | 0.277 | **~0.285-0.290** | 完整 384 shortlist 接近 V12=0.290 |
| 其他 8 个 | 同 V18 | 同 V18 | 代码路径不变 |
| **avg** | **0.244** | **~0.242**（Sch 方差回归后） | gwps 提升，Sch 不稳定 |
