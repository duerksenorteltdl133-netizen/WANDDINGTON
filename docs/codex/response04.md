# 对第四版审稿意见（suggest04.md）的回应与改进

> 按要求：**没有为追显著性加 seed**；recurrence 阴性结论原样保留。补齐了 5-seed 协议一致性，新增 novel-hit
> 分解（最有科学价值的一项），并把 Method 重构为"先讲无泄漏最终系统"。论文 = `docs/results_tables.tex`（26pp）。

---

## 1｜不追显著性（遵从）
- recurrence 结论保持阴性，且 5-seed 后**更明确**：见 #2。

## 2｜统一到 5 seeds（协议一致性，非救显著性）
- **补跑**（已冻结协议，`WADDINGTON_DUMP_SELECTIONS` 记录命中基因）：
  - **final clean Waddington 5-seed = 0.251**（3-seed 曾为 0.255）；vs LOO **+0.034 [0.016, 0.053]，8/0/1**；
    与 legacy routed 0.256 仍**不可区分**（−0.005 [−0.018, 0.007]）。
  - **hit-freq 先验 + online + LLM 5-seed = 0.239** vs **hit-freq-only 0.243** → 配对 **−0.004 [−0.046, 0.028]**
    （3-seed 曾为 +0.002）：仍 inconclusive，**如今点估计略为负**。
- **改**：主 Table 4 的 C 列换成 5-seed（0.251，重算高亮：IFN-γ 与 OnlineAdaptive 并列最佳；Sanchez21-dn 掉到
  第三，诚实写明）；摘要 headline 0.251；Table 5 Final 行 0.251 + seed 脚注（final=5 seeds，router 变体行=3 seeds，
  故 anchor/routing 差值在 3-seed 下读）；recurrence 段与 "What we claim" 全部更新为 5-seed 数字。
- no-anchor A1/A2/linear 暂保持 3 seeds（审稿人标为可选，且现有结果已支持 structure-sufficiency）。

## 3｜把贡献收敛为 4 点（新增 "What we claim, and what we do not" 小节）
1. 跨屏复发 + 通用 essentiality = 强可迁移先验（hit-frequency 排序即达 0.243，追平学习到的 LOO）。
2. Waddington **可靠改善它实际部署的特征先验**：LOO 0.217 → 最终 0.251，**+0.034 [0.016, 0.053]，8/9**。
3. **未证明**优于纯 recurrence 排序（同起点 +（-0.004），CI 含 0）。
4. LLM 被支持的作用是**对高置信 ML 候选的条件性验证**，非发现新生物学。

## 4｜novel-hit 分解（探索性，最有信息量）
- 新模块 `analysis/novel_hit_analysis.py`。把每屏命中分为 recurrent（在其他屏也曾命中）/ novel（从未）。
  **全体命中 65% 是 novel。**
- 结果（novel-recall / recurrent-recall）：
  - hit-frequency（纯复发）：**0.000** / 0.495 —— 结构上找不到任何 novel。
  - feature-LOO（特征先验）：**0.105** / 0.439 —— 结构特征能命中"从未复发"的基因。
  - **full Waddington：0.074 / 0.462** —— novel-recall **反而低于**裸特征先验，recurrent-recall 更高。
- **诚实结论**：online + LLM 把选择**推向 recurrent 高置信命中**、略微**远离 novel**——即 LLM 是**验证器**而非
  发现器，正好支撑 claim #4。写入正文（标注 exploratory，未在其上调参）。

## 5｜Method 重构（先讲无泄漏最终系统）
- **改**：Method 新增 "The final configuration: fixed from metadata" 小节，**先**描述最终系统——全局
  w_llm=0.2（由 metadata + 训练屏 LOO 选出）、metadata 特征策略、**完全去除 anchor-relative 特征**；把
  legacy target-aware 路由（ml_heavy/two_stage/baseline，读真实 hit rate + 含 anchor）降为一句指向 robustness
  节（Table 5）的说明；原冗长的 leakage 披露段压缩为一段。

---

**主张（最终）**：*跨屏复发与 essentiality 提供了大部分可迁移信号；Waddington 把该先验整合进一个受约束、对话式
的序贯系统并通过屏内适应 + 受约束 LLM 验证可靠地改善它，但现有九屏 benchmark 不能确立其优于纯 recurrence 排序。*
raw: `clean_headline_w0.2_5seed.json`、`hitfreq_prior_full_5seed.json`、`novel_hit_analysis.json`。
