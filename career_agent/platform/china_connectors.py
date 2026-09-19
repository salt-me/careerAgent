"""Connectors for Chinese employer-owned recruitment pages.

These connectors use only content rendered by the public official careers page.
They deliberately avoid calling application, login, or protected internal APIs.
"""

from __future__ import annotations

from base64 import b64decode
import http.cookiejar
import json
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable

from Crypto.Cipher import AES

from .connectors import IncomingJob, _text


HtmlFetcher = Callable[[str], str]
JsonPostFetcher = Callable[[str, dict[str, Any]], dict[str, Any]]
MokaJsonFetcher = Callable[[str, dict[str, Any]], dict[str, Any]]


def _http_get_html(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CareerAgent/1.0; official-job-board-sync)",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


def _http_get_moka_html(url: str) -> str:
    """Fetch a public Moka page while retaining its challenge-set session cookie.

    Moka first responds with a same-URL redirect that sets an ``acw_tc``
    cookie.  A normal browser follows it with that cookie; a bare
    ``urlopen`` does not retain it and loops forever.  This is not an
    authenticated session and is used only to read the public career page.
    """

    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    with opener.open(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


def _http_post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CareerAgent/1.0; official-job-board-sync)",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://careers.pddglobalhr.com",
            "Referer": "https://careers.pddglobalhr.com/campus/grad",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    if not isinstance(payload, dict):
        raise ValueError("official careers endpoint returned a non-object payload")
    return payload


def _http_post_moka_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CareerAgent/1.0; official-job-board-sync)",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://app.mokahr.com",
            "Referer": "https://app.mokahr.com/",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        envelope = json.loads(response.read().decode("utf-8", "replace"))
    if not isinstance(envelope, dict):
        raise ValueError("Moka public job endpoint returned a non-object payload")
    return envelope


def _json_value_after(html: str, key: str) -> Any:
    marker = f'"{key}":'
    start = html.find(marker)
    if start < 0:
        raise ValueError(f"official page did not contain {key}")
    value_start = start + len(marker)
    return json.JSONDecoder().raw_decode(html[value_start:])[0]


class _MokaInitialDataParser(HTMLParser):
    value: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "input":
            return
        attributes = dict(attrs)
        if attributes.get("id") == "init-data":
            self.value = attributes.get("value")


def _moka_initial_data(html: str) -> dict[str, Any]:
    """Read the JSON payload rendered into a public Moka career page.

    This deliberately reads only the page's initial HTML.  It does not use a
    candidate session, recommendation code, or application endpoint.
    """

    parser = _MokaInitialDataParser(convert_charrefs=True)
    parser.feed(html)
    parser.close()
    if parser.value is None:
        raise ValueError("Moka public career page did not include initial data")
    try:
        payload = json.loads(parser.value)
    except json.JSONDecodeError as exc:
        raise ValueError("Moka public career page initial data was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Moka public career page initial data was not an object")
    return payload


def _decrypt_moka_public_payload(envelope: dict[str, Any], aes_iv: str) -> dict[str, Any]:
    """Decode the public Moka response exactly as the employer's page does."""

    ciphertext = envelope.get("data")
    key = envelope.get("necromancer")
    if not isinstance(ciphertext, str) or not isinstance(key, str) or not isinstance(aes_iv, str):
        raise ValueError("Moka public job endpoint returned an invalid encrypted payload")
    try:
        plaintext = AES.new(key.encode("utf-8"), AES.MODE_CBC, aes_iv.encode("utf-8")).decrypt(b64decode(ciphertext))
    except (TypeError, ValueError) as exc:
        raise ValueError("Moka public job endpoint payload could not be decoded") from exc
    padding = plaintext[-1] if plaintext else 0
    if padding < 1 or padding > AES.block_size or plaintext[-padding:] != bytes([padding]) * padding:
        raise ValueError("Moka public job endpoint payload had invalid padding")
    try:
        decoded = json.loads(plaintext[:-padding].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Moka public job endpoint payload was not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError("Moka public job endpoint decoded to a non-object payload")
    return decoded


class BaiduCampusPageConnector:
    """Read the publicly server-rendered first page of Baidu's campus board.

    The official UI has a protected internal pagination endpoint.  We do not
    bypass it, so this connector only consumes the positions its public page
    itself renders.  It is non-authoritative: a position falling off that page
    must not be mistaken for a closed job.
    """

    authoritative = False
    name = "baidu:campus-2027"
    page_url = "https://talent.baidu.com/jobs/list?projectType=1"

    def __init__(self, *, fetch_html: HtmlFetcher | None = None) -> None:
        self._fetch_html = fetch_html or _http_get_html

    def fetch(self) -> list[IncomingJob]:
        html = self._fetch_html(self.page_url)
        if "2027" not in html or "校园招聘" not in html:
            raise ValueError("Baidu campus board no longer exposes the expected 2027-campus page")
        records = _json_value_after(html, "listDetailData")
        if not isinstance(records, list):
            raise ValueError("Baidu campus board returned invalid listDetailData")

        jobs: list[IncomingJob] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            post_id = _text(record.get("postId"))
            title = _text(record.get("name"))
            if not post_id or not title:
                continue
            requirements = _text(record.get("serviceCondition"))
            responsibilities = _text(record.get("workContent"))
            jobs.append(
                IncomingJob(
                    source_name=self.name,
                    external_id=post_id,
                    source_url=f"https://talent.baidu.com/jobs/detail/GRADUATE/{post_id}",
                    company="百度",
                    title=title,
                    description="\n".join(part for part in (responsibilities, requirements) if part) or title,
                    location=_text(record.get("workPlace"), "not_disclosed"),
                    declared_status="open",
                    published_at=_text(record.get("updateDate")) or _text(record.get("publishDate")) or None,
                    declared_group=f"2027届 校招 {_text(record.get('projectType'), '校招')} {_text(record.get('postType'))}",
                    metadata={
                        "connector": "baidu_public_ssr",
                        "coverage": "official server-rendered first page only",
                        "post_type": _text(record.get("postType")),
                        "project_type": _text(record.get("projectType")),
                        "recruit_num": _text(record.get("recruitNum")),
                        "job_id": _text(record.get("jobId")),
                    },
                ).with_inferred_language()
            )
        return jobs


class PddCampusPageConnector:
    """Import the complete public PDD campus-job list.

    The employer's public ``/campus/grad`` page calls this endpoint directly.
    It returns a stable position ID, total count and complete public JD, so the
    connector pages until it has received every record.  The source remains
    non-authoritative until its public removal/closure semantics are reviewed.
    """

    authoritative = False
    name = "pdd:campus-public-api"
    endpoint = "https://careers.pddglobalhr.com/api/careers/api/recruit/position/list"
    detail_url = "https://careers.pddglobalhr.com/campus/grad/detail?positionId={position_id}"
    page_size = 20

    def __init__(self, *, fetch_json: JsonPostFetcher | None = None) -> None:
        self._fetch_json = fetch_json or _http_post_json

    @staticmethod
    def _published_at(value: Any) -> str | None:
        try:
            return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            return None

    def fetch(self) -> list[IncomingJob]:
        page, total, jobs, seen_ids = 1, None, [], set()
        while total is None or len(jobs) < total:
            payload = self._fetch_json(self.endpoint, {"page": page, "pageSize": self.page_size})
            result = payload.get("result") if payload.get("success") is True else None
            records = result.get("list") if isinstance(result, dict) else None
            if not isinstance(records, list):
                raise ValueError("PDD public campus endpoint returned an invalid position list")
            try:
                response_total = int(result.get("total"))
            except (TypeError, ValueError):
                raise ValueError("PDD public campus endpoint did not provide a total count") from None
            if response_total < len(jobs):
                raise ValueError("PDD public campus endpoint total decreased during pagination")
            total = response_total
            if not records and len(jobs) < total:
                raise ValueError("PDD public campus endpoint returned an incomplete page")
            for record in records:
                if not isinstance(record, dict):
                    continue
                position_id = _text(record.get("id"))
                title = _text(record.get("name"))
                if not position_id or not title:
                    continue
                if position_id in seen_ids:
                    raise ValueError(f"PDD public campus endpoint repeated position {position_id} on page {page}")
                seen_ids.add(position_id)
                recruitment_type = _text(record.get("recruitTypeName"))
                job_family = _text(record.get("jobName"))
                graduation_year = _text(record.get("graduationYear"))
                jobs.append(
                    IncomingJob(
                        source_name=self.name,
                        external_id=position_id,
                        source_url=self.detail_url.format(position_id=position_id),
                        company="拼多多集团",
                        title=title,
                        description=_text(record.get("jobDuty")) or title,
                        location=_text(record.get("workLocationName") or record.get("workLocation"), "not_disclosed"),
                        declared_status="open",
                        published_at=self._published_at(record.get("releaseTime")),
                        declared_group=" ".join(
                            part for part in (f"{graduation_year}届" if graduation_year else "", "校招", recruitment_type, job_family) if part
                        ),
                        metadata={
                            "connector": "pdd_public_campus_api",
                            "coverage": "complete public paginated campus list",
                            "position_code": _text(record.get("code")),
                            "recruitment_type": recruitment_type,
                            "job_family": job_family,
                            "graduation_year": graduation_year,
                            "labels": [str(label) for label in record.get("labelList") or []],
                        },
                    ).with_inferred_language()
                )
            page += 1

        if total is None or len(jobs) != total:
            raise ValueError(f"PDD public campus endpoint expected {total} positions but mapped {len(jobs)}")
        return jobs


class MokaPublicBoardConnector:
    """Import a complete public Moka career board from its own API.

    The official public page renders only 15 recent jobs, but it requests the
    complete paginated list itself from the public Moka endpoint.  The response
    is encrypted for browser delivery and is decoded with the public page's
    ephemeral key and IV.  No account, recommendation code, candidate data, or
    application endpoint is used.
    """

    authoritative = True
    name = ""
    organization_id = ""
    company = ""
    site_id = ""
    board_label = ""
    page_url = ""
    detail_url = ""
    endpoint = "https://app.mokahr.com/api/outer/ats-apply/website/jobs/v2"
    page_size = 20
    _city_names = {
        "110000": "北京",
        "310000": "上海",
        "440300": "深圳",
        "440305": "深圳",
    }

    def __init__(
        self,
        *,
        fetch_html: HtmlFetcher | None = None,
        fetch_json: MokaJsonFetcher | None = None,
    ) -> None:
        self._fetch_html = fetch_html or _http_get_moka_html
        self._fetch_json = fetch_json or _http_post_moka_json

    @classmethod
    def _location(cls, record: dict[str, Any]) -> str:
        location = record.get("location")
        if not isinstance(location, dict):
            locations = record.get("locations")
            location = locations[0] if isinstance(locations, list) and locations and isinstance(locations[0], dict) else None
        if not isinstance(location, dict):
            return "not_disclosed"
        address = _text(location.get("address"))
        city = cls._city_names.get(_text(location.get("cityId")))
        country = _text(location.get("country"))
        return " ".join(part for part in (country, city, address) if part) or "not_disclosed"

    def fetch(self) -> list[IncomingJob]:
        page_payload = _moka_initial_data(self._fetch_html(self.page_url))
        organization = page_payload.get("org")
        if (
            not isinstance(organization, dict)
            or _text(organization.get("id")) != self.organization_id
            or _text(organization.get("siteId")) != self.site_id
        ):
            raise ValueError("Moka public career page was not the expected employer board")
        aes_iv = _text(page_payload.get("aesIv"))
        if not aes_iv:
            raise ValueError("Moka public career page did not expose an API decryption IV")

        department_labels: dict[str, str] = {}
        for department in page_payload.get("jobsGroupedByDepartment") or []:
            if not isinstance(department, dict):
                continue
            label = _text(department.get("label"))
            for department_id in department.get("ids") or []:
                department_labels[_text(department_id)] = label

        raw_jobs: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        offset, total = 0, None
        while total is None or len(raw_jobs) < total:
            envelope = self._fetch_json(
                self.endpoint,
                {
                    "orgId": self.organization_id,
                    "siteId": self.site_id,
                    "limit": self.page_size,
                    "offset": offset,
                    "needStat": True,
                    "site": "campus",
                    "locale": "zh-CN",
                },
            )
            response = _decrypt_moka_public_payload(envelope, aes_iv)
            response_data = response.get("data") if response.get("success") is True else None
            records = response_data.get("jobs") if isinstance(response_data, dict) else None
            job_stats = response_data.get("jobStats") if isinstance(response_data, dict) else None
            if not isinstance(records, list) or not isinstance(job_stats, dict):
                raise ValueError("Moka public job endpoint returned an invalid job page")
            try:
                response_total = int(job_stats.get("total"))
            except (TypeError, ValueError):
                raise ValueError("Moka public job endpoint did not provide a valid total") from None
            if response_total < len(raw_jobs):
                raise ValueError("Moka public job endpoint total decreased during pagination")
            total = response_total
            if not records and len(raw_jobs) < total:
                raise ValueError("Moka public job endpoint returned an incomplete page")
            for record in records:
                if not isinstance(record, dict):
                    continue
                job_id = _text(record.get("id"))
                if not job_id:
                    continue
                if job_id in seen_ids:
                    raise ValueError(f"Moka public job endpoint repeated position {job_id} at offset {offset}")
                seen_ids.add(job_id)
                raw_jobs.append(record)
            offset += self.page_size

        if total is None or len(raw_jobs) != total:
            raise ValueError(f"Moka public job endpoint expected {total} positions but mapped {len(raw_jobs)}")

        jobs: list[IncomingJob] = []
        for record in raw_jobs:
            job_id = _text(record.get("id"))
            title = _text(record.get("title"))
            if not job_id or not title:
                continue
            status = _text(record.get("status")).casefold()
            functional_area = record.get("zhineng")
            functional_area_name = _text(functional_area.get("name")) if isinstance(functional_area, dict) else ""
            department = department_labels.get(_text(record.get("deptId")), "")
            project_folder = record.get("projectFolder")
            project_name = _text(project_folder.get("name")) if isinstance(project_folder, dict) else ""
            description = "\n".join(
                part
                for part in (
                    f"职位编号：{_text(record.get('mjCode'))}" if _text(record.get("mjCode")) else "",
                    f"职位方向：{functional_area_name}" if functional_area_name else "",
                    f"招聘项目：{department}" if department else "",
                    f"岗位项目：{project_name}" if project_name else "",
                    f"职位性质：{_text(record.get('commitment'))}" if _text(record.get("commitment")) else "",
                )
                if part
            ) or title
            jobs.append(
                IncomingJob(
                    source_name=self.name,
                    external_id=job_id,
                    source_url=self.detail_url.format(job_id=job_id),
                    company=self.company,
                    title=title,
                    description=description,
                    location=self._location(record),
                    declared_status="open" if status == "open" else "closed" if status == "closed" else "unknown",
                    published_at=_text(record.get("publishedAt")) or None,
                    declared_group=" ".join(part for part in (self.board_label, project_name, department, functional_area_name) if part),
                    metadata={
                        "connector": "moka_public_api",
                        "coverage": "complete public paginated job list",
                        "reported_total": str(total),
                        "site_id": self.site_id,
                        "board": self.board_label,
                        "job_code": _text(record.get("mjCode")),
                        "department": department,
                        "functional_area": functional_area_name,
                        "project": project_name,
                        "commitment": _text(record.get("commitment")),
                    },
                ).with_inferred_language()
            )
        return jobs


class ShopeeCampusPageConnector(MokaPublicBoardConnector):
    name = "shopee:campus-public-api"
    organization_id = "shopee"
    company = "Shopee"
    site_id = "2962"
    board_label = "校园招聘"
    page_url = "https://app.mokahr.com/campus_apply/shopee/2962"
    detail_url = "https://app.mokahr.com/campus_apply/shopee/2962#/job/{job_id}"


class ShopeeAiStarProgramConnector(ShopeeCampusPageConnector):
    name = "shopee:ai-star-program-public-api"
    site_id = "170008"
    board_label = "AI Star 人才计划"
    page_url = "https://app.mokahr.com/campus_apply/shopee/170008"
    detail_url = "https://app.mokahr.com/campus_apply/shopee/170008#/job/{job_id}"


class ShopeeInternConnector(ShopeeCampusPageConnector):
    name = "shopee:intern-public-api"
    site_id = "140513"
    board_label = "研发中心实习生招聘"
    page_url = "https://app.mokahr.com/campus_apply/shopee/140513"
    detail_url = "https://app.mokahr.com/campus_apply/shopee/140513#/job/{job_id}"


class JoinQuantCampusConnector(MokaPublicBoardConnector):
    name = "joinquant:campus-public-api"
    organization_id = "joinquant"
    company = "JoinQuant"
    site_id = "92347"
    board_label = "校园招聘"
    page_url = "https://app.mokahr.com/campus_apply/joinquant/92347"
    detail_url = "https://app.mokahr.com/campus_apply/joinquant/92347#/job/{job_id}"


class NvidiaCampusConnector(MokaPublicBoardConnector):
    name = "nvidia:campus-public-api"
    organization_id = "nvidia"
    company = "NVIDIA"
    site_id = "47111"
    board_label = "2027校园招聘与实习"
    page_url = "https://app.mokahr.com/campus-recruitment/nvidia/47111"
    detail_url = "https://app.mokahr.com/campus-recruitment/nvidia/47111#/job/{job_id}"
