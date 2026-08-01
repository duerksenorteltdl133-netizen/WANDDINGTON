# 对第九版审稿意见（suggest09.md）的回应与改进

> 最终 copy-edit（无实验、无结构调整）。逐条按**渲染后 PDF** 审计：7 个旧措辞全部清零，替换全部到位。
> 审稿人判定至此可正式结束迭代。

1. **Prior 定义消歧**："trained … using the features above" → "trained … using the **screen-appropriate
   subset defined by the final feature policy: gene-intrinsic features and metadata-selected DepMap
   features, with no anchor-relative features**"。读者不会再怀疑 0.231 的最终 prior 是否含 anchor。
2. **区分 +0.020 与 +0.034**：方法页由 "still beats the routing-free LOO prior by +0.034" 改为 "**It improves
   over its matched static prior by +0.020; relative to the differently-configured benchmark LOO baseline
   the difference is +0.034**"。
3. **Prior-audit 段落不再跨集合堆叠**：sibling-excluded 0.182（6 paired）、no-DepMap 0.219（9）、no-anchor
   0.228（9）、single-experiment ~0.11（6 shared）分属不同 screen 子集，改为 "across their respective
   evaluation sets … leave a substantial transferable signal; because these are measured on different screen
   subsets, we do not read them as a single numeric hierarchy against the ~0.11 single-experiment methods"。
4. **Structure 段事实修正**："matches, and marginally exceeds, A1's 0.265, screen by screen" →
   "**a slightly higher mean than A1's 0.265, with mixed per-screen differences**"（例中 K562-Ess/Scharenberg22
   实为线性 < A1）；"the gene name is dispensable once the structure is supplied" → "**consistent with
   gene-name dispensability on average under this feature representation**"。
5. **Appendix 口语/过强**："a language model knows cold" → "**canonical exhaustion regulators with highly
   recognizable gene-name semantics**"；"This closes the loop" → "**This offers a plausible explanation**"
   （hit-set concentration 假说仍标注未验证）。
6. **Tool-agent 收敛**："the deterministic pipeline" → "**the fixed-policy constrained pipeline**"（pipeline
   含 LLM 调用，非严格 deterministic）；"it is the reason the pipeline wins" → "**it appears to be the reason
   … under this tested harness (one action schema, prompt, stopping rule, and budget)**"。
7. **"statistically close" → "no detected difference"**（附录引言，未测等价处不用"接近/一致"）。

**验证**：clean build（删 aux/log/pdf 重编两遍，无 undefined refs、无 >100pt overfull，26pp）+ 对
`pdftotext` 渲染文本审计——`features above / routing-free LOO prior by / stays well above / marginally /
gene name is dispensable once / knows cold / closes the loop / deterministic pipeline / it is the reason
the pipeline wins / statistically close` 全部 = 0；替换文本（matched +0.020 / different screen subsets /
slightly higher mean / canonical exhaustion regulators / plausible explanation / fixed-policy constrained
pipeline / tested harness / no detected difference）均在对齐后的渲染文本中确认存在。

**迭代结束。** 八/九两轮已从"研究日志"收敛为围绕单一清晰主张（cross-experiment recurrence 强先验 → 匹配配置下
+0.020 屏内增益 → 未超过纯 recurrence → LLM 条件性验证）组织的投稿稿。
