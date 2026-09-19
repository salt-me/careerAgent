from career_agent.source_import import validate_records


def test_authorised_export_validation_keeps_valid_rows_and_rejects_invalid_rows() -> None:
    valid = {
        "source_name": "nowcoder",
        "source_url": "https://www.nowcoder.com/jobs/detail/example",
        "title": "后端开发工程师",
        "company": "示例科技有限公司",
        "location": "北京",
        "text": "这是来自授权导出的足够长职位摘要，用于验证批量导入时能够保留可追溯来源和岗位信息。",
        "captured_at": "2026-08-02",
    }
    invalid = {**valid, "source_url": ""}
    accepted, result = validate_records([valid, invalid])
    assert len(accepted) == 1
    assert result.accepted == 1
    assert result.rejected == 1
    assert "source_url" in result.errors[0]
