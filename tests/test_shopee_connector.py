import base64
import html
import json

import pytest
from Crypto.Cipher import AES

from career_agent.platform.china_connectors import (
    JoinQuantCampusConnector,
    NvidiaCampusConnector,
    ShopeeAiStarProgramConnector,
    ShopeeCampusPageConnector,
    ShopeeInternConnector,
)


_KEY = "moka-public-key1"
_IV = "moka-public-iv01"


def _public_page(site_id: str, organization_id: str = "shopee") -> str:
    payload = {
        "org": {"id": organization_id, "siteId": site_id},
        "aesIv": _IV,
        "jobsGroupedByDepartment": [{"label": "Shopee CNDC校招", "ids": [448995]}],
    }
    encoded = html.escape(json.dumps(payload, ensure_ascii=False), quote=True)
    return f'<html><input type="hidden" id="init-data" value="{encoded}"></html>'


def _encrypted_response(data: dict) -> dict:
    raw = json.dumps({"success": True, "data": data}, ensure_ascii=False).encode("utf-8")
    padding = AES.block_size - len(raw) % AES.block_size
    ciphertext = AES.new(_KEY.encode("utf-8"), AES.MODE_CBC, _IV.encode("utf-8")).encrypt(raw + bytes([padding]) * padding)
    return {"data": base64.b64encode(ciphertext).decode("ascii"), "necromancer": _KEY}


def _job(job_id: str, title: str, status: str = "open") -> dict:
    return {
        "id": job_id,
        "title": title,
        "status": status,
        "publishedAt": "2026-08-11T09:15:26.000Z",
        "mjCode": f"MJ-{job_id}",
        "deptId": 448995,
        "location": {"country": "中国", "cityId": 440300, "address": ""},
        "zhineng": {"name": "SRE"},
        "commitment": "全职",
        "projectFolder": {"name": "2027届常规秋招"},
    }


def test_shopee_public_connector_pages_complete_official_job_list() -> None:
    calls: list[dict] = []

    def fetch_json(_url: str, payload: dict) -> dict:
        calls.append(payload)
        jobs = [_job("job-1", "（27届秋招）SRE工程师-深圳"), _job("job-2", "研发工程师-深圳")]
        if payload["offset"] == 20:
            jobs = [_job("job-3", "信息安全工程师-深圳", "closed")]
        return _encrypted_response({"jobStats": {"total": 3}, "jobs": jobs})

    connector = ShopeeCampusPageConnector(fetch_html=lambda _url: _public_page("2962"), fetch_json=fetch_json)
    jobs = connector.fetch()

    assert [job.external_id for job in jobs] == ["job-1", "job-2", "job-3"]
    assert calls == [
        {"orgId": "shopee", "siteId": "2962", "limit": 20, "offset": 0, "needStat": True, "site": "campus", "locale": "zh-CN"},
        {"orgId": "shopee", "siteId": "2962", "limit": 20, "offset": 20, "needStat": True, "site": "campus", "locale": "zh-CN"},
    ]
    assert jobs[0].source_name == "shopee:campus-public-api"
    assert jobs[0].source_url == "https://app.mokahr.com/campus_apply/shopee/2962#/job/job-1"
    assert "recommendCode" not in jobs[0].source_url
    assert jobs[0].location == "中国 深圳"
    assert jobs[0].declared_status == "open"
    assert jobs[2].declared_status == "closed"
    assert jobs[0].metadata["reported_total"] == "3"
    assert jobs[0].metadata["coverage"] == "complete public paginated job list"
    assert jobs[0].metadata["project"] == "2027届常规秋招"
    assert connector.authoritative is True


def test_shopee_public_connector_rejects_an_incomplete_page() -> None:
    connector = ShopeeCampusPageConnector(
        fetch_html=lambda _url: _public_page("2962"),
        fetch_json=lambda _url, _payload: _encrypted_response({"jobStats": {"total": 1}, "jobs": []}),
    )

    with pytest.raises(ValueError, match="incomplete page"):
        connector.fetch()


def test_shopee_talent_program_and_intern_connectors_use_separate_official_boards() -> None:
    ai_star = ShopeeAiStarProgramConnector()
    intern = ShopeeInternConnector()

    assert ai_star.name == "shopee:ai-star-program-public-api"
    assert ai_star.site_id == "170008"
    assert ai_star.board_label == "AI Star 人才计划"
    assert intern.name == "shopee:intern-public-api"
    assert intern.site_id == "140513"
    assert intern.board_label == "研发中心实习生招聘"
    assert ai_star.authoritative is True
    assert intern.authoritative is True


def test_joinquant_and_nvidia_connectors_use_their_own_official_boards() -> None:
    calls: list[dict] = []

    def fetch_json(_url: str, payload: dict) -> dict:
        calls.append(payload)
        return _encrypted_response({"jobStats": {"total": 1}, "jobs": [_job("joinquant-job", "量化研究员（校招）")]})

    joinquant = JoinQuantCampusConnector(
        fetch_html=lambda _url: _public_page("92347", "joinquant"),
        fetch_json=fetch_json,
    )
    jobs = joinquant.fetch()
    nvidia = NvidiaCampusConnector()

    assert jobs[0].source_name == "joinquant:campus-public-api"
    assert jobs[0].company == "JoinQuant"
    assert calls[0]["orgId"] == "joinquant"
    assert calls[0]["siteId"] == "92347"
    assert nvidia.name == "nvidia:campus-public-api"
    assert nvidia.organization_id == "nvidia"
    assert nvidia.site_id == "47111"
    assert nvidia.page_url == "https://app.mokahr.com/campus-recruitment/nvidia/47111"
    assert nvidia.authoritative is True
