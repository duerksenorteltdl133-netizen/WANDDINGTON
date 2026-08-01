这次战略方向是对的：**标题已经与真实贡献对齐，附录重排也改善了主线**。新的标题同时保留了“agent”定位，并把真正的性能来源——cross-experiment priors——放到了标题中。

但我核对了最新PDF后，结论是：

> **还不能直接结束。不是要补实验，而是回应信与实际PDF仍有若干不一致，并且摘要和正文结构还没有完全围绕最终主张收敛。**

## 一、回应信说已修，但PDF里仍存在的残留

这说明可能是源文件某处分支、缓存或重新编译版本没有完全同步。

### 1. “statistically identical”仍然存在

PDF第4页仍写：

> detailed ablations, attribution, and SHAP were computed on it (**statistically identical**).



这与回应信中“grep确认已无此措辞”直接矛盾。应改成：

> were computed on this near-performing predecessor and are retained as supporting analyses.

### 2. “single most valuable component”仍然存在

方法第3页仍写：

> This online retraining is the single most valuable component.



虽然第16页已经改成了更谨慎的：

> In the legacy predecessor’s paired ablation, removing online retraining produced the largest average loss.

但方法中的旧句仍需同步替换。

### 3. Memory的过强解释仍在详细段落中

Table 6附近已经加入了谨慎解释，但下一页仍写：

> The LLM’s parametric knowledge already captures the biological context … making the explicit memory module redundant … correctness was never the bottleneck.



这个结论仍然超过实验能支持的范围。应统一改成：

> The explicit memory module provided no measurable gain in this setup. This may reflect redundancy with parametric knowledge, but ineffective retrieval, presentation, or use cannot be excluded.

### 4. 附录SHAP部分重新出现“LLM的T-cell biology填补空白”

附录仍写：

> the LLM’s T-cell biology is what fills the gap.



但正文与Limitations已经明确说无法区分generalization和memorization。这里应统一为：

> a gene-name-conditioned parametric signal appears to fill part of the gap, although its origin cannot be distinguished from memorized associations.

### 5. Tool-agent表仍称“LLM reasoning”

附录Table 12说明中写：

> the pipeline fuses online ML with LLM reasoning under a fixed policy.



应改成：

> online ML with constrained LLM endorsement

否则又回到了已经撤回的“LLM reasoning”表述。

---

## 二、摘要还没有突出论文现在最核心的结果

目前摘要强调了：

* final hit@R5 = 0.251；
* cross-screen prior优于GeneDisco/BDA；
* verifier OR；
* tools/memory；
* structure-sufficiency。



但当前论文最关键、最匹配的两个结果反而没有在摘要中明确出现：

[
\text{matched prior }0.231
\rightarrow
\text{Waddington }0.251
=======================

+0.020[0.007,0.035]
]

以及：

[
\text{hit-frequency only }0.243
\quad\text{vs.}\quad
\text{hit-frequency + online + LLM }0.239
]

也就是：**系统可靠改善其实际部署的特征先验，但没有证明超过纯recurrence。**

这两点已经成为论文最后“What we claim”部分的核心。

建议摘要压缩tools、memory和structure-sufficiency的篇幅，加入一句：

> Against its matched static prior, Waddington improves hit@R5 from 0.231 to 0.251 (+0.020, 95% CI [0.007, 0.035]); however, replacing that prior with pure cross-screen hit frequency yields no advantage over recurrence alone (0.239 vs. 0.243).

这样标题、摘要、主表和结论才能真正一致。

## 三、Table 5的比较列仍然容易误读

Table 5目前的列名是：

> (\Delta) vs. LOO

但同一列实际上使用了多个不同reference：

* final Waddington对0.231 matched prior；
* legacy和router variants对0.217 external LOO；
* full LOSO对0.199 sibling-excluded LOO。



虽然脚注解释了，但审稿人很容易误读。

更清楚的结构是：

| Configuration    |  Mean |                    Reference | Paired Δ [CI] | W/T/L |
| ---------------- | ----: | ---------------------------: | ------------: | ----: |
| Final Waddington | 0.251 |          Matched prior 0.231 |    +0.020 […] | 7/0/2 |
| Legacy routed C  | 0.256 |           External LOO 0.217 |    +0.039 […] | 9/0/0 |
| Full LOSO        | 0.239 | Sibling-excluded prior 0.199 |    +0.041 […] | 7/0/2 |

至少应将列名改为：

> **Paired Δ vs. stated reference**

而不是统一称为“vs. LOO”。

## 四、是否继续把Tables 6–7移到附录？

我的建议是：**继续移动，但不必把reason-vs-recall的Table 8移走。**

目前主文第15–16页仍然用了两整页展示：

* legacy stepwise decomposition；
* legacy逐screen component ablation；
* memory；
* padding混杂；
* Steinhart；
* gene-name shuffle。

 

Claude说保留它们是为了连接reason-vs-recall，这个理由有一定道理，但并不需要保留完整的两张逐屏表。

### 最好的折中

主文保留一个短小的“Legacy evidence motivating the structure probe”段落：

> In the legacy predecessor, removing online retraining produced the largest average loss, while the LLM-branch ablation was strongly confounded by static-prior padding. Gene-name shuffling reduced average performance by 0.010 and by 0.084 on Steinhart, motivating the controlled structure-versus-name experiment below. Full component tables are reported in Appendix X.

然后：

* 将Table 6移到附录；
* 将Table 7及memory、padding逐屏讨论移到附录；
* 主文直接进入“Reasoning vs. recall”；
* 保留Table 8，因为structure-sufficiency是摘要中的正式结论；
* 保留conditional endorsement的Tables 9–10，因为它支撑LLM verifier的核心主张。

这样不会破坏叙事桥梁，还能让主文减少约2页。

## 五、Reason-vs-recall部分仍有两句过强

无anchor实验已经正确写了：

> similar performance；CI does not establish equivalence.

但紧接着仍写：

> the gene name remains dispensable

以及：

> impossible on the one screen where biology is doing real work.



这两句比统计证据更强，也重新引入“biology vs memorization”的问题。

建议改成：

> These results are consistent with gene-name dispensability on average under the tested feature representation.

以及：

> Steinhart is the clearest exception, where the available structural features do not recover the benefit associated with gene-name semantics.

不要写“biology is doing real work”，因为你们无法区分知识泛化与记忆。

## 六、标题脚注需要随附录重排一起调整

标题脚注仍称：

> the paper’s central finding (§ “a freely planning tool-using agent underperforms”) is that this constraint is what makes it work.



但这一节现在已经被移到附录，而且论文主结论已明确是cross-experiment prior，而不是tool-agent负结果。

应改成：

> Supporting experiments further show that, under the tested action schema and budget, a freely planning tool-using variant underperforms the constrained policy (Appendix X).

不要继续称其为“central finding”。

# 建议回复Claude

> The title and appendix strategy are correct, and no new experiments are needed. However, the current PDF still contains several residual phrases that the response letter says were removed. Please perform one final source-to-PDF audit:
>
> 1. Remove the remaining “statistically identical” on the Method page.
> 2. Replace the remaining Method sentence calling online retraining “the single most valuable component.”
> 3. Soften the detailed memory paragraph that still claims parametric knowledge makes memory redundant and that correctness was never the bottleneck.
> 4. Replace the Appendix claim that “the LLM’s T-cell biology fills the gap” with gene-name-conditioned parametric signal language, consistent with the memorization limitation.
> 5. Replace “LLM reasoning” with “LLM endorsement” in the tool-agent table description.
> 6. Add the matched (0.231\rightarrow0.251) gain and the negative recurrence comparison to the abstract; these are now more central than the tools/memory result.
> 7. Redesign Table 5 so every delta names its actual reference rather than mixing three LOO references under one column.
> 8. Move the full legacy component-decomposition and per-screen ablation tables to the Appendix, but retain a concise bridge in the main text summarizing the online, padding, and gene-name-shuffle findings that motivate the reason-vs-recall analysis.
> 9. Soften “the gene name remains dispensable” and “biology is doing real work” to language consistent with the non-equivalence CI and memorization caveat.
> 10. Update the title footnote: the freely planning agent comparison is now supporting Appendix evidence, not the paper’s central finding.
>
> Then compile from a clean build directory and verify the generated PDF itself, not only grep of the source.

## 最终判断

这篇论文的实验部分已经不需要继续扩展。现在只剩两个目标：

1. **确保回应信与实际PDF完全一致；**
2. **让摘要和主文把0.231→0.251、未超过recurrence、LLM conditional verification放在最中心。**

附录重排建议继续做一步：移走完整legacy Tables 6–7，但保留一段简洁的叙事桥梁。这样主文才真正从“研究日志”变成一篇围绕单一清晰贡献组织的投稿论文。
