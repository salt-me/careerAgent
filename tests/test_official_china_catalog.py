from career_agent.platform.official_china_catalog import china_source_catalog


def test_user_supplied_employer_sources_use_public_career_pages_only() -> None:
    sources = {item["company"]: item for item in china_source_catalog()}

    expected_companies = {
        "华为",
        "OPPO",
        "Bambu Lab",
        "百度",
        "拼多多集团",
        "DJI 大疆",
        "智元机器人",
        "普渡科技",
        "科大讯飞",
        "Ubiquant",
        "Shopee",
        "JoinQuant",
        "NVIDIA",
        "联想",
        "腾讯音乐娱乐集团",
    }
    assert expected_companies <= sources.keys()

    for company in expected_companies:
        source = sources[company]
        assert source["trust_basis"] == "employer_owned_official_domain"
        assert "personal" not in source["career_url"]
        assert "deliver" not in source["career_url"]
        assert "share_token" not in source["career_url"]
        assert "recommendCode" not in source["career_url"]

    assert sources["百度"]["integration_status"] == "active_public_ssr"
    assert sources["百度"]["lifecycle_mode"] == "non_authoritative"
    assert sources["拼多多集团"]["integration_status"] == "active_public_api"
    assert sources["拼多多集团"]["lifecycle_mode"] == "non_authoritative"
    assert sources["Shopee"]["integration_status"] == "active_public_api"
    assert sources["Shopee"]["lifecycle_mode"] == "authoritative"
    assert sources["JoinQuant"]["lifecycle_mode"] == "authoritative"
    assert sources["NVIDIA"]["lifecycle_mode"] == "authoritative"
    assert sources["联想"]["integration_status"] == "active_public_api"
    assert sources["联想"]["lifecycle_mode"] == "authoritative"
    assert sources["华为"]["integration_status"].endswith("review_pending")
