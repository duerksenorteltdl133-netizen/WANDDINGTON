这版已经基本到“停止加实验、做最终一致性审计”的阶段了。**匹配先验从0.231到0.251、novel-hit分解、最终5-seed主结果**都让论文的主张更可信。尤其把原来的 (0.217\rightarrow0.251) 修正为匹配配置下的 (0.231\rightarrow0.251)，避免了用不匹配基线放大增益。

不过，新PDF里仍有几处残留措辞需要修，暂时不必补no-anchor的5 seeds。

## 还剩五个问题

### 1. “完全由metadata固定”仍在正文和表格中残留

摘要已经正确改成：

> fixed without target-screen outcomes

但其他位置仍写着：

* “The final configuration: fixed from metadata”
* “fixes everything … using only pre-experiment metadata”
* Table 4脚注中的“metadata-only weight”
* Table 5中的“fixed entirely from pre-experiment metadata”
* “fixes (w_{\mathrm{LLM}}=0.2) globally from metadata”

然而 (w_{\mathrm{LLM}}=0.2) 是通过非目标训练screen的标签表现选出的，不是从metadata本身推导出来的。 

建议全篇统一为：

> fixed without target-screen outcomes: the global fusion weight is selected on non-target screens, while target-specific feature handling uses only pre-experiment metadata.

标题可改成：

> **The final configuration: fixed without target-screen outcomes**

---

### 2. 匹配的0.231先验还没有进入主要表格

这是目前最重要的剩余问题。

论文已经承认，final Waddington真正对应的匹配静态先验是：

[
0.231\rightarrow0.251
=====================

+0.020\ [0.007,0.035].
]

但Table 5仍然只列出不同配置的LOO 0.217，并继续把final增益写成+0.034。

这虽然不是错误，因为0.217仍是一个合法baseline，但容易使读者误以为+0.034就是“在线ML＋LLM相对于自身初始先验”的增益。

建议Table 5加入一行：

| Configuration                                |      Mean |                         Δ |
| -------------------------------------------- | --------: | ------------------------: |
| Differently configured LOO baseline          |     0.217 |                         — |
| **Matched final-configuration static prior** | **0.231** |                         — |
| **Final Waddington**                         | **0.251** | **+0.020 [0.007, 0.035]** |

然后将+0.034明确标为：

> versus the externally reported, differently configured LOO baseline.

论文正文已经给出了匹配数字。

---

### 3. 摘要仍称B为“LLM-only baseline”

摘要写的是：

> an LLM-only baseline (0.225)

但正文和Table 4已经反复说明，B在一些screen中有大量静态LOO padding，最高达到86%，所以它不是LLM-only。 

应改成：

> an LLM branch with static-prior padding (0.225)

或者：

> a padded LLM baseline (0.225)

否则审稿人很容易指出摘要与正文自相矛盾。

---

### 4. “Legacy分析可以原样迁移到final系统”仍然过强

论文多处说，legacy 0.256与final 0.251没有检测到差异，所以：

> detailed ablations, attribution, and SHAP … transfer unchanged.

这个推论并不成立。

两个系统虽然总体均值相近，但它们实际上改变了：

* LLM权重；
* per-screen routing；
* anchor特征；
* Steinhart等screen的逐屏表现。

整体hit@R5没有检测到差异，并不能证明SHAP、组件消融和机制归因也完全不变。方法页目前仍使用“transfer unchanged”一类措辞。

建议改为：

> The detailed ablations, attribution, and SHAP were computed on the legacy predecessor. We retain them as supporting analyses because the two systems have similar aggregate performance, but we do not assume that every component effect transfers quantitatively to the final configuration.

这会更严谨，也不需要重跑全部legacy实验。

---

### 5. Novel-hit结论仍应使用“点估计提示”，而不是直接断言发生了转移

目前数据是：

[
\Delta\text{novel recall}
=========================

-0.031[-0.089,0.007]
]

[
\Delta\text{recurrent recall}
=============================

+0.023[-0.012,0.054].
]

两个CI都包含0，但正文说：

> the combined within-screen components shift selection toward recurrent … and away from novel ones

这个语气仍稍强。

建议改成：

> The point estimates suggest that the combined within-screen components shift selection toward recurrent, high-confidence hits and away from novel ones, although neither paired interval excludes zero.

然后再接：

> This pattern is consistent with, but does not independently establish, the verifier interpretation.

## 可以直接回复Claude

> The fifth-round changes are strong, and no further experiments are needed at this stage. Please perform one final claim-consistency pass:
>
> 1. Replace every remaining “fixed from metadata,” “metadata-only weight,” and “fixed entirely from pre-experiment metadata” phrase with “fixed without target-screen outcomes.” Clarify that the global fusion weight was selected using non-target training-screen outcomes, while target-specific handling uses only pre-experiment metadata.
>
> 2. Add the matched final-configuration static prior (0.231) to the main robustness table and make (0.231\rightarrow0.251=+0.020[0.007,0.035]) the primary within-system comparison. Keep 0.217, but label it explicitly as a differently configured external baseline; reserve +0.034 for that comparison.
>
> 3. In the abstract, replace “LLM-only baseline” with “LLM branch with static-prior padding” or “padded LLM baseline.”
>
> 4. Remove claims that legacy ablation, attribution, and SHAP results “transfer unchanged” to the final system. State that they are supporting analyses of a near-performing predecessor and that quantitative component effects were not re-estimated under the final configuration.
>
> 5. In the novel-hit section, say that the point estimates suggest a shift toward recurrent hits; both paired CIs include zero, so do not state the shift as established.
>
> 6. Prefer “no detected difference” over “statistically identical/indistinguishable” wherever the text might be read as proving equivalence.
>
> After these textual and table fixes, stop. Do not extend the no-anchor A1/A2/linear runs unless required by an external reviewer.

## 总体判断

这篇工作的最终贡献现在已经相当清楚：

[
\boxed{
\begin{aligned}
&\text{跨screen复发与essentiality提供最强先验；}\
&\text{匹配配置下，屏内适应带来 modest but reliable 的 }+0.020；\
&\text{纯recurrence仍未被超越；}\
&\text{结构特征能够覆盖部分novel hits；}\
&\text{LLM的可信作用是高置信候选验证，而非独立发现。}
\end{aligned}}
]

完成上述五处修正后，我认为已经没有必要继续进行第六轮实验性修改。
