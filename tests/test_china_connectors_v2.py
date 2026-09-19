from career_agent.platform.china_connectors_v2 import BaiduCampus2027Connector
from career_agent.platform.taxonomy import classify_job


def test_baidu_official_campus_label_beats_prior_internship_experience() -> None:
    page = '''<html>2027届校园招聘<script>{"listDetailData":[{"name":"AI产品经理","postId":"post-1","postType":"产品","projectType":"校招","workPlace":"北京市","serviceCondition":"有大模型相关实习经历者优先","workContent":"负责AI产品规划"}]}</script></html>'''
    [job] = BaiduCampus2027Connector(fetch_html=lambda _: page).fetch()

    taxonomy = classify_job(job.title, job.description, job.declared_group)
    assert taxonomy.campus_cycle == "2027_campus_unspecified"
    assert taxonomy.employment_kind == "campus"
    assert job.metadata["official_description"].endswith("实习经历者优先")
