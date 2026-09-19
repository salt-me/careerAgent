from career_agent.platform.china_connectors import BaiduCampusPageConnector


def test_baidu_campus_page_connector_marks_2027_campus_jobs() -> None:
    page = '''<html>2027届校园招聘<script>{"listDetailData":[{"name":"北京-后端开发工程师(J100737)","postId":"post-1","jobId":"job-1","postType":"技术","projectType":"校招","workPlace":"北京市","updateDate":"2026-07-21","recruitNum":"10","serviceCondition":"熟悉 Python 与数据结构","workContent":"负责后端服务开发"}]}</script></html>'''
    connector = BaiduCampusPageConnector(fetch_html=lambda _: page)

    [job] = connector.fetch()
    assert job.source_name == "baidu:campus-2027"
    assert job.external_id == "post-1"
    assert job.declared_status == "open"
    assert "2027届 校招" in job.declared_group
    assert job.source_url.endswith("/post-1")
    assert connector.authoritative is False
