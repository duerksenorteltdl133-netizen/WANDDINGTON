# V10 计划：在线自适应 ML 臂（PerTurboAgent ML Inference 组件）

**日期**：2026-06-20 | **状态**：进行中 | **目标**：WADDINGTON_PLAN M3 部分实现

---

## 背景与范围

WADDINGTON_PLAN M3 要求复现 PerTurboAgent，其核心由三类动作组成：
- **Reasoning**：LLM 直接推理选基因（需要 Claude/GPT-4 API）
- **ML Inference**：在线训练 LightGBM，用已揭示的实验结果更新预测
- **Analysis**：GSEA / 富集分析

由于 `ANTHROPIC_API_KEY` 当前未配置，V10 先实现 **ML Inference 组件**，这是 PerTurboAgent 中唯一不依赖 LLM 的自适应模块，也是其性能增益的主要来源（论文 Figure 3b 显示 ML model 动作频率随轮次上升，是后期最重要的动作类型）。

Reasoning + Analysis 组件留待 V11（LLM 接入后）。

---

## 核心思想：在线自适应排名

```
V7 StaticRanker（V8）：   排名固定 → 每轮选排名前 k 个
OnlineAdaptiveArm（V10）：排名随实验反馈动态更新
```

**每轮流程**：
```
Round R:
  1. select()  →  选 batch_size 个基因（按当前排名）
  2. oracle.reveal()  →  获得 {gene: is_hit} 标签
  3. update(revealed_new):
       - 把 (gene, is_hit) 追加到"本实验已揭示样本"
       - 合并训练集 = LOO 训练数据（8 个历史数据集）+ 本实验已揭示样本
       - 重新训练 LightGBM
       - 重新对剩余基因打分排名
  4. 下一轮 select() 使用新排名
```

关键特点：
- **第 0 轮**：与 StaticRanker 完全相同（LOO 模型，无实验数据）
- **第 1–4 轮**：逐轮更新，命中的 hit 基因为模型提供新的正样本信号
- **不需要 LLM**，但实现了 PerTurboAgent 最核心的自适应机制

---

## 预期行为

### 对比 StaticRanker
| 阶段 | 预期差异 |
|------|---------|
| Round 1 | 相同（都用 LOO 先验，无实验数据） |
| Round 2–3 | OnlineAdaptive 略有优势（已学到本实验 hit 的特征分布） |
| Round 4–5 | 差距扩大（尤其在特征信号强的数据集） |

### 对于瓶颈数据集（Carnevale22, Steinhart）
期望影响有限：这些数据集的 hit 基因特征分散，少量揭示样本难以改变模型偏向。但若 Round 1 恰好命中几个 hit，模型可能形成正反馈。

### 预期 avg hit@R5
- 乐观：0.230–0.250（比 StaticRanker 0.217 提升 6–15%）
- 中性：0.217–0.225（微幅提升，噪声范围内）
- 悲观：0.210–0.217（首轮相同，后续改善不足以积累）

---

## 实现细节

### 新增文件
```
workspace/agent/arms/online_adaptive_arm.py
```

### 训练策略
```python
# 合并训练集：历史 LOO 数据 + 本实验揭示样本
train = pd.concat([
    loo_train_df,              # 8 个历史数据集（与 StaticRanker 相同）
    revealed_df,               # 本实验已揭示样本（gene, features, label）
], ignore_index=True)

# 增加本实验样本权重（放大已揭示样本的影响）
sample_weight = [1.0] * len(loo_train_df) + [IN_EXPERIMENT_WEIGHT] * len(revealed_df)
```

超参数：
- `IN_EXPERIMENT_WEIGHT = 10.0`（本实验样本比历史数据权重高 10×，让模型快速适应当前实验特征）
- `min_revealed_to_retrain = 10`（揭示样本不足 10 个时不重新训练，避免噪声）
- LightGBM 其余超参数与 V7 相同

### 与 StaticRankerArm 的代码共用
OnlineAdaptiveArm 继承并扩展 StaticRankerArm 的 LOO 初始化逻辑，只新增 `update()` 方法中的在线再训练。

---

## 与 WADDINGTON_PLAN 的关系

| 里程碑 | 状态 |
|--------|------|
| M1 骨架 + Oracle | ✅ V8 |
| M2 A臂（Coreset） | ✅ V9 |
| **M3 PerTurboAgent（ML Inference 组件）** | **V10（本版本）** |
| M3 PerTurboAgent（LLM Reasoning + Analysis） | V11（需要 ANTHROPIC_API_KEY） |
| M4 B臂（通用 LLM） | V12 |
| M5 ★ 跨实验记忆 | V13 |

---

## 验收标准
1. `run_sequential.py --arms online_adaptive` 可正常运行
2. Round 1 hit_ratio 与 StaticRanker 完全一致（同一 LOO 先验）
3. Round 2–5 OnlineAdaptive ≥ StaticRanker（在多数数据集上）
4. avg hit@R5：OnlineAdaptive > StaticRanker（≥ 0.217）
