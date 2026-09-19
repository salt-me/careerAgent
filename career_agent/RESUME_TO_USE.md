# 简历项目经历（以此文件为准）

**CareerAgent：证据驱动型校招岗位匹配与面试准备系统｜个人项目** `2026.08`

技术栈：`Python · LangGraph · FastAPI · Pydantic · 稀疏检索 · 重排序 · pytest · Uvicorn`

- 基于 LangGraph 构建 `input_validation → match_agent → interview_agent → critic` 条件工作流，将匿名简历与岗位 JD 映射至 18 个可审计技能维度，并以 `match / partial / missing_evidence` 表达结论，避免把“简历未写”误判为能力缺失。
- 实现本地稀疏召回与技能重排序，为匹配结论和面试追问返回简历、JD 与知识库原文片段；设计确定性 Critic 校验输入引用、维度依据、问题引用及“保证 offer”等过度承诺。
- 使用 FastAPI + Pydantic 提供岗位匹配、面试准备、反馈与健康检查接口，返回节点 trace、请求 ID 和耗时；实现浏览器演示页并通过 Uvicorn 完成服务验证。
- 构建 12 条本地演示检索评测和 6 项自动化测试，当前 Recall@3 为 **0.9167**、MRR@3 为 **0.8750**；指标仅基于仓库内模拟语料，用作可复现的回归基线。

## 使用条件

上述文案对应当前仓库可运行的代码和实测结果。应主动说明 12 条评测语料为本地演示集，不能描述为真实线上指标或大规模公开语料效果。
