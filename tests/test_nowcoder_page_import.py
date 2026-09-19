from career_agent.nowcoder_page_import import _raw_record, parse_public_career_page


def test_parses_individual_public_job_cards_and_keeps_unique_id_in_source_url():
    html = """
    <div class="rec-job rec-job-fold" data-id="42">
      <h2>【示例公司】前端工程师</h2>
      <span title="工作城市：北京">北京</span>
      <span title="职位方向：前端开发">前端开发</span>
      <span title="招聘公司：示例公司">示例公司</span>
      <div class="nc-post-content js-duty-content">开发 Web 界面并持续优化性能。</div>
      <div class="nc-post-content js-duty-content">熟悉 JavaScript、React 与团队协作。</div>
    </div>
    """
    jobs = parse_public_career_page(html)
    assert len(jobs) == 1
    record = _raw_record(jobs[0], page_url="https://www.nowcoder.com/careers/nowcoder1/413", captured_at="2026-08-02")
    assert record["source_job_id"] == "nowcoder-careers-413-42"
    assert record["source_url"].endswith("jobIds=42")
    assert "JavaScript" in record["text"]
