# 可直接使用的项目经历（基于当前代码与实测）

**CareerAgent：证据驱动型校招岗位匹配与面试准备系统｜个人项目** `2026.08`

技术栈：`Python · LangGraph · FastAPI · Pydantic · 稀疏检索 · 重排序 · pytest · Uvicorn`

- 基于 LangGraph 构建 `input_validation → match_agent → interview_agent → critic` 条件工作流，将匿名简历与岗位 JD 解析为 16 个可审计技能维度，并以 `match / partial / missing_evidence` 表达结论，避免把“简历未写”误判为能力缺失。
- 实现本地稀疏召回与技能重排序，为匹配结论和面试追问返回简历、JD 与知识库原文片段；设计确定性 Critic 校验输入引用、维度依据、问题引用及“保证 offer”等过度承诺。
- 使用 FastAPI + Pydantic 提供岗位匹配、面试准备、反馈与健康检查接口，返回节点 trace、请求 ID 和耗时；实现浏览器演示页并通过 Uvicorn 完成服务验证。
- 构建 12 条本地演示检索评测和 6 项自动化测试，当前 Recall@3 为 **0.9167**、MRR@3 为 **0.8750**；指标仅基于仓库内模拟语料，用作可复现的回归基线。

## 面试时必须能解释

1. 为什么只将两个业务节点设计为 Agent，而把检索和 Critic 设计为受控节点；
2. `missing_evidence` 为什么不等同于“不会”，以及如何避免简历匹配系统产生伤害性结论；
3. 稀疏召回、技能重排序、Recall@k 和 MRR 的含义；
4. Critic 的四项检查各防止了什么问题；
5. 当前语料是模拟资料的局限，以及下一步如何接入有来源记录的公开 JD、embedding、Qdrant 和人工标注评测集。
