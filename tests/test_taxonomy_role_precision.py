from __future__ import annotations

from career_agent.platform.taxonomy import classify_job


def test_product_family_requires_product_management_intent() -> None:
    assert classify_job("Product Manager", "Build APIs with engineers.").job_group == "product"
    assert classify_job("Product Owner", "Own a roadmap.").job_group == "product"
    assert classify_job("Product Designer", "Own user research.").job_group == "design"
    assert classify_job("Product Marketing Manager", "Launch a product.").job_group == "marketing"
    assert classify_job("Product Operations Manager", "Work with product teams.").job_group == "operations"
    assert classify_job("Product Security Engineer", "Protect product infrastructure.").job_group == "engineering"
    assert classify_job("Backend Engineer", "Partner with product managers.").job_group == "engineering"


def test_product_keyword_in_description_does_not_override_actual_role() -> None:
    assert classify_job("Recruiter", "Recruit product managers and engineers.").job_group == "hr"
    assert classify_job("Software Engineer", "Build product features.").job_group == "engineering"
