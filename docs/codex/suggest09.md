这次已经把**主要科学问题和主线问题都解决了**。尤其摘要现在直接突出：

[
0.231\rightarrow0.251,\qquad +0.020[0.007,0.035]
]

并同时承认换成纯hit-frequency先验后，完整系统并未超过recurrence；这与全文最终结论已经一致。

而且改用渲染后PDF文本审计，而不是只grep源码，是正确的质量控制方式。

**不需要再做新实验。**不过，我核对最新PDF后，仍建议做一次很小的最终文字补丁，主要有以下几点。

## 1. Prior定义仍有轻微歧义

方法先介绍了intrinsic、anchor-relative和DepMap特征，随后明确说最终系统删除anchor，但紧接着又说LOO模型使用“the features above”。

建议改成：

> The reported LOO prior is trained using the screen-appropriate subset defined by the final feature policy: gene-intrinsic features and metadata-selected DepMap features, with no anchor-relative features.

这样读者不会怀疑0.231的最终prior究竟是否含anchor。

## 2. 方法中的 (+0.034) 仍容易被误读为内部增益

第4页仍写最终系统：

> still beats the routing-free LOO prior by +0.034

但真正匹配的内部比较是：

[
0.231\rightarrow0.251=+0.020
]

而 (+0.034) 是对不同配置的0.217外部baseline。

建议改为：

> It improves over its matched static prior by +0.020; relative to the differently configured benchmark LOO baseline, the difference is +0.034.

## 3. Prior审计段仍混用了不同screen集合

当前段落把以下数字放在一起：

* sibling-excluded：0.182，来自六个paired screens；
* no-DepMap：0.219，来自九屏；
* no-anchor：0.228，来自九屏；
* single-experiment methods约0.11，来自Table 2的六个shared screens。

这些不是同一screen集合，不能直接形成严格的数字层级。

最稳妥的处理是删除具体的跨集合比较，改成：

> Across their respective evaluation sets, all three probes leave a substantial transferable signal; matched-subset comparisons are reported separately.

或者直接利用已有逐屏JSON重算同一个六屏集合，不需要重新运行模型。

## 4. Structure部分有一句事实性表述不准确

目前写线性质心规则：

> matches, and marginally exceeds, A1’s 0.265, screen by screen

但紧接着给出的例子中：

* K562-Essential：0.587 < 0.597；
* Scharenberg22：0.571 < 0.584；
* Steinhart：0.083 > 0.065。

所以它只是**平均值略高**，并非逐屏都匹配或超过。

改为：

> It achieves a slightly higher mean than A1, with mixed per-screen differences.

同一段中的：

> the gene name is dispensable once the structure is supplied

也应与后续谨慎结论统一：

> the result is consistent with gene-name dispensability on average under this feature representation.

## 5. Appendix里仍有少量较强或口语化措辞

例如：

> textbook exhaustion regulators … that a language model knows cold



这既偏口语，也容易重新引出“知识还是记忆”的问题。建议改成：

> canonical exhaustion regulators with highly recognizable gene-name semantics.

同样，“This closes the loop”可改为：

> This offers a plausible explanation.

因为hit-set concentration假说仍被明确标记为未验证。

## 6. Tool-agent部分再收敛一点

Table 12仍称其比较对象为：

> the deterministic pipeline

但pipeline中含LLM调用，严格来说不一定是deterministic。应改成：

> the fixed-policy constrained pipeline.



结尾：

> it is the reason the pipeline wins

也最好改为：

> it appears to be the reason the pipeline wins under this tested harness.

这样与前面“一种action schema、prompt、stopping rule和budget”的范围限定一致。

## 建议直接回复Claude

> The eighth-round revision resolves the major scientific and narrative issues, and no new experiments are needed. Please make one final rendered-PDF copy-edit pass:
>
> 1. Clarify that the reported LOO prior uses only the final screen-appropriate feature subset, not all “features above.”
> 2. In Method, distinguish the matched +0.020 gain from the +0.034 comparison against the differently configured external LOO baseline.
> 3. Fix the prior-audit paragraph that mixes six-paired-screen, nine-screen, and six-shared-screen averages; either recompute a matched subset from existing outputs or remove the cross-set numeric comparison.
> 4. Replace “marginally exceeds A1 screen by screen” with “slightly higher mean, with mixed per-screen differences,” and soften the remaining “gene name is dispensable” sentence.
> 5. Replace “a language model knows cold” and “closes the loop” with neutral, memorization-compatible language.
> 6. Replace “deterministic pipeline” with “fixed-policy constrained pipeline,” and scope “the reason the pipeline wins” to the tested harness.
> 7. Replace any remaining “indistinguishable/statistically close” wording with “no detected difference” where equivalence was not tested.
>
> Then stop. No additional experiments or structural reorganization are needed.

完成这些后，我认为可以正式结束迭代。现在剩余的已经不是方法有效性问题，而是避免审稿人在最后通读时抓到**比较集合不一致、逐屏表述不准确和个别因果措辞过强**。
