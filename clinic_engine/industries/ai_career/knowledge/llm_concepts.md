# 大模型技术概念精要

## 大模型架构演进

### 发展历程
- **2017**：Transformer 论文 "Attention is All You Need"
- **2018**：BERT（双向编码）、GPT-1（自回归生成）
- **2020**：GPT-3（175B 参数，涌现能力）、T5（统一文本到文本框架）
- **2022**：ChatGPT（RLHF 对齐）、LLaMA（开源高效模型）
- **2023**：GPT-4（多模态）、Claude 2（长上下文）、Mistral（MoE 架构）
- **2024**：Claude 3 系列、Gemini 1.5（超长上下文）、LLaMA 3

### 关键架构创新
- **MoE（混合专家）**：只激活部分参数，兼顾性能与效率
- **GQA（分组查询注意力）**：共享 KV 头，减少推理显存
- **RoPE（旋转位置编码）**：支持外推到更长序列
- **SwiGLU 激活函数**：比 ReLU/GELU 表现更好

## 训练数据与数据工程

### 预训练数据
- 来源：网页（Common Crawl）、书籍、论文、代码（GitHub）、百科
- 清洗流程：去重（MinHash/LSH）、质量过滤、毒性过滤、去污染
- 数据配比：代码占比提升有助于推理能力，数学数据增强逻辑能力

### 指令数据
- Self-Instruct：用模型自动生成指令数据
- Evol-Instruct：逐步增加指令复杂度
- 数据质量 >> 数据数量：1000 条高质量数据可能优于 10 万条噪声数据

### 面试关注点
- 数据污染如何检测和处理？
- 中文语料不足如何弥补？
- 多语言模型的数据配比策略？

## 推理优化技术

### 量化（Quantization）
- **INT8 量化**：模型大小减半，精度损失小
- **INT4 量化**：模型大小减少 75%，配合 GPTQ/AWQ
- **GGUF 格式**：llama.cpp 的量化格式，CPU 友好
- 量化粒度：per-tensor、per-channel、per-group

### 蒸馏（Distillation）
- 用大模型（Teacher）的输出训练小模型（Student）
- 软标签（Soft Label）包含更多信息
- DistilBERT、Phi 系列是蒸馏的典型应用

### 推理加速
- **KV Cache**：缓存已计算的 Key/Value，避免重复计算
- **Flash Attention**：IO 感知的注意力计算，减少显存读写
- **推测解码（Speculative Decoding）**：小模型猜测 + 大模型验证
- **vLLM**：PagedAttention，高效管理 KV Cache

## 多模态技术

### 视觉-语言模型
- **架构方案**：ViT 编码器 + LLM（LLaVA）、端到端训练（GPT-4V）
- **视觉编码器**：ViT、SigLIP、InternViT
- **连接器**：线性投影、Q-Former、感知器重采样器

### 音频-语言模型
- Whisper 做语音识别 → 文本 → LLM 处理
- 端到端语音对话：直接从音频波形到文本生成

### 面试关注点
- 多模态对齐的难点是什么？
- 如何处理高分辨率图像？
- 视频理解的技术路线？

## Agent 与工具使用

### Agent 核心组件
- **规划**：任务拆解（ReAct、Plan-and-Execute、ToT）
- **记忆**：短期（上下文窗口）、长期（向量数据库）、工作记忆
- **工具**：API 调用、代码执行、数据库查询
- **反思**：Self-Refine、Reflexion

### Function Calling
- OpenAI 的 Function Calling 格式
- 工具描述的 Schema 定义（JSON Schema）
- 并行调用 vs 串行调用

### MCP（Model Context Protocol）
- 标准化的工具接入协议
- 服务端-客户端架构
- 支持资源读取、工具调用、Prompt 模板

### 面试关注点
- Agent 的可靠性和错误恢复？
- 多 Agent 协作的架构设计？
- 如何评估 Agent 的能力？

## 安全与对齐

### 对齐技术
- RLHF：基于人类反馈的强化学习
- DPO：直接偏好优化
- Constitutional AI：基于规则的自我改进
- Red Teaming：红队测试发现安全漏洞

### 常见安全问题
- Prompt Injection：恶意指令注入
- Jailbreak：绕过安全限制
- 幻觉（Hallucination）：生成不存在的信息
- 数据泄露：训练数据记忆和提取

### 面试关注点
- 如何平衡安全性和可用性？
- 大模型幻觉如何缓解？
- 内容安全过滤的技术方案？
