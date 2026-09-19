# AI Agent 秋招项目选型记录

日期：2026-07-26

## 个人背景

- 计算机专业，大三升大四，985 学校。
- 马上面临秋招。
- 已学习机器学习、深度学习相关内容，但 PyTorch 还没系统学习。
- Python 有一定基础，仍在学习中。
- 求职方向优先考虑 AI Agent 开发岗，也希望项目能兼顾大模型算法岗。
- 后续计划学习 LLM、Transformer、PyTorch、Agent、RAG、LangChain 等内容。
- 当前诉求是尽快准备一个能写进简历、能实际讲清楚、难度适中的 AI Agent 项目。

## 项目选择原则

项目不宜只是简单跑通别人的 demo，也不宜选择过于研究型、工程量过大的项目。

更合适的路线是：

- 选择一个成熟开源项目作为学习和改造底座。
- 保留多 Agent、RAG、LangChain/LangGraph 等核心技术栈。
- 改造成和自己背景、求职场景更贴近的垂直应用。
- 增加少量差异化功能，例如评测、反馈优化、答案校验、Web 界面。
- 简历中强调“基于开源项目学习并重构/扩展”，避免把完全照搬的项目说成原创。

## 推荐主方向

最终推荐方向：

**CareerAgent：基于 LangGraph 的多 Agent 秋招求职与岗位匹配系统**

这个方向结合了“校园就业助手”和“企业知识库客服”的优点：

- 业务动机自然，和个人秋招背景高度相关。
- 数据容易准备，例如岗位 JD、公司资料、面经、简历、课程资料、论文 PDF。
- 技术栈能覆盖 AI Agent 岗位常见要求。
- 项目可以讲 RAG、Agent 路由、工具调用、评测、反馈优化。
- 相比金融研报助手，不容易被追问到超出当前知识储备的金融专业问题。

## 三个改造方向对比

| 方向 | 改动难度 | 和个人背景匹配 | 面试好讲 | 算法感 | 实用性 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| 校园就业/科研助手 | 中低 | 很高 | 很高 | 中 | 高 | 最推荐 |
| 企业知识库客服 | 中 | 中高 | 高 | 中 | 很高 | 技术架构值得借鉴 |
| 金融研报分析助手 | 中高 | 中 | 中 | 较高 | 高 | 不建议作为第一项目 |

### 校园就业/科研助手

可替换的数据包括：

- 校招岗位 JD
- 公司招聘要求
- 往年面经
- 个人简历
- 论文、PDF、课程资料
- 实验室招生信息或科研方向介绍

可设计的 Agent：

- Planner Agent：拆解用户问题。
- Retriever Agent：检索岗位、面经、论文资料。
- Resume Match Agent：分析简历和岗位匹配度。
- Interview Agent：生成针对性八股题、项目追问和面试建议。
- Critic Agent：检查回答是否有引用、是否跑题、是否存在幻觉。

### 企业知识库客服

可替换的数据包括：

- 公司产品文档
- FAQ
- 售后政策
- 操作手册
- 工单记录
- 模拟数据库中的订单或用户状态

适合作为技术架构参考，因为真实 AI Agent 开发岗中大量工作都与企业知识库、客服、工单、内部助手相关。

### 金融研报分析助手

可替换的数据包括：

- 公司年报
- 研报 PDF
- 财报数据
- 新闻公告
- 股票行情
- 行业报告

优点是听起来更像大模型算法或金融科技项目，但金融专业门槛较高，容易被追问估值、财务指标、行业分析等内容。当前阶段不建议作为主项目。

## 两个 GitHub 项目对比

讨论过的两个仓库：

- [ro-anderson/multi-agent-rag-customer-support](https://github.com/ro-anderson/multi-agent-rag-customer-support)
- [liangdabiao/langgraph_multi-agent-rag-customer-support](https://github.com/liangdabiao/langgraph_multi-agent-rag-customer-support)

结论：

- `ro-anderson/multi-agent-rag-customer-support` 更适合作为主学习和改造底座。
- `liangdabiao/langgraph_multi-agent-rag-customer-support` 更适合作为中文参考和功能扩展灵感来源。

| 对比项 | ro-anderson 原版 | liangdabiao 版本 |
| --- | --- | --- |
| 来源关系 | 原始项目 | fork 自 ro-anderson |
| 文档语言 | 英文 | 中文 |
| 核心场景 | 旅行客服 | 旅行客服 + WooCommerce 商城 |
| 项目结构 | 更干净，适合学习主干 | 功能更多，但更杂 |
| Agent 能力 | 航班、租车、酒店、行程等 | 增加商城、表单、博客搜索等能力 |
| RAG/向量库 | Qdrant + travel database | Qdrant + FAQ 等扩展 |
| Web 界面 | 主要是命令行 | 增加 web_app |
| 安全机制 | 敏感工具需要用户确认 | 增加越狱防护、相关性检查、人工审核 |

## 推荐实施路线

第一阶段：先学习 ro-anderson 原版

- 理解 LangGraph 状态图。
- 理解 Primary Assistant 如何做任务路由。
- 理解 Specialized Assistants 如何分工。
- 理解 safe tools / sensitive tools 的设计。
- 理解 RAG 和 Qdrant 如何接入。

第二阶段：将业务场景改成求职助手

- 把旅行客服数据替换成岗位 JD、面经、简历、公司资料。
- 将航班、酒店、租车等 Agent 改造成岗位匹配、简历分析、面试题生成等 Agent。
- 保留多 Agent 路由和 RAG 检索结构。

第三阶段：加入差异化功能

- 简单 Web 界面。
- 答案引用溯源。
- Critic Agent 检查答案质量。
- 基于用户点赞/点踩的反馈优化。
- RAGAS 或自定义评测集，用来评估检索和回答质量。

## 简历可写方向

项目名称示例：

**基于 LangGraph 的多 Agent 秋招求职与岗位匹配系统**

可写技术栈：

`Python / LangChain / LangGraph / Qdrant 或 Chroma / RAG / FastAPI / LLM Tool Calling / RAGAS / Feedback Optimization`

可写项目描述：

设计并实现一个面向秋招场景的多 Agent 智能求职助手，支持岗位 JD、公司资料、面经和个人简历的知识库构建。系统基于 LangGraph 构建 Supervisor Agent、Retriever Agent、Resume Match Agent、Interview Agent 和 Critic Agent，实现问题分解、知识检索、岗位匹配、面试题生成和答案可信度校验。引入 RAG 检索增强和用户反馈机制，提升回答相关性与可追溯性。

## 注意事项

- 不要在简历中声称“训练了大模型”，除非后续真的完成相关训练实验。
- 可以说“围绕大模型应用系统设计了检索增强、多 Agent 协作和反馈优化机制”。
- 如果加入 RL 内容，建议先做轻量版，例如基于用户反馈调整检索参数、rerank 阈值或 Agent 路由策略。
- 面试重点应放在系统设计、Agent 分工、RAG 流程、评测方法和个人改造点上。
