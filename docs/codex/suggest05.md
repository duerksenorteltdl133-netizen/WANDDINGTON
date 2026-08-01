这次结果把论文的定位进一步收紧了，而且 **novel-hit 分解很有价值**：特征先验能够发现 recurrence 完全无法发现的新命中，但加入在线更新与 LLM 后，novel recall 从 0.105 降至 0.074，同时 recurrent recall 从 0.439 升至 0.462。这比单纯比较总体 hit@R5 更清楚地说明系统在优化“高置信复发命中”，而不是探索新生物学。

我暂时**不建议优先把无 anchor 的 A1/A2/linear 补到 5 seeds**。现在更需要处理的是几处统计表述与最终系统的一致性。你可以这样回复 Claude：

> The new negative recurrence result and novel-hit decomposition should remain exactly as reported. Do not add seeds to chase a stronger structure-sufficiency result yet.
>
> Before considering the paper final, please make the following consistency and claim-precision fixes:
>
> 1. **Do not describe the no-anchor structure result as equivalence unless an equivalence margin was pre-specified.** A1 (0.241) versus names (0.249), with a paired CI of ([-0.041, 0.029]), shows similar mean performance and no detected difference, but the interval still permits a practically meaningful loss. In the abstract and Results, replace “matches” with wording such as “yielded similar mean performance; we did not detect a difference.” Describe the result as “consistent with structure-sufficiency,” not proof of equivalence. Apply the same qualification to the linear-centroid comparison.
>
> 2. **Correct “fixed entirely from pre-experiment metadata.”** The target screen contributes only pre-experiment metadata, but (w_{\mathrm{LLM}}=0.2) was selected using outcomes from the non-target training screens. Use: “fixed without target-screen outcomes; the global weight is selected on non-target screens, and target-specific handling uses only pre-experiment metadata.”
>
> 3. **Fix the stale legacy comparison in Method.** The final five-seed result is (0.251) versus legacy (0.256), paired (-0.005[-0.018,0.007]), not the remaining (-0.001) value.
>
> 4. **Recompute the paired robustness table for the final five-seed Waddington.** The current paired CIs against Online ML, the LLM branch, and Coreset still refer to the legacy (0.256) configuration. Report final-system deltas, CIs, and win/tie/loss counts, or explicitly label the entire table as a legacy-only analysis and avoid using it to support claims about the final system.
>
> 5. **Regenerate the main discovery and comparison figures using final Waddington (0.251).** The current figures still display (0.256), while one caption refers readers to the updated Table 4. The principal figures should show the principal method; legacy figures can remain in an appendix.
>
> 6. **Strengthen the novel-hit analysis statistically, without tuning.** Report per-screen novel and recurrent recall, macro averages, and paired screen-level intervals for final Waddington versus feature LOO. Phrase the result as applying to the combined within-screen components; this comparison does not isolate whether online ML or the LLM individually causes the novelty reduction. Use “consistent with the verifier interpretation,” not “independently confirms it.”
>
> 7. **Confirm that the (0.217) LOO comparator uses the exact final no-anchor metadata feature policy.** If it does, label it “matched final-configuration LOO.” If not, produce the matched comparator before retaining the (0.217 \rightarrow 0.251) component claim.
>
> 8. In the Steinhart discussion, replace “the padded LLM result is not evidence of LLM reasoning” with “its advantage cannot be cleanly attributed to the LLM alone,” because 43% padding creates a confound but does not invalidate the genuine LLM portion.
>
> After these fixes, stop adding experiments unless a consistency check fails. The no-anchor A1/A2/linear five-seed extension is optional and lower priority than correcting the final-system tables, figures, and statistical language.

## 当前最重要的两处文字问题

### “完全由metadata固定”不准确

论文现在说最终系统是：

> fixed entirely from pre-experiment metadata

但紧接着又说 (w_{\mathrm{LLM}}=0.2) 是通过其他screen的leave-one-out表现选出的。也就是说：

* **目标screen的信息**确实只有实验前metadata；
* 但**权重选择**使用了训练screen标签。

这没有泄漏，但不能称为“entirely from metadata”。论文方法部分已经写出了这两个步骤，因此只需精确改写，不需要重跑。

推荐摘要写法：

> under a configuration fixed without target-screen outcomes: a global fusion weight selected on non-target screens, a metadata-only target feature policy, and no privileged anchor features.

### “CI包含0”不等于“已经证明相等”

目前无anchor结果是：

[
A1-A2=-0.007,\qquad 95%,CI=[-0.041,0.029].
]

它很好地说明之前的structure结果**不是由anchor泄漏单独制造的**，但不能严格证明两者等价。因为这个区间仍允许A1比名称条件低0.041。

因此摘要中的：

> structural features … match the real-name condition

建议改为：

> structural features yield similar mean performance to the real-name condition, with no detectable difference in this benchmark.

或更简练：

> the results are consistent with structure-sufficiency, although the uncertainty does not establish formal equivalence.

增加到5 seeds可能减少seed噪声，但只有九个screen，主要不确定性仍来自screen异质性。因此它不是最优先实验。

## 当前最明显的数字残留

方法页仍写着：

> 0.251 … indistinguishable from 0.256 (**paired −0.001**)

但最新五seed结果是：

[
-0.005[-0.018,0.007].
]

这个旧数字需要全局搜索替换。最终Table 5中的数字已经是正确的。 

## 主图最好必须更新

当前Table 4已经正确采用final Waddington 0.251，并统一为5 seeds。

但第13页的discovery curve和柱状图仍画的是legacy 0.256。虽然图注明确披露了这一点，但主图展示旧系统、主表展示新系统，会让读者不断在两个C-arm之间切换。尤其Figure 2还写着对应Table 4，却显示0.256。

建议：

* 主文Figures 1–3全部换成final 0.251；
* legacy 0.256的曲线和消融图移入附录；
* legacy的SHAP和component ablation可以保留，但标题中明确写“legacy configuration analysis”。

## Novel-hit结果值得保留，但不要过度归因给LLM

这个结果目前能够支持：

> 在线更新与LLM验证的**组合**使选择从novel hits转向recurrent high-confidence hits。

它还不能单独说明是在线ML还是LLM造成的。论文正文目前使用“consistent with the LLM acting as a verifier”，这是合适的；Claude总结里的“independently confirms”则稍强，应改掉。

此外，“hit-frequency finds no novel hits **by construction**”最好改成：

> hit-frequency found no novel hits in these runs, as every novel gene receives a zero recurrence score.

严格来说，若所有正分基因被耗尽或零分tie-breaking介入，recurrence排序并非数学上永远不可能选中novel gene。

## 总体判断

论文现在的核心发现已经很清楚，而且比最初“更聪明的LLM Agent”更有科学意义：

[
\boxed{
\begin{aligned}
&\text{复发与essentiality构成极强的跨实验先验；}\
&\text{结构特征能够发现复发排序无法覆盖的新命中；}\
&\text{但完整系统更偏向可靠复发命中，而非novel discovery；}\
&\text{LLM的可信作用是高置信候选验证，不是自由发现。}
\end{aligned}}
]

先完成上面的最终系统统计与图表一致性，再考虑是否补A1的两个seed。现阶段继续增加A1 seed带来的收益，明显小于把“相似”“等价”“最终系统”和“legacy分析”严格区分开的收益。
