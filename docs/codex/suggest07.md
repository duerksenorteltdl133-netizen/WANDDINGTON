整体判断：**不需要再补实验，但还需要最后一轮“论文主线重构＋残留措辞清理”**。

第六版已经把最重要的科学结论收敛得很准确：跨屏复发与essentiality构成强先验；相对匹配先验的增益是较小但可靠的 (+0.020)；尚未超过纯recurrence；LLM主要发挥条件性验证作用。

现在的问题已不是结果可信度，而是**标题、方法定义、主表和机制分析是否都围绕这条主线服务**。

# 一、论文真正的主线已经成立

目前最合理的论文逻辑是：

[
\boxed{
\begin{aligned}
&\text{跨实验标签中存在很强的复发与essentiality信号}\
&\downarrow\
&\text{特征化的跨实验先验能够利用该信号，并覆盖部分novel hits}\
&\downarrow\
&\text{Waddington在匹配先验上获得 modest but reliable 的增益}\
&\downarrow\
&\text{LLM的可信作用是验证高置信候选，而不是独立发现新生物学}
\end{aligned}}
]

论文最后的“What we claim, and what we do not”已经非常接近理想的结论结构：明确区分匹配先验增益、纯recurrence阴性结果和LLM验证器结论。

因此，不应再扩大主张。下一步应让全文其他部分与这四点完全一致。

# 二、仍有三处必须修正的具体残留

## 1. PDF中仍残留“statistically identical”

第六版回应说该措辞已经清除，但最新版PDF第4页仍写着：

> detailed ablations, attribution, and SHAP were computed on it (**statistically identical**)

这与前后文的“no detected difference”以及“不证明等价”的原则冲突。

直接改为：

> were computed on this near-performing predecessor and are retained as supporting analyses.

不要再加任何“identical”判断。

## 2. 伪代码仍说权重来自metadata

最新版伪代码仍写：

> Pre-experiment: ((w_{\mathrm{ML}},w_{\mathrm{LLM}})) from metadata

但权重实际上是在非目标训练screen上根据结果选择的；只有目标screen的feature policy来自metadata。

建议改成：

```text
Global fusion weight: preselected on non-target screens
Target feature policy: determined from pre-experiment metadata
```

否则正文刚刚澄清的区别，又在算法框中被模糊掉了。

## 3. 配对结果的文字与表格矛盾

最终系统的配对结果是：

* vs LOO：8/0/1
* vs Online ML：**6/1/2**
* vs LLM branch：8/0/1
* vs Coreset：9/0/0

但紧接着正文说：

> the system beats every baseline on at least 8 of 9 screens

这显然不符合对Online ML的6/1/2。

建议改成：

> All paired mean deltas are positive and their intervals exclude zero; Waddington wins on 6–9 of the nine screens, depending on the comparator.

# 三、方法部分仍应围绕“最终系统”重新整理

当前“Gene features and the cross-experiment prior”先把anchor-relative features描述成模型的正式特征，并说LOO模型使用“features above”；下一页才说明最终系统完全删除了anchor features。 

这会让首次阅读的审稿人产生困惑：

> 最终0.251的prior到底有没有使用anchor？

推荐把方法改成两层。

### 最终系统使用的特征

首先只介绍：

* intrinsic topology；
* pLI与pathway counts；
* 由metadata policy决定是否保留的DepMap；
* 明确说明不含anchor-relative features。

### 历史候选特征

随后用一小段写：

> An earlier predecessor additionally used anchor-relative features. Because an audit found that 51% of the anchors were target hits, these features are excluded from the reported system and retained only for legacy analyses.

这样读者从一开始看到的就是正式方法，而不是先学习一个稍后被撤回的版本。

# 四、legacy机制分析仍有若干过强结论

你们已经声明legacy的消融、归因和SHAP只是支撑性分析，未在final配置重估。这是正确的。但正文仍然使用了一些确定性语言。

## 1. “online retraining is the single most valuable component”

方法部分仍直接写：

> This online retraining is the single most valuable component.

但这个判断来自legacy消融，而不是final 0.251配置。

应改成：

> In the legacy predecessor’s paired ablation, removing online retraining produced the largest average loss.

## 2. “Each component provides an additive gain”

Table 6后写：

> Each component provides an additive gain.

但这并不是严格的加性分解：

* 有些行是顺序加入；
* LLM branch是平行分支；
* 比较对象并不始终相同；
* 整张表还是legacy配置。



建议改成：

> The legacy stepwise analysis suggests that the cross-experiment prior is the dominant source of performance, while online adaptation and LLM endorsement provide smaller increments under that configuration. These quantities are descriptive rather than a formal additive decomposition.

## 3. “memory无效是因为参数知识已包含它”

正文说memory贡献为零，是因为：

> the LLM’s parametric knowledge already subsumes the explicit memory entries.

实验只能证明“当前memory模块没有提高性能”，不能区分：

* 信息已被参数记忆覆盖；
* retrieval质量不好；
* prompt没有利用memory；
* memory信息本身不相关。

建议改成：

> The explicit memory module provides no measurable gain in this setup. This is consistent with redundancy with parametric knowledge, but could also reflect ineffective retrieval or use.

# 五、“生物知识”措辞仍与记忆污染限制矛盾

这是当前最值得处理的机制叙事问题。

正文Steinhart部分仍写：

> the LLM’s biological knowledge is what fills the gap

以及：

> genuinely mediated by biological gene-name knowledge



但Limitations明确承认：

> 无法区分生物知识与训练数据记忆，九个screen中没有一个真正满足训练截止时间后的干净控制。

因此这两处仍然过强。

建议改为：

> the LLM’s gene-name-conditioned parametric signal appears to fill part of the gap, although we cannot distinguish biological generalization from memorized associations.

并将小节标题：

> the clean probe of LLM biology

改成：

> a probe of dependence on gene-name semantics

“shuffle后下降”能证明系统依赖基因名语义，不能证明语义来源一定是生物推理。

# 六、主结果表最好让匹配先验更醒目

Table 5现在已经正确列出：

* differently configured LOO：0.217；
* matched final-config prior：0.231；
* final Waddington：0.251；
* 匹配增益：(+0.020[0.007,0.035])。

这一点处理得很好。

但读者最先看到的主Table 4仍然只展示0.217的LOO，而不展示0.231的匹配先验；同表中的OnlineAdapt 0.224也不是final配置下严格匹配的component ablation。

有两种处理方式：

1. 在Table 4增加一列或一行“Matched static prior 0.231”；
2. 至少在Table 4脚注明确写：

> The LOO and OnlineAdaptive columns are benchmark baselines under a different feature configuration; the matched within-system prior is 0.231 and is compared in Table 5.

否则读者仍可能把0.251−0.217理解为最终系统内部的真实提升。

# 七、标题与核心贡献仍有轻微错位

当前标题强调的是：

> **Constrained Conversational ML–LLM Agent**

但论文自己的摘要和结论明确说：

> differentiator is the cross-experiment prior, not the agent. 

这不是事实错误，但可能让审稿人觉得：

* 标题卖的是Agent；
* 实际贡献却是cross-experiment transfer；
* LLM增益很小且主要是verification；
* 纯recurrence甚至没有被超越。

最精确的标题是：

> **Waddington: Cross-Experiment Priors with Constrained LLM Verification for Sequential CRISPR Gene Selection**

你想保留agent定位，可以用折中版本：

> **Waddington: A Constrained Conversational Agent with Cross-Experiment Priors for Sequential CRISPR Gene Selection**

后者仍保留“agent”，但把真正的性能来源放进了标题。

这不是投稿前必须改，但属于影响审稿人第一印象的战略选择。

# 八、建议压缩成更清晰的主文结构

目前26页包含大量legacy router、SHAP、memory、skill、tool agent和reason-vs-recall分析。它们都很有价值，但容易掩盖主线。

建议主文只保留：

1. **问题与贡献**：为什么要跨screen迁移；
2. **最终clean Waddington**：只讲正式系统；
3. **主结果**：0.231→0.251；
4. **先验审计**：recurrence、essentiality、siblings；
5. **LLM角色**：条件化OR与top-tertile结果；
6. **novel-hit分析与边界**；
7. **Discussion / What we claim and do not claim**。

以下内容可移到附录：

* legacy target-aware router细节；
* anchor泄漏完整审计表；
  -完整SHAP；
* memory/skill完整消融；
* tool-agent逐screen表；
* A0/A0.5/A1/A2完整九屏表；
* legacy组件分解表。

主文中的一句核心总结可以定为：

> **Cross-screen recurrence and essentiality provide most of the transferable signal. Waddington instantiates this signal through a feature-based prior and modestly improves its matched implementation through a constrained sequential policy; the LLM’s supported contribution is conditional endorsement of high-confidence candidates, not discovery beyond recurrence.**

# 最终结论

**不需要第七轮实验。**

但在真正提交前，建议完成一次最后的文字与结构提交，至少修复：

1. 残留的“statistically identical”；
2. 伪代码中“weight from metadata”；
3. “at least 8 of 9”的数字矛盾；
4. legacy消融的“single most valuable/additive”过强表达；
5. “LLM biological knowledge”与memorisation limitation的冲突；
6. 主Table 4对匹配0.231先验的标注。

完成后，论文的结果、方法、标题和结论才会真正围绕同一条主线，而不是“最终系统已经很克制，但部分legacy文字仍讲着更强的旧故事”。
