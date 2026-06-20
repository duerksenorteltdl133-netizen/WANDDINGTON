# V13 计划：WaddingtonV2Arm — 双路融合（加权集成）

**日期**：2026-06-20 | **状态**：计划中 | **里程碑**：WADDINGTON_PLAN M5 改进版

---

## V12 瓶颈诊断

V12 核心问题：**ML 候选池约束**（shortlist constraint）

```
V12 架构：
  ML top-K 候选 → LLM 从候选中选
                       ↑
                    LLM 被锁在 ML 的视野内
```

结果：LLM 无法选择不在 ML top-K 中的基因，即使那些基因才是真正的最优选择：
- Steinhart：BATF、IRF4（T 细胞耗竭抵抗）PPI 分数低，不在 ML top-K → LLM 无法选 → 0.108 vs 0.152
- Replogle_essential：核糖体亚基处于蛋白互作网络外围，ML 排名靠后 → 0.497 vs 0.550

---

## V13 修复方案：双路加权集成

**核心思路**：不约束 LLM，让 ML 和 LLM 各自独立运作，用加权分数融合。

```
V13 架构（双路并行）：

  ┌─ 信号 1：OnlineAdaptive ─────────────────────────────────┐
  │   对全量基因打分：{gene: ml_score}（0-1 概率）            │
  │   随实验进行在线重训练                                    │
  └──────────────────────────────────────────────────────────┘
                       ↓
              ┌─────────────────┐
              │  加权集成        │
              │  score(g) =     │
              │  w_ml × ml(g)  │
              │  + w_llm ×     │   ← top-batch_size 基因
              │  llm_bonus(g)  │
              └─────────────────┘
                       ↑
  ┌─ 信号 2：LLM + 跨实验记忆 ─────────────────────────────┐
  │   自由提名 batch_size 个基因（无候选池约束）              │
  │   prompt 包含：任务 + 跨实验记忆 + 已揭示反馈            │
  │   llm_bonus(g) = 1.0 if g in llm_picks else 0.0       │
  └───────────────────────────────────────────────────────┘
```

### 参数设计

```python
w_ml  = 0.6   # ML 分数权重（占优）
w_llm = 0.4   # LLM 提名权重

# 合并分数（每个未选基因）：
score(g) = w_ml × ml_score(g) + w_llm × (1.0 if g in llm_picks else 0.0)
```

**权重选择理由**：
- `w_ml=0.6`：ML 分数为连续值（覆盖全量基因），信噪比高；稍高权重保证在 ML 强数据集（IFNG/IL2）不退化
- `w_llm=0.4`：LLM 提名为 0/1 二元信号，batch_size/n_genes 通常 < 1%，需要足够大的权重才能影响排名

---

## 预期行为分析

### LLM 主导数据集（V12 受损，V13 修复）

| 数据集 | V11 LLM | V12 W | V13 预期 | 机制 |
|--------|---------|-------|---------|------|
| Steinhart | 0.152 | 0.108 | **≥0.140** | LLM 自由提名 BATF/IRF4/T-bet；ML 分数不再成为过滤器 |
| Replogle_essential | 0.550 | 0.497 | **≥0.520** | LLM 自由提名核糖体亚基；ML 给强 hit 额外加权 |
| Scharenberg22 | 0.469 | 0.435 | **≥0.455** | LLM 自由命名 ATG 基因；ML 补充 hub 基因 |

### ML 主导数据集（V12 保持好，V13 须不退化）

| 数据集 | V10 OA | V12 W | V13 预期 | 机制 |
|--------|--------|-------|---------|------|
| IFNG | 0.183 | 0.160 | **≥0.175** | ML 高权重（0.6）保持 JAK-STAT 排名；LLM 记忆（IL2/Sanchez 相关）协助 |
| IL2 | 0.314 | 0.292 | **≥0.300** | 类似 IFNG，ML 主导 |
| Replogle_gwps | **0.290** | 0.290 | **≥0.285** | V12 已是新高，需维持 |

### 双方信号一致时（潜力最大）

在 LLM 提名的基因与 ML 高分基因重叠时：
```
score(g) = 0.6 × 0.9 + 0.4 × 1.0 = 0.54 + 0.4 = 0.94  ← 超过任何单信号的最高分 0.9
```
这类基因会被**强力推到选择列表最前面**，实现超过单方法的精度。

**预期 avg hit@R5：0.235–0.255**（当前最高 OA=0.224）

---

## 实现方案

### 代码变更

#### 1. `online_adaptive_arm.py` — 新增 `all_scores()` 方法

```python
def _rebuild_ranking(self):
    self._model = self._train_model(...)
    scores = self._model.predict_proba(...)[:, 1]
    order = np.argsort(-scores)
    self._ranking = [...]
    self._scores = dict(zip(self._genes, scores.tolist()))  # 新增：存储全量分数

def all_scores(self) -> dict[str, float]:
    """Return current ML confidence scores for all genes."""
    return dict(self._scores)
```

#### 2. `llm_reasoning_arm.py` — 添加 `memory_entries` 可选参数

```python
class LLMReasoningArm(BaseArm):
    def __init__(self, ..., memory_entries: list[dict] | None = None):
        ...
        self._memory = memory_entries or []  # 新增
    
    def _build_prompt(self, round_idx):
        # 在现有 prompt 中插入 memory section（与 V12 同逻辑）
        memory_sec = self._build_memory_section()  # 新增
        ...
```

#### 3. 新增 `arms/waddington_v2_arm.py`

```python
class WaddingtonV2Arm(BaseArm):
    def __init__(self, dataset_name, batch_size,
                 memory_path=MEMORY_PATH,
                 w_ml=0.6, w_llm=0.4):
        self._online = OnlineAdaptiveArm(dataset_name, batch_size)
        
        # LLM 组件：自由提名 + 跨实验记忆
        memory = load_memory(memory_path, exclude=dataset_name)
        self._llm = LLMReasoningArm(dataset_name, batch_size, memory_entries=memory)
        
        self._w_ml = w_ml
        self._w_llm = w_llm
    
    def select(self, round_idx, revealed):
        # 获取 ML 全量分数
        ml_scores = self._online.all_scores()
        
        # 获取 LLM 自由提名（含记忆）
        llm_picks = set(self._llm.select(round_idx, revealed))
        
        # 加权合并
        combined = {
            g: self._w_ml * ml_scores.get(g, 0) +
               self._w_llm * (1.0 if g in llm_picks else 0.0)
            for g in self._online._genes
            if g not in self._selected
        }
        ranked = sorted(combined, key=combined.get, reverse=True)
        return ranked[:self.batch_size]
    
    def update(self, round_idx, revealed_new):
        self._online.update(round_idx, revealed_new)
        self._llm.update(round_idx, revealed_new)
        super().update(round_idx, revealed_new)
```

### 新增文件
```
workspace/agent/arms/waddington_v2_arm.py   # V13 C 臂
```

### 修改文件
```
workspace/agent/arms/online_adaptive_arm.py  # 新增 all_scores()
workspace/agent/arms/llm_reasoning_arm.py    # 新增 memory_entries 参数
workspace/agent/run_sequential.py            # 新增 waddington_v2 臂
```

---

## 每轮 API 调用

- V12：1 次调用（LLM 从 ML shortlist 选）
- **V13：1 次调用**（LLM 自由提名，无需第 2 次调用）

成本与 V12 相同。

---

## 验收标准

| 标准 | 目标 |
|------|------|
| avg hit@R5 > OnlineAdaptive (0.224) | avg ≥ 0.235 |
| LLM 强数据集恢复 | Steinhart ≥ 0.135，Replogle_essential ≥ 0.520 |
| ML 强数据集不退化 | IFNG ≥ 0.165，IL2 ≥ 0.295 |
| 全臂最高 | 在 ≥ 3 个数据集上为最优 |

---

## 里程碑状态

| 版本 | 内容 | avg hit@R5 |
|------|------|----------|
| V9 | Coreset A 臂 | 0.134 |
| V10 | OnlineAdaptive（在线 ML）| 0.224 |
| V11 | LLMReasoning B 臂 | 0.220 |
| V12 | WaddingtonArm（约束 LLM）| 0.221 |
| **V13** | **WaddingtonV2（加权集成）** | **预期 0.235–0.255** |
