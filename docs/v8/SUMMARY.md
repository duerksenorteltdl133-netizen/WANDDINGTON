# V8 实验报告：序贯 Oracle 评估框架（M1）

**日期**：2026-06-20 | **状态**：已完成 | **里程碑**：WADDINGTON_PLAN M1

---

## 背景

V1–V7 的评估方式是**离线一次性排名**：对全部候选基因排序，取前 5×batch_size 名计算 hit_ratio@R5。这等同于"第 0 轮就固定了所有选择"，没有轮次交互，也无法接入自适应 agent。

V8 建立了**序贯 Oracle 评估框架**，实现了真正的多轮交互：每轮选 batch_size 个基因 → Oracle 揭示真值 → 记录累积命中 → 下一轮。这是接入 LLM agent 的基础设施。

---

## 新增模块

```
workspace/agent/
├── oracle.py               # DatasetOracle：严格隔离的真值揭示机制
├── sequential_runner.py    # SequentialRunner + RunResult
├── run_sequential.py       # 入口：全数据集 × 全 arm × 多 seed
└── arms/
    ├── base.py             # BaseArm：select(round, revealed) → gene_list
    ├── random_arm.py       # RandomArm：均匀随机基线
    └── static_ranker_arm.py  # StaticRankerArm：V7 LightGBM LOO 一次性排名
```

### 关键设计决策

- **Oracle 严格隔离**：标签只通过 `oracle.reveal()` 对外暴露，任何 arm 不得直接读取
- **Arm 统一接口**：所有策略实现 `select(round_idx, revealed) → list[str]`，可直接插拔
- **静态 vs 自适应**：StaticRankerArm 忽略反馈（`update()` 无操作），LLM arm 将覆写 `update()` 实现自适应

---

## 结果

### 验收：StaticRankerArm 与 V7 LOO 完全一致

| 数据集 | Random R5 | StaticRanker R5 | V7 LOO（预期） | 一致性 |
|--------|----------|----------------|--------------|--------|
| IFNG | 0.029 | **0.168** | 0.168 | ✅ |
| IL2 | 0.031 | **0.306** | 0.306 | ✅ |
| Sanchez21 | 0.037 | **0.077** | 0.077 | ✅ |
| Sanchez21_down | 0.029 | **0.091** | 0.091 | ✅ |
| Carnevale22 | 0.024 | **0.048** | 0.048 | ✅ |
| Scharenberg22 | 0.102 | **0.449** | 0.449 | ✅ |
| Steinhart | 0.021 | **0.076** | 0.076 | ✅ |
| Replogle_K562_essential | 0.254 | **0.492** | 0.492 | ✅ |
| Replogle_K562_gwps | 0.065 | **0.247** | 0.247 | ✅ |
| **平均** | **0.066** | **0.217** | **0.217** | ✅ |

### StaticRanker vs Random 对比

- **平均 hit@R5**：0.217 vs 0.066 → **+229%**
- **AUC_norm（平均）**：StaticRanker 0.194 vs Random 0.057 → **+240%**
- StaticRanker 在所有 9 个数据集上均优于 Random
- 瓶颈数据集（Carnevale22=0.048, Steinhart=0.076）依然接近 Random，与 V7 分析一致

### 每轮命中曲线（StaticRanker）

StaticRanker 为**静态排名器**，每轮固定选择排名靠前的基因，不更新策略：

| 数据集 | R1 | R2 | R3 | R4 | R5 |
|--------|----|----|----|----|-----|
| IFNG | 0.072 | 0.105 | 0.128 | 0.148 | 0.168 |
| IL2 | 0.131 | 0.193 | 0.235 | 0.289 | 0.306 |
| Scharenberg22 | 0.143 | 0.245 | 0.347 | 0.408 | 0.449 |
| Replogle_K562_essential | 0.111 | 0.222 | 0.333 | 0.413 | 0.492 |

---

## 关键发现

1. **框架验收通过**：StaticRankerArm 的 hit@R5 与 V7 LOO 数字完全一致，证明 oracle 机制正确
2. **Random 基线符合预期**：命中率 ≈ (rounds × batch_size) / n_genes（约 0.04–0.10）
3. **接口已就绪**：任何新 arm 只需继承 BaseArm 并实现 `select()`，即可接入框架
4. **StaticRanker 的局限性已量化**：每轮 hit 增量递减（因为排名靠前的基因已被选完），而自适应 agent 理论上可以在后期轮次保持更高增益

---

## 与 WADDINGTON_PLAN 的关系

| 里程碑 | 状态 |
|--------|------|
| **M1 骨架 + Oracle** | **✅ V8 完成** |
| M2 A臂（Coreset/AdvBIM） | V9（下一步） |
| M3 PerTurboAgent 复现 | V10 |
| M4 B臂（通用 LLM） | V11 |
| M5 ★ 跨实验记忆 | V12 |
| M6 全面实验 + 消融 | V13 |

---

## 下一步（V9）

在 V8 框架基础上接入 **A 臂（Coreset）**：

- 每轮在已选基因的特征空间中计算覆盖度，选最大化多样性的下一批
- 实现 `CoresetArm(BaseArm)`：覆写 `select()` 使用 greedy k-center 算法
- 与 Random 和 StaticRanker 做三臂对比，证明数据驱动的采集函数优于/劣于先验排名
