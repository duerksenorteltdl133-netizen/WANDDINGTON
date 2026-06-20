# V8 计划：序贯 Oracle 评估框架（WADDINGTON_PLAN M1）

**日期**：2026-06-20 | **状态**：进行中 | **目标**：建立多轮序贯评估基础设施

---

## 背景与动机

V1–V7 做的是**离线一次性排名**：对全部基因排序，hit_ratio@R5 = 取前 5×batch_size 名的命中率。这等价于"第 0 轮就看完了所有实验结果"，没有任何轮次交互。

WADDINGTON_PLAN 的核心是**序贯实验设计**（sequential experiment design）：
- 每轮选 batch_size 个基因
- Oracle 揭示这批基因的真值（hit/non-hit）
- Agent 根据新信息调整下一轮策略
- 目标：N 轮内命中尽可能多的 hit 基因

V8 = WADDINGTON_PLAN **M1 里程碑**：搭建这个序贯框架，并用现有 V7 LightGBM 作为第一个 arm 接入验证。

---

## 设计

### 核心原则

1. **Oracle 严格隔离**：真值只能通过 `oracle.reveal()` 获取，任何 arm 不得直接读取数据集标签
2. **Arm 接口统一**：三臂（A/B/C）实现同一 `BaseArm.select()`，共享同一 oracle 和评估循环
3. **静态 vs 自适应**：V7 LightGBM 是静态 arm（排名一次不更新），未来 LLM arm 是自适应 arm

### 新增文件

```
workspace/agent/
├── __init__.py
├── oracle.py               # DatasetOracle：揭示机制
├── sequential_runner.py    # N 轮序贯循环 + 指标计算
├── run_sequential.py       # 入口：跑全部数据集 × arm
└── arms/
    ├── __init__.py
    ├── base.py             # BaseArm 接口
    ├── random_arm.py       # RandomArm：均匀随机
    └── static_ranker_arm.py  # StaticRankerArm：V7 LightGBM 一次性排名
```

### oracle.py

```python
class DatasetOracle:
    def __init__(self, dataset_name: str):
        # 从 lgbm_training_data.csv 加载该数据集的基因列表和标签
        # 标签只在 reveal() 时对外暴露

    def all_genes(self) -> list[str]:
        # 返回候选基因全集（不含标签）

    def reveal(self, genes: list[str]) -> dict[str, bool]:
        # {gene: is_hit}，只揭示被询问的基因

    @property
    def total_hits(self) -> int:
        # 该数据集中 hit 基因总数
```

### BaseArm 接口

```python
class BaseArm:
    def reset(self): ...

    def select(self, round_idx: int, revealed: dict[str, bool]) -> list[str]:
        # 从未选过的基因中选出下一批
        # revealed: {gene: is_hit} 到目前为止已揭示的所有结果
        # 返回长度 == batch_size 的列表

    def update(self, round_idx: int, revealed_new: dict[str, bool]):
        # 接收本轮揭示结果（静态 arm 忽略，LLM arm 用于更新策略）
```

### StaticRankerArm

- 初始化时：从 `lgbm_training_data.csv` 加载该数据集的特征，用其他 8 个数据集训练 LightGBM（LOO），对本数据集所有基因打分，生成静态排名
- `select()`：依次返回排名前 k、前 2k、... 的基因（不看 `revealed` 中的反馈）
- 这是一个**零轮次学习器**（zero-round learner）：第 0 轮的先验排名贯穿全程

### sequential_runner.py

```python
class RunResult:
    dataset: str
    arm_name: str
    batch_size: int
    n_rounds: int
    hits_per_round: list[int]        # 每轮新发现的 hit 数
    cumulative_hits: list[int]       # 累积命中数
    hit_ratio_per_round: list[float] # cumulative_hits[r] / total_hits
    auc: float                       # 归一化 AUC（面积 / 最优曲线面积）
```

---

## 数据

- **来源**：`workspace/evaluation/lgbm_training_data.csv`（已有，9 数据集 × ~13,000 基因）
- **特征列**：g1_ppi_score, hub_score_norm, archs4_coexpr, ppi_score_sum, kegg_overlap, pli_score, string_degree_norm, kegg_pathway_count_norm, reactome_pathway_count_norm
- **轮次设置**：N=5，batch_size 沿用 `BATCH_SIZES`（IFNG=128, Scharenberg22=32, ...）

---

## 预期结果

| 数据集 | Random hit@R5（期望） | StaticRanker hit@R5（期望） |
|--------|---------------------|---------------------------|
| IFNG | ~0.050 | ~0.168（= V7 LOO） |
| IL2 | ~0.050 | ~0.306 |
| Scharenberg22 | ~0.050 | ~0.449 |
| Carnevale22 | ~0.050 | ~0.048（瓶颈，接近随机） |
| 平均 | ~0.050 | ~0.217 |

StaticRanker 的 hit@R5 应与 V7 LOO avg 完全一致（同一逻辑），验证框架正确性。

---

## 里程碑验收

1. `python3 run_sequential.py` 可成功运行，输出所有 9 个数据集 × 2 个 arm 的每轮结果
2. RandomArm hit_ratio 每轮大致线性增长（≈ 批大小/候选基因数）
3. StaticRankerArm hit@R5 与 V7 LOO 数字一致（误差 < 0.005）
4. 框架接口允许未来直接接入 LLM arm（只需实现 `select()` 方法）

---

## 与 WADDINGTON_PLAN 的关系

| 里程碑 | 状态 |
|--------|------|
| M1 骨架 + Oracle | **V8（本版本）** |
| M2 A臂（Coreset/AdvBIM） | V9 |
| M3 PerTurboAgent 复现 | V10 |
| M4 B臂（通用 LLM） | V11 |
| M5 ★ 跨实验记忆 | V12 |
| M6 全面实验 + 消融 | V13 |

---

## 下一步（V9）

在 V8 框架基础上接入 **A 臂**：Coreset 采集函数（复用 GeneDisco 逻辑），实现真正的自适应选择（每轮根据已选基因更新特征空间覆盖）。
