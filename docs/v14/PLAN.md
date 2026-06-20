# V14 计划：WaddingtonV3Arm — 精度自适应权重（EMA 在线估算）

**日期**：2026-06-20 | **状态**：计划中 | **里程碑**：WADDINGTON_PLAN M5 深化版

---

## V13 残余问题

V13 用固定权重（w_ml=0.6, w_llm=0.4）融合两路信号，整体 avg=0.232 为项目新高，但：

```
ML 强数据集：LLM 权重 0.4 是"税"
  IFNG:  V13=0.165 < OA=0.183  (-10%)  ← LLM 命名 TF，实际 hit 是信号适配器
  IL2:   V13=0.272 < OA=0.314  (-13%)  ← 同上
  Sanchez21/down: V13 < OA        ← LLM 表观遗传盲区

LLM 强数据集：LLM 权重 0.4 又不够
  Scharenberg22: V13=0.456 < LLM=0.469  (-3%)
```

固定权重在 9 个异质数据集上是妥协，不是最优解。

---

## V14 修复方案：EMA 精度自适应权重

**核心思路**：每轮揭示后，比较 ML 和 LLM 的实际命中精度，用指数移动平均（EMA）追踪各信号质量，下一轮按信号质量比例分配权重。

### 算法设计

```
初始化：
  ml_ema  = 0.6  # 先验（偏 ML，与 V13 一致）
  llm_ema = 0.4  # 先验

每轮 select()：
  1. 记录 ml_top_batch（ML 独立排名 top-batch_size 基因）
  2. 记录 llm_free_picks（LLM 自由提名 batch_size 基因）
  3. 计算 weighted score 并选出 batch_size 个基因（同 V13）

每轮 update(revealed)：
  1. ml_prec  = |hits ∩ ml_top_batch| / batch_size
  2. llm_prec = |hits ∩ llm_free_picks| / batch_size
  3. ml_ema  = α × ml_prec  + (1-α) × ml_ema   (α=0.9，快速收敛)
  4. llm_ema = α × llm_prec + (1-α) × llm_ema
  5. 归一化：w_ml = ml_ema / (ml_ema + llm_ema)
              w_llm = 1 - w_ml
  6. 截断：w_llm ∈ [0.10, 0.90]  ← 防极端退化
```

### 参数选择

| 参数 | 值 | 理由 |
|------|-----|------|
| α (EMA 速率) | 0.9 | 5 轮评估窗口内需快速收敛；α=0.9 使当轮观测占 90% 权重 |
| 先验 ml_ema | 0.6 | 与 V13 保持连贯，Round 0 权重与 V13 相同 |
| 先验 llm_ema | 0.4 | 同上 |
| w_llm 截断 | [0.10, 0.90] | 防止过早完全排除某一信号 |

---

## 收敛速度分析

### 案例 1：IFNG（ML 强，LLM 弱）

| 轮次 | ml_prec | llm_prec | ml_ema | llm_ema | w_ml | w_llm |
|------|---------|---------|--------|---------|------|-------|
| 初始 | — | — | 0.600 | 0.400 | 0.600 | 0.400 |
| R0 reveal | ~0.14 | ~0.04 | 0.186 | 0.076 | **0.71** | **0.29** |
| R1 reveal | ~0.14 | ~0.04 | 0.145 | 0.044 | **0.77** | **0.23** |
| R2 reveal | ~0.14 | ~0.04 | 0.131 | 0.040 | **0.77** | **0.23** |

→ 从 Round 1 起 w_ml≈0.77，接近纯 ML（期望恢复接近 OA=0.183）

### 案例 2：Steinhart（LLM 强，ML 弱）

| 轮次 | ml_prec | llm_prec | ml_ema | llm_ema | w_ml | w_llm |
|------|---------|---------|--------|---------|------|-------|
| 初始 | — | — | 0.600 | 0.400 | 0.600 | 0.400 |
| R0 reveal | ~0.04 | ~0.10 | 0.096 | 0.130 | **0.42** | **0.58** |
| R1 reveal | ~0.04 | ~0.10 | 0.046 | 0.103 | **0.31** | **0.69** |
| R2 reveal | ~0.04 | ~0.10 | 0.040 | 0.100 | **0.29** | **0.71** |

→ 从 Round 1 起 w_llm≈0.69，LLM 主导（期望超过 V13=0.163）

### 案例 3：Replogle_essential（两路均强）

| 轮次 | ml_prec | llm_prec | w_ml | w_llm |
|------|---------|---------|------|-------|
| 初始 | — | — | 0.60 | 0.40 |
| R0 reveal | ~0.15 | ~0.20 | 0.42 | 0.58 |
| R1 reveal | ~0.15 | ~0.20 | 0.39 | 0.61 |

→ LLM 微弱占优，但双信号互补仍保留（期望维持 0.580+）

---

## 预期性能

| 数据集 | OA | LLM | V13 | V14 预期 | V14 vs V13 |
|--------|-----|------|-----|---------|-----------|
| IFNG | 0.183 | 0.156 | 0.165 | **~0.178** | +8% |
| IL2 | 0.314 | 0.253 | 0.272 | **~0.298** | +10% |
| Sanchez21 | 0.087 | 0.060 | 0.060 | **~0.078** | +30% |
| Sanchez21_down | 0.101 | 0.069 | 0.072 | **~0.090** | +25% |
| Carnevale22 | 0.047 | 0.058 | 0.057 | ~0.056 | -2% |
| Scharenberg22 | 0.449 | 0.469 | 0.456 | **~0.468** | +3% |
| Steinhart | 0.090 | 0.152 | 0.163 | **~0.172** | +6% |
| Replogle_essential | 0.476 | 0.550 | 0.582 | **~0.580** | -0.3% |
| Replogle_gwps | 0.273 | 0.214 | 0.258 | **~0.275** | +7% |
| **avg** | **0.224** | **0.220** | **0.232** | **~0.244** | **+5.2%** |

---

## 实现方案

### 新增文件

```
workspace/agent/arms/waddington_v3_arm.py   # V14 C 臂
```

### 核心代码结构

```python
class WaddingtonV3Arm(BaseArm):
    def __init__(self, dataset_name, batch_size,
                 memory_path=MEMORY_PATH,
                 ema_alpha=EMA_ALPHA, w_ml_init=W_ML_INIT, w_llm_init=W_LLM_INIT):
        # Sub-arms
        self._online = OnlineAdaptiveArm(dataset_name, batch_size)
        memory = load_memory(memory_path, exclude=dataset_name)
        self._llm = LLMReasoningArm(dataset_name, batch_size, memory_entries=memory)
        
        # Adaptive weight state
        self._ml_ema  = w_ml_init   # 先验精度估计
        self._llm_ema = w_llm_init
        self._w_ml    = w_ml_init
        self._w_llm   = w_llm_init
        self._ema_alpha = ema_alpha
        
        # Per-round picks (for precision tracking)
        self._round_ml_picks:  list[str] = []
        self._round_llm_picks: list[str] = []

    def select(self, round_idx, revealed):
        ml_scores = self._online.all_scores()
        
        # Record ML's independent top-batch (pure ML ranking)
        self._round_ml_picks = [
            g for g in sorted(ml_scores, key=ml_scores.get, reverse=True)
            if g not in self._selected
        ][:self.batch_size]
        
        # LLM free picks (with memory, unconstrained)
        self._round_llm_picks = self._llm.select(round_idx, revealed)
        llm_set = set(self._round_llm_picks)
        
        # Weighted combination (same as V13, but w_ml/w_llm now adaptive)
        combined = {
            g: self._w_ml * ml_scores.get(g, 0.0)
               + self._w_llm * (1.0 if g in llm_set else 0.0)
            for g in self._online._genes
            if g not in self._selected
        }
        return sorted(combined, key=combined.get, reverse=True)[:self.batch_size]

    def update(self, round_idx, revealed_new):
        hits = {g for g, is_hit in revealed_new.items() if is_hit}
        
        # Update precision EMAs
        if self._round_ml_picks:
            ml_prec = len(hits & set(self._round_ml_picks)) / len(self._round_ml_picks)
            self._ml_ema = self._ema_alpha * ml_prec + (1-self._ema_alpha) * self._ml_ema
        
        if self._round_llm_picks:
            llm_prec = len(hits & set(self._round_llm_picks)) / len(self._round_llm_picks)
            self._llm_ema = self._ema_alpha * llm_prec + (1-self._ema_alpha) * self._llm_ema
        
        # Recompute weights
        total = self._ml_ema + self._llm_ema + 1e-9
        self._w_llm = max(W_LLM_MIN, min(W_LLM_MAX, self._llm_ema / total))
        self._w_ml  = 1.0 - self._w_llm
        
        # Sub-arm updates
        self._online.update(round_idx, revealed_new)
        self._llm.update(round_idx, revealed_new)
        super().update(round_idx, revealed_new)
```

### 修改文件

```
workspace/agent/run_sequential.py  # 新增 waddington_v3 臂
```

---

## 验收标准

| 标准 | 目标 |
|------|------|
| avg hit@R5 > V13 (0.232) | avg ≥ 0.240 |
| ML 强数据集改善 | IFNG ≥ 0.175，IL2 ≥ 0.290 |
| LLM 强数据集不退化 | Steinhart ≥ 0.155，Replogle_essential ≥ 0.560 |
| Scharenberg22 恢复 | ≥ 0.462 |

---

## 里程碑状态

| 版本 | 内容 | avg hit@R5 |
|------|------|----------|
| V10 | OnlineAdaptive | 0.224 |
| V11 | LLMReasoning | 0.220 |
| V12 | WaddingtonArm（ML shortlist 约束）| 0.218 |
| V13 | WaddingtonV2（固定加权集成）| 0.232 |
| **V14** | **WaddingtonV3（EMA 精度自适应）** | **预期 ~0.244** |
