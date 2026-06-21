# V23 计划：WaddingtonV12Arm — 修复 Steinhart 路由

**日期**：2026-06-21 | **状态**：计划中

## 改动

仅修改路由条件：将 ml_heavy 扩展到所有 n>15000 数据集。

```python
# V22（错误）
if n_genes > 15000 and 0.02 < hit_rate < 0.07:
    return "ml_heavy"

# V23（修复）
if n_genes > 15000:
    return "ml_heavy"
```

受影响数据集：
- Steinhart (n=18144, hr=0.80%): baseline(w_llm=0.40) → ml_heavy(w_llm=0.20)
- gwps: 不变（已是 ml_heavy）

特征选择与 V22 相同（essential→v1，其他→v2）。

## 预期

若 Steinhart 回到 V19 水平（0.154）：avg ≈ 0.257
