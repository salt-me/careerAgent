"""Evidence-grounded interview preparation templates."""

from __future__ import annotations

from .models import Citation, InterviewQuestion, MatchReport


QUESTION_TEMPLATES = {
    "RAG": "请结合一个知识库问答场景，说明你会如何设计文档切分、召回、重排序和引用校验，并如何评测每一层。",
    "LangGraph": "请画出你设计的工作流状态图，解释条件路由、失败降级和人工确认节点分别解决什么问题。",
    "LLM": "当模型回答与检索证据冲突或缺少依据时，你会如何限制输出并记录失败案例？",
    "Python": "请举例说明你如何将一段原型 Python 代码改造成可测试、可配置且便于排错的服务。",
    "PyTorch": "请解释训练循环中的前向计算、损失反传、优化器更新分别做什么，并举出一个常见调参问题。",
    "Transformer": "请解释 self-attention 的计算过程，以及它相比循环网络处理长文本的优势与代价。",
    "评测": "请设计一个离线评测集，并说明 Recall@k、引用正确率与端到端回答质量分别衡量什么。",
}


def build_interview_questions(report: MatchReport, limit: int = 6) -> list[InterviewQuestion]:
    priority = sorted(
        report.dimensions,
        key=lambda item: (item.status == "match", not item.required, item.skill),
    )
    questions: list[InterviewQuestion] = []
    for dimension in priority:
        question = QUESTION_TEMPLATES.get(
            dimension.skill,
            f"JD 提到了 {dimension.skill}。请结合一段真实经历说明你的理解、具体做法、遇到的问题和验证结果。",
        )
        hint = dimension.recommendation
        questions.append(
            InterviewQuestion(
                skill=dimension.skill,
                question=question,
                intent=f"验证 {dimension.skill} 是否与该岗位要求相匹配，并追问可复现的项目细节。",
                preparation_hint=hint,
                citations=report.citations[:2],
            )
        )
        if len(questions) >= limit:
            break
    return questions
