import pytest

from career_agent.official_ats_import import is_direct_ats_url, select_new_company_candidates


def _row(company: str, url: str) -> dict:
    return {
        "id": company,
        "company": company,
        "title": "Software Engineer",
        "url": url,
        "function": "engineering",
    }


def test_selects_only_new_direct_ats_companies():
    rows = [
        _row("Known", "https://jobs.lever.co/known/1"),
        _row("Fresh One", "https://boards.greenhouse.io/fresh/jobs/1"),
        _row("Fresh Two", "https://jobs.ashbyhq.com/fresh-two/1"),
        _row("Not ATS", "https://example.test/jobs/1"),
    ]
    indices, companies = select_new_company_candidates(rows, known_companies={"known"}, min_new_companies=2)
    assert indices == [1, 2]
    assert companies == {"freshone", "freshtwo"}
    assert is_direct_ats_url("https://apply.workable.com/acme/j/123") is True


def test_rejects_when_new_company_floor_is_not_met():
    with pytest.raises(RuntimeError, match="net-new companies"):
        select_new_company_candidates(
            [_row("Only One", "https://jobs.lever.co/one/1")], known_companies=set(), min_new_companies=2
        )
