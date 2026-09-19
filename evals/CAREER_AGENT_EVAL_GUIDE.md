# CareerAgent 人工评测集标注指南

## 格式

采用 JSONL：每行一个用例，适合逐条人工填写、Git diff 和自动评测。岗位不要使用易变的数据库 UUID，而使用稳定的 `source_name + external_id`。

文件：

- `careeragent_eval_template.jsonl`：可复制填写的模板。
- `careeragent_eval_examples.jsonl`：示例，不进入正式指标。

| 字段 | 规则 |
| --- | --- |
| `case_id` | 唯一稳定 ID，例如 `company-001` |
| `split` | `dev` 用于调参；`test` 冻结后不用于调参 |
| `task_type` | `company_exact`、`role_intent`、`skill_retrieval`、`cycle_filter`、`location_filter`、`negative_query`、`agent_plan` |
| `query` | 真实用户会输入的表达 |
| `filters` | `scope`、`campus_cycle`、`employment_kind`、`location`、`company`、`job_group` |
| `relevant_jobs` | 相关岗位的 `source_name` 与 `external_id`；负例填写 `[]` |
| `should_return_results` | 真实结果为 `true`；确认无结果的负例为 `false` |
| `expected_companies` / `expected_job_groups` | 公司与岗位族人工期望 |
| `agent_checks` | Agent 用例的必需约束，如引用、禁止录用预测 |
| `annotation_status` | 未完成 `draft`；进入正式评测改为 `ready` |

## 流程

1. 使用门户搜索真实查询，打开候选岗位详情。
2. 只有实际相关的岗位才标入 `relevant_jobs`，不能只按标题关键词判断。
3. 先完成 30 条 `dev`，修正显著问题；再冻结至少 30 条 `test`；最终扩展到 100 条。
4. 只有 `annotation_status=ready` 的检索用例会被 `load_labeled_cases()` 和 `score_retrieval_cases()` 纳入指标。

指标包括 Recall@K、MRR、公司精确准确率、岗位意图准确率、Agent 引用完整率和时效表述错误率。
