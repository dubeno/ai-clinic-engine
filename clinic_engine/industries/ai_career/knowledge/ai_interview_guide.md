# 大模型面试核心知识点

## Transformer 架构

### 自注意力机制（Self-Attention）
Transformer 的核心是自注意力机制，通过 Query、Key、Value 三个矩阵实现序列中任意两个位置之间的关联建模。

计算公式：Attention(Q,K,V) = softmax(QK^T / √d_k) × V

关键点：
- 缩放因子 √d_k 防止点积过大导致 softmax 梯度消失
- 多头注意力（Multi-Head Attention）让模型关注不同子空间的信息
- 位置编码（Positional Encoding）弥补注意力机制对位置信息的缺失

### Encoder-Decoder 结构
- 编码器：将输入序列映射为隐藏表示
- 解码器：基于隐藏表示自回归生成输出
- GPT 系列只用 Decoder，BERT 只用 Encoder，T5 用完整结构

### 面试常见问题
1. 为什么用 Layer Norm 而不是 Batch Norm？
2. KV Cache 的原理和作用？
3. Flash Attention 如何优化显存和速度？

## RLHF 训练流程

### 三阶段训练
1. **SFT（监督微调）**：在高质量指令数据上微调预训练模型
2. **Reward Model 训练**：训练奖励模型评估回复质量
3. **PPO 优化**：用强化学习策略优化生成结果，使其符合人类偏好

### DPO（Direct Preference Optimization）
- 绕过显式奖励模型，直接从偏好数据优化策略
- 损失函数基于 Bradley-Terry 模型
- 训练更稳定，调参更简单

### 面试常见问题
1. RLHF 中 reward hacking 是什么？如何缓解？
2. DPO 相比 PPO 的优缺点？
3. Constitutional AI 的原理？

## RAG（检索增强生成）

### 基本流程
1. 文档切分（Chunking）→ 向量化（Embedding）→ 存入向量数据库
2. 查询时：Query 向量化 → 相似度检索 → 拼接上下文 → LLM 生成

### 关键技术
- 文档切分策略：固定长度、语义分割、递归分割
- 向量模型选择：BGE、M3E、text-embedding-ada-002
- 检索方式：稠密检索、稀疏检索（BM25）、混合检索
- 重排序（Reranking）：Cross-Encoder 提升检索精度

### 面试常见问题
1. RAG 和长上下文窗口哪个更好？
2. 如何评估 RAG 系统的效果？
3. 如何处理多模态文档的 RAG？

## 微调方法

### 参数高效微调（PEFT）
- **LoRA**：低秩分解权重矩阵，只训练少量参数
- **QLoRA**：4-bit 量化 + LoRA，单卡可微调大模型
- **Adapter**：在层间插入小型网络模块
- **Prefix Tuning**：训练可学习的前缀向量

### 全参微调 vs PEFT
- 全参微调效果上限高，但需要多卡
- PEFT 资源需求低，适合垂直领域适配
- 实际选择取决于数据量、模型大小、硬件条件

### 面试常见问题
1. LoRA 的秩 r 如何选择？
2. 微调时学习率应该怎么设？
3. 如何避免微调后的灾难性遗忘？

## Prompt Engineering

### 核心技巧
- **Few-shot**：提供 2-5 个示例引导模型理解任务
- **Chain-of-Thought（CoT）**：引导模型逐步推理
- **ReAct**：推理与行动交替进行，结合工具调用
- **Self-Consistency**：多次采样取多数结果

### Agent 架构
- 工具调用（Function Calling）：让模型使用外部 API
- 规划器 + 执行器：将复杂任务拆解为子任务
- 记忆系统：短期记忆（上下文）+ 长期记忆（向量数据库）

### 面试常见问题
1. Prompt injection 攻击如何防御？
2. 如何评估 Prompt 的效果？
3. System Prompt 和 User Prompt 的区别？

## 模型评估指标

### 常用指标
- **困惑度（Perplexity）**：衡量语言模型的预测能力
- **BLEU / ROUGE**：文本生成的自动评估
- **MMLU / C-Eval**：知识能力基准测试
- **HumanEval**：代码生成能力评估
- **MT-Bench**：多轮对话质量评估

### 评估方法
- 自动评估：基准测试、规则匹配
- 人工评估：打分、对比、标注
- LLM-as-Judge：用大模型评估大模型

### 面试常见问题
1. 如何评估一个大模型在垂直领域的表现？
2. BLEU 评分的局限性是什么？
3. 如何设计一个公平的模型对比实验？
