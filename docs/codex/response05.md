# 对第五版审稿意见（suggest05.md）的回应与改进

> 全部为一致性/表述精度修正 + 三项**确定性重算**（无新 LLM 实验；no-anchor 5-seed 按要求推迟）。
> recurrence 阴性与 novel-hit 分解**原样保留**。论文 = `docs/results_tables.tex`（26pp，编译干净）。

## 最重要的两处表述

- **#1 不把"相似"说成"等价"**：摘要与 reason-vs-recall 中的 "matches" → "**yields similar mean
  performance … with no detected difference**"，并注明 "structure vs names 配对 −0.007 [−0.041, 0.029]
  **does not establish formal equivalence**"；结论改为 "**consistent with structure-sufficiency**"，
  linear-centroid 同样处理（"does about as well as the LLM"）。
- **#2 "完全由 metadata 固定"不准确**：摘要+Method → "**fixed without target-screen outcomes**: a global
  fusion weight selected on non-target screens, a metadata-only target feature policy, and no privileged
  anchor features"（全局权重用了训练屏标签，非目标屏，无泄漏但不是"metadata only"）。

## 数字/一致性

- **#3** Method 残留 "paired **−0.001**" → **−0.005 [−0.018, 0.007]**（5-seed）。
- **#4** 主文配对稳健表**重算为最终 5-seed 系统**（`final_system_stats.py`）：vs LOO **+0.034 [.016,.053]
  8/0/1**、vs Online **+0.027 [.007,.049] 6/1/2**、vs LLM **+0.026 [.003,.052] 8/0/1**、vs Coreset
  **+0.117 [.056,.185] 9/0/0**——全部排除 0；表头/说明改为 final，不再是 legacy 0.256。
- **#7 匹配 comparator**：验证发现"0.217→0.251"用的是**非匹配** LOO。**匹配的 no-anchor-metadata LOO =
  0.231**，故 claim #2 改为 "**matched final-configuration prior 0.231 → 0.251 = +0.020 [0.007, 0.035]，
  7/9**"（仍排除 0，但比 +0.034 诚实地小）；0.217 保留为"differently-configured LOO baseline"。
- **#5 主图**：`data.load_methods(final=True)` 把 waddington_c 换成最终 5-seed 运行；**Figures 1–3 现在画
  final 0.251**（不再是 legacy 0.256），图注改写；legacy 的 ablation/attribution/SHAP 图注加
  "**legacy configuration analysis**"；Table 6 行改 "(C, legacy)"。

## Novel-hit（#6，保留但不过度归因）

- 加了**配对屏级 CI**：Waddington vs feature-LOO 的 **novel-recall −0.031 [−0.089, 0.007]**（6/9 更低，
  CI 勉强含 0）、**recurrent-recall +0.023 [−0.012, 0.054]**。
- 措辞：强调是 online+LLM 的**组合**，"**does not isolate** whether online ML or the LLM causes the shift"；
  "consistent with the LLM acting as a verifier"（未用"confirms"）；"finds none **by construction**" →
  "**found none in these runs**, as every novel gene receives a zero recurrence score"。

## #8
- Steinhart："its advantage **cannot be cleanly attributed to the LLM alone**"（43% padding 是 confound，
  不否定真实 LLM 部分）。

---

**当前主张（未变，更精确）**：复发 + essentiality 是极强跨实验先验；结构特征能发现复发排序覆盖不到的新命中；
但完整系统更偏向可靠复发命中而非 novel discovery；LLM 的可信作用是高置信候选的条件性验证。最终 0.251 系统在
无目标统计量、无 privileged anchor 的协议下成立；相对**匹配**先验的屏内增益为 +0.020 [0.007, 0.035]。
raw: `final_system_stats.json`。
