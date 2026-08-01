# 对第七版审稿意见（suggest07.md）的回应与改进

> 无新实验。做了残留措辞清理 + 主线一致性。评估结论：审稿人列的 6 条"至少修复"全部合理（其中 #1 实为
> 上一版已改、审稿人看的是旧 PDF）；两条战略性建议（标题、正文精简入附录）是可选项，留给作者决定（见末尾）。

## 六条"至少修复"

1. **残留 "statistically identical"** —— 经核对**源文件中已无此措辞**（round 6 已全部改为 "no detected
   difference"）。审稿人看到的是 v6 之前的 PDF。无需再改（已确认 grep 为空）。
2. **伪代码"权重来自 metadata"** —— 已改：`Global fusion weight: preselected on NON-target screens
   (leave-one-out)` / `Target feature policy: from pre-experiment metadata`。
3. **"at least 8 of 9" 与 Online ML 6/1/2 矛盾** —— 已改为 "All paired mean deltas are positive and their
   intervals exclude zero; Waddington wins on 6--9 of the nine screens, depending on the comparator (6/1/2
   vs Online ML, 9/0/0 vs Coreset)"。
4. **legacy 消融的过强表述**：
   - "single most valuable component" → "In the legacy predecessor's paired ablation, removing online
     retraining produced the largest average loss"（图注同步）。
   - "Each component provides an additive gain" → "This legacy stepwise analysis suggests … descriptive
     rather than a formal additive decomposition（顺序加入、LLM 是平行分支、均为 legacy 配置）"。
   - memory "parametric knowledge already subsumes it" → "no measurable gain … consistent with redundancy
     with parametric knowledge, but could also reflect ineffective retrieval or use"。
5. **"biological knowledge" 与记忆污染 limitation 冲突**：
   - "the LLM's biological knowledge is what fills the gap" → "gene-name-conditioned parametric signal
     appears to fill part of the gap, although we cannot distinguish biological generalization from
     memorized associations"。
   - "genuinely mediated by biological gene-name knowledge" → "mediated by the gene names … whether that
     name-conditioned signal reflects biological generalization or memorized associations, this ablation
     cannot say"。
   - 小节标题 "the clean probe of LLM biology" → "a probe of dependence on gene-name semantics"。
6. **主 Table 4 标注匹配先验**：$\ddagger$ 脚注新增——"LOO-LightGBM 与 OnlineAdapt 列是**不同特征配置**下的
   benchmark 基线；匹配的 within-system 先验是 0.231，故内部提升是 0.231→0.251（+0.020），而非 0.217→0.251"。

## 另做（§三，主线清晰化，light touch）
- 在"Gene features and the cross-experiment prior"里**提前声明**：最终系统只用 gene-intrinsic +
  metadata-selected DepMap 特征，**完全不含 anchor-relative 特征**（51% anchor 是本屏 hit，privileged），
  anchor 仅保留在 legacy 前身与 reason-vs-recall 探针中——"读下文的 anchor 特征时，请视为历史候选，而非最终
  先验的一部分"。避免读者先学一个稍后被撤回的版本。

## 两条战略性建议（可选，未自动执行，见对话）
- **§七 标题**：审稿人建议把 "Cross-Experiment Priors" 放进标题（保留 "agent" 的折中版）。这与作者一贯保留
  "agent" 框架的偏好相关，属主观定位选择，交由作者决定。
- **§八 正文精简入附录**：把 legacy router 细节、完整 SHAP、memory/skill 消融、tool-agent 逐屏表、
  A0/A0.5/A1/A2 九屏全表、legacy 组件分解移入附录。这是较大的结构重排，非"必修"，建议单独确认后再做。
