我按“准备投稿时审稿人会怎么挑问题”的标准检查了一遍。整体判断是：

> **这个工作有价值，而且结果组织得相当认真；但当前版本存在几个会直接影响 headline 结果可信度的评估设计问题。最需要先解决的是按目标数据集调参、跨实验近邻泄漏，以及若干数字和文字的不一致。**

好的方面是，你已经做了大量真正有用的消融、受控复现和负结果分析，而且所有数值都由冻结的结果文件自动生成，不是手工抄表，这一点对可复现性很好。

# 一、我认为最有价值的贡献

这项工作真正有说服力的贡献不完全是“提出了一个更强的Agent”，而是下面三点。

## 1. 跨实验监督先验非常有效

你的LOO-LightGBM不使用目标实验标签，仅利用其他实验的标签和基因特征，就已经显著超过GeneDisco式单实验主动学习和BioDiscoveryAgent式LLM选择。文档也非常诚实地指出，这应解释为：

> 跨实验标签转移很有价值，而不是“我们的Agent比他们的Agent聪明”。

这是正确且重要的判断。

相比继续设计越来越复杂的采集函数，这个结论可能更有科学价值：

[
\text{其他实验中积累的监督信号}

>

\text{只在当前实验中从零开始学习}
]

## 2. LLM更适合做验证器，而不是自由提议器

你的归因分析非常有意思：

* ML单独选择的基因命中率约14.7%；
* LLM单独引入的基因命中率约8.1%；
* ML和LLM同时认可的基因命中率约46.5%。

因此，LLM的优势不是凭空提出候选，而是对ML候选进行第二种知识来源的确认。

这个结论与当前“给LLM更多自主权”的趋势相反，反而可能成为论文最鲜明的观点：

> **LLM应该重加权一个校准良好的模型，而不是自由接管实验选择。**

## 3. 你认真报告了负结果

例如：

* 显式跨实验memory平均贡献为0；
* skill library约为0；
* runtime enrichment约为+0.003；
* tool-using agent平均比固定pipeline低0.047。

这类结果很有价值，因为它们直接挑战“工具越多、记忆越多、Agent越自主就越强”的直觉。

不过，这些负结论的表述范围需要控制，后面会谈。

---

# 二、必须优先修复的三个问题

## 问题1：当前router存在明显的目标任务调参风险

这是最严重的问题。

文档中写道，fusion routing依赖于：

* 候选池大小 (n)；
* **真实hit rate (hr)**；
* 不同数据集使用不同ML/LLM权重。

同时，feature routing是：

> “trying feature sets and keeping whatever scored best”

也就是在不同screen上尝试特征集合，再保留表现最好的配置。

按现在的描述，审稿人会认为：

1. 你知道目标screen的真实hit rate；
2. 你在目标screen上试过多个特征配置；
3. 你根据目标screen的最终结果决定使用哪个配置；
4. 然后再在同一个screen上报告性能。

这属于测试集调参，至少构成严重风险。

### 为什么hit rate也有问题

真实hit rate通常只能在完整实验做完后才知道。如果它只是由benchmark规则预先规定，例如“top 5%定义为hit”，需要明确写出：

* 使用的是协议规定的预期hit比例；
* 还是完整标签计算出的真实hit比例；
* 去除CEGv2后比例是否重新计算；
* Steinhart的0.8%是如何在实验前获得的。

如果0.8%来源于完整ground truth，那么routing直接使用了测试标签统计量。

### 推荐修正

采用真正的nested leave-one-out：

[
\text{外层：留出目标screen}
]

在剩余screen中：

* 选择feature set；
* 选择fusion权重；
* 确定routing阈值；
* 决定是否使用DepMap。

完成后锁定全部配置，再一次性评估目标screen。

更严格的做法是取消per-screen手工配置，使用：

* 一个全局固定fusion权重；
* 一个在训练screen上学习的meta-router；
* 或只依赖实验前确实可知的元数据，如pool size、扰动模态、细胞类型。

**在这个问题修复前，我不建议把平均0.256作为最终headline。**

---

## 问题2：leave-one-screen-out可能不足以阻止“近邻实验泄漏”

你的九个screen中存在多组高度相关任务：

* IFN-γ和IL-2来自同一研究与相近细胞系统；
* Sanchez21和Sanchez21-down来自同一个数据源；
* K562-Essential和K562-GWPS来自同一个Perturb-seq背景。

这些任务在leave-one-screen-out时，很可能出现：

> 测试其中一个screen时，它的近亲任务仍然留在训练集中。

数据集列表明确包含这些成对任务。

这不一定是非法泄漏，因为你的目标本来就是跨实验转移；但它会让“泛化到新实验”的含义变得模糊：

* 是泛化到真正新的生物系统？
* 还是从同一研究的姐妹任务迁移？
* 是学习通用规律？
* 还是利用两个任务之间高度重叠的hit结构？

### 必须补充的评估

至少增加三种拆分：

#### Leave-one-study-out

把同一论文、同一实验平台或同一原始数据源的所有screen一起移出训练集。

例如测试Sanchez21时，也移除Sanchez21-down。

#### Leave-one-biological-family-out

按细胞类型、表型家族或实验模态分组：

* cytokine；
* T-cell功能；
* K562 Perturb-seq；
* neuronal tau；
* lysosomal phenotype。

#### Sibling-exclusion ablation

直接报告：

| 目标screen       | 普通LOO | 排除姐妹screen |
| -------------- | ----: | ---------: |
| IFN-γ          |       |            |
| IL-2           |       |            |
| Sanchez21      |       |            |
| Sanchez21-down |       |            |
| K562-Essential |       |            |
| K562-GWPS      |       |            |

如果LOO-LightGBM在这些更严格设置下仍然强，论文的核心结论会稳固很多。

---

## 问题3：文档里有几处会被审稿人立刻抓到的矛盾

### 矛盾A：到底有没有运行BioDiscoveryAgent？

前文明确写道：

* 运行了BioDiscoveryAgent自己的no-tools agent；
* 使用Haiku 4.5；
* 修改了认证路由、parser和一个harness bug；
* 得到了0.105。

但Limitations中又写：

> “we use their data … but never ran their agent” 

这两句直接冲突。后者看起来是旧版本残留，必须删除或改成：

> We did not exactly reproduce the published BioDiscoveryAgent configuration; we ran a controlled adaptation using our backend and evaluation harness.

### 矛盾B：比较时混用了六个screen和九个screen的平均值

页面5写道：

[
0.11 < 0.187 < 0.256
]

但：

* 0.187来自与BDA共享的六个screen；
* 0.256来自全部九个screen；
* 同样六个screen上的C实际是0.217。

共享六个screen的正确层级应是：

[
\boxed{
\text{BDA controlled }0.105
<
\text{LOO }0.187
<
\text{C }0.217
}
]

相关六屏数据已经在Table 3中列出。

不能用0.187和0.256直接形成层级，否则是不同测试集合之间的比较。

### 矛盾C：GeneDisco到底比较了五个还是八个规则？

正文说：

> best-per-screen over five rules

但Table 2写的是：

> oracle over 8

需要统一。 

---

# 三、LLM“验证器”结论还需要一个关键控制实验

你现在的结论是：

* agreement组命中率46.5%；
* ML-only组14.7%；
* LLM-only组8.1%。

这个观察很强，但还不能直接证明：

> LLM的认可本身把一个ML候选变得更可信。

因为agreement组很可能本来就是ML分数最高的那一小部分基因。换句话说，存在混杂：

[
\text{LLM同意}
\longleftrightarrow
\text{ML分数特别高}
\longrightarrow
\text{高命中率}
]

LLM可能只是更容易说出那些非常显眼、同时也被ML排得很高的基因。

## 建议增加条件化分析

在控制ML分数或ML排名之后，比较LLM endorsement是否仍有额外价值。

例如按ML score decile分组：

[
P(\text{hit}\mid \text{ML decile},\text{LLM endorsed})
]

对比：

[
P(\text{hit}\mid \text{ML decile},\text{not endorsed})
]

也可以做：

* propensity matching；
* 条件logistic regression；
* 每个ML候选匹配一个分数最接近但LLM未认可的基因；
* 估计LLM endorsement带来的条件增益。

如果控制ML分数后仍然有明显提升，才可以较强地说：

> LLM提供了独立验证信号。

否则更保守的说法应是：

> ML/LLM agreement is a strong predictive marker, but its incremental value beyond the ML score remains to be isolated.

另外，agreement只有101个基因，约占全部选择的2.4%，文档已经承认其区间较宽。 建议使用按screen和seed分层的bootstrap，而不是把约4200个基因视作独立样本。

---

# 四、“reasoning vs recall”实验很有趣，但缺少一个简单基线

A1设置中，LLM看到：

* 匿名基因ID；
* 每个候选的结构特征；
* 已发现hit与non-hit的平均特征画像。

然后A1平均达到0.265，高于真实基因名A2的0.253。

这说明“名称不是必要的，结构特征足够”，很有意思。但目前还不能证明是LLM在进行独特的复杂推理。

因为一个非常简单的算法也可以：

1. 计算hit与non-hit平均特征差；
2. 根据方向对候选打分；
3. 选择最接近hit画像的基因。

建议加入以下基线：

[
s(g)=
(x_g-\mu_{\text{nonhit}})^\top
(\mu_{\text{hit}}-\mu_{\text{nonhit}})
]

或者：

* nearest centroid；
* 线性判别分析；
* logistic regression；
* 每轮重新拟合的小型线性模型；
* 基于标准化特征差的手工排序。

如果LLM仍然优于这些方法，才说明它对特征进行了超越简单线性规则的整合。

否则结论应改为：

> 结构化特征可以替代参数化基因知识；LLM是实现该映射的一种方式。

这仍然是有价值的结果，只是重点从“LLM会推理”转为“结构信息比基因名更可靠”。

---

# 五、跨实验先验需要几个“反平凡化”基线

目前LOO-LightGBM是整个结果提升的主要来源。Table 5中：

* Coreset增加0.068；
* cross-experiment prior增加0.083；
* online retraining再增加0.007～0.009；
* LLM融合增加约0.022。

所以审稿人首先会问：

> 这个跨实验模型究竟学到了什么？

尤其SHAP显示DepMap essentiality是主要特征。

它可能主要学到的是：

* 一般性essentiality；
* PPI hubness；
* “容易成为任何screen hit”的基因；
* 而不一定是表型特异的迁移。

建议增加以下基线和指标。

## 1. 其他screen中的hit频率

最简单的基线：

[
s(g)=
\frac{\text{gene }g\text{在其他screen中成为hit的次数}}
{\text{其他screen数量}}
]

如果这个基线已经接近LOO-LightGBM，就说明主要信号是通用hit propensity。

## 2. 训练screen中从未成为hit的新hit

把目标screen的hit拆为：

* **seen-hit**：在其他screen中也曾是hit；
* **novel-hit**：在其他screen中从未是hit。

分别报告发现率。

这能回答模型是否真正发现了新的表型特异性基因。

## 3. 特征家族消融

至少报告：

* intrinsic only；
* anchor-relative only；
* DepMap only；
* intrinsic + anchor，不含DepMap；
* 全部特征。

尤其需要看LOO提升是否主要由DepMap产生。

## 4. Anchor来源和泄漏审计

文档说anchor是描述screen生物学的小型seed set，anchor-relative特征是重要输入。

需要明确：

* anchor由谁选择；
* 在实验前是否可获得；
* 是否来自BDA task prompt；
* 是否利用了目标screen结果；
* anchor与目标hit的重叠；
* 删除重叠anchor后的性能；
* 随机anchor或错误anchor下性能。

如果anchor由已知机制或已发表screen结果人工整理，它可能是一种很强的privileged information。

---

# 六、当前方法是否应该叫“Agent”？

现在的C-arm实际上是：

* 固定routing；
* 固定fusion；
* online LightGBM；
* tool-less LLM；
* LLM只能对候选进行有限重加权。

而自由规划、调用工具、自己决定batch的agent版本反而显著更差。你甚至明确总结：

> constraining the LLM to a fixed fusion policy is the reason the pipeline wins. 

从严格术语上看，当前主方法更接近：

* hybrid selector；
* decision pipeline；
* ML–LLM ensemble；
* constrained experiment-design system。

而不是BioDiscoveryAgent或PerTurboAgent意义上的自主Agent。

标题中的“agent”容易让审稿人期待：

* 自主规划；
* 工具调用；
* 多步行动；
* 动态策略；
* 记忆驱动决策。

但你的核心贡献恰恰是证明“不要让LLM过度自主”。

一个更贴合结果的标题方向是：

> **Waddington: Cross-Experiment Transfer with LLM Verification for Sequential CRISPR Gene Selection**

或者：

> **Waddington: A Calibrated ML–LLM Selector for Sequential CRISPR Screens**

这样能把“受约束是优势”变成设计主张，而不是被质疑“这不算Agent”。

---

# 七、“工具会让LLM变差”的结论应缩小范围

当前实验只能支持：

> 在本文实现的工具协议、提示词、预算和九个screen上，自主tool-using agent平均不如固定fusion pipeline。

它不能直接支持更宽泛的：

> 给LLM工具通常会让系统更差。

因为只有一种task-specialized harness和有限动作：

* `ml_rank`
* `enrich`
* `finish`

工具agent性能还高度依赖：

* action schema；
* prompt；
* stopping rule；
* ML结果如何呈现；
* 是否允许覆盖强ML信号；
* 工具调用成本；
* 选择策略。

因此建议把小节标题从：

> Does giving the LLM tools help? (No.)

改为更严谨的：

> A freely planning tool-using agent underperforms the constrained fusion pipeline

这不会削弱结果，反而更可信。

---

# 八、统计报告还需要增强

目前主要是九个screen、五个seed。文档报告了均值和部分标准差，也使用了paired delta，这是正确方向。

建议补充：

* 每个方法平均hit@R5的95% bootstrap CI；
* 以screen为cluster的paired bootstrap；
* C对LOO、Online、BDA、Coreset的逐screen差异；
* leave-one-screen-out jackknife；
* median而不仅是mean；
* 胜/平/负screen数量；
* 多重比较校正。

尤其不要把每个被选择的gene当成独立样本，因为同一screen、round、seed中的选择高度相关。

---

# 九、对LLM记忆污染的处理是诚实的，但仍缺少决定性证据

你已经正确承认：

* 七个screen已公开；
* Steinhart也在2024年被BDA公开；
* 当前LLM可能在训练中见过；
* gene-name shuffle同时破坏记忆和真实生物知识，无法区分二者。

这是很好的限制说明。

但如果论文想强力主张“LLM biological knowledge improves discovery”，最好增加至少一个：

* 模型cutoff之后产生的私有screen；
* 完全未公开的内部数据；
* 隐藏基因名但提供文献时间截断后的结构信息；
* 人工构造的新组合表型；
* prospective小规模湿实验验证。

否则建议把措辞限定为：

> gene-name semantics provide useful signal

而不要直接断言这是生物推理，而非训练数据记忆。

---

# 十、我建议你现在按这个优先级修改

## P0：不解决就会影响结果有效性

1. 用nested leave-study-out重新确定feature router和fusion route。
2. 移除任何依赖目标真实hit rate的routing。
3. 增加排除姐妹screen的评估。
4. 修复BDA“运行了/没有运行”的矛盾。
5. 所有跨方法比较统一使用相同screen集合。
6. 统一GeneDisco五个/八个规则的描述。

## P1：决定论文贡献是否站得住

1. 控制ML score后检验LLM endorsement增益。
2. 为A1增加线性模型和nearest-centroid基线。
3. 加入其他screen hit-frequency基线。
4. 报告novel-hit发现率。
5. 消融anchor-relative、intrinsic和DepMap特征。
6. 增加clustered bootstrap置信区间。

## P2：增强表达和定位

1. 将论文主线从“更强Agent”改为“跨实验转移＋受约束LLM验证”。
2. 缩小“工具无用”“更多agency更差”的结论范围。
3. 重新考虑标题中的Agent。
4. 给每个router和feature配置提供实验前可获得性的说明。
5. 在方法中加入完整伪代码和一次round的可复现实例。

# 最终评价

我认为这项工作**有潜力成为一篇很有意思的论文**，尤其是这三个结论：

[
\boxed{
\begin{aligned}
&\text{跨实验监督先验是最大增益来源}\
&\text{在线适应稳定有效}\
&\text{LLM更适合作为稀疏但高精度的验证信号}
\end{aligned}}
]

但当前最需要警惕的是：

> **你的主要性能提升可能同时受到per-screen配置选择、近邻screen迁移和通用essentiality信号的影响。**

如果在锁定router、leave-study-out、novel-hit和条件化LLM归因之后，结果仍然成立，那么论文会比现在更强：它不只是又一个“LLM做基因选择”的工作，而是对**ML与LLM在序贯生物实验设计中应该如何分工**给出了较有说服力的实证答案。
