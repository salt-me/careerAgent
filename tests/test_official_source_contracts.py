from __future__ import annotations

from career_agent.platform.official_source_contracts import OfficialJsonContractConnector


def _contract(**changes):
    base = {
        "id": "acme", "company": "Acme", "feed_url": "https://careers.example.test/jobs.json", "items_path": "data.jobs",
        "authoritative": True, "full_enumeration_verified": True,
        "field_map": {"external_id": "id", "title": "name", "source_url": "url", "description": "description", "location": "city", "status": "status"},
    }
    return {**base, **changes}


def test_official_json_contract_maps_public_positions_and_authority() -> None:
    connector = OfficialJsonContractConnector(_contract(), fetch_json=lambda _: {"data": {"jobs": [{"id": "1", "name": "Engineer", "url": "https://careers.example.test/1", "description": "<p>Python</p>", "city": "Beijing", "status": "open"}]}})
    [job] = connector.fetch()
    assert connector.authoritative is True
    assert job.description == "Python"
    assert job.source_name == "official-json:acme"


def test_official_json_contract_never_enables_closure_without_enumeration_proof() -> None:
    connector = OfficialJsonContractConnector(_contract(full_enumeration_verified=False), fetch_json=lambda _: {"data": {"jobs": []}})
    assert connector.authoritative is False
