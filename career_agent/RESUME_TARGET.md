# 简历项目经历：验收后版本

> 本文是项目目标文案。投递时只能保留已经通过 README、测试和评测验证的内容；方括号中的数值必须以实际运行结果替换。

**证据驱动型校招岗位匹配与面试准备 Copilot｜个人项目** `2026.08–2026.09`

技术栈：`Python · LangGraph · FastAPI · Qdrant · Pydantic · RAG · Rerank · Docker · pytest`

- 独立设计并实现面向校招的岗位匹配与面试准备工作流，基于 LangGraph 路由 Match、Interview 与 Critic 节点；将简历与 JD 解析为结构化 schema，以规则层输出可解释的技能/经历匹配结论。
- 实现文档清洗、切分、向量召回与 rerank 链路；将结论与原文片段、来源 URL 绑定，并使用 Citation Validator 拦截无检索依据或引用不匹配的回答。
- 构建 **[实际数量]** 条离线评测集，对比 baseline 与 rerank、引入 Critic 前后的 Recall@k、引用正确率和回答有依据率；依据失败样本调整 top-k、阈值与提示词。
- 使用 FastAPI、Docker Compose、pytest 和 trace 实现服务化交付，记录节点延迟和调用成本，形成 README、演示与复盘文档。

## 当前已验证 MVP 对应的真实文案

**证据驱动型校招岗位匹配与面试准备 Copilot｜个人项目** `2026.08`

技术栈：`Python · 标准库 HTTP API · 稀疏检索 · 可解释匹配 · unittest`

- 设计并实现岗位匹配与面试准备工作流，将简历/JD 技能证据映射为 `match`、`partial`、`missing_evidence`，避免将“简历未写”错误推断为能力缺失。
- 实现本地稀疏召回与技能重排序基线，在回答中保留简历、JD 与知识库的来源片段；增加 Critic 校验输入引用、维度依据与过度承诺。
- 构建 12 条本地演示检索评测与 4 项自动化测试，当前离线 Recall@3 为 **0.9167**、MRR@3 为 **0.8750**（模拟语料基线）。
- 提供零依赖浏览器演示、JSON API、节点耗时 trace 与可复现运行命令。
