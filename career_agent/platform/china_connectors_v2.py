"""Source-specific taxonomy correction for official 2027 campus pages."""

from __future__ import annotations

import re
from dataclasses import replace

from .china_connectors import BaiduCampusPageConnector
from .connectors import IncomingJob


class BaiduCampus2027Connector(BaiduCampusPageConnector):
    """Trust Baidu's page-level ``2027届校招`` label over JD preference text.

    Job descriptions frequently say that a prior internship is preferred.  That
    is candidate background, not an internship vacancy.  The raw text remains
    in metadata; the normalized retrieval text replaces that ambiguous phrase
    so the generic taxonomy does not classify a graduate role as internship.
    """

    def fetch(self) -> list[IncomingJob]:
        corrected: list[IncomingJob] = []
        for job in super().fetch():
            normalized_description = re.sub(
                r"(?:实习(?:经历|经验)?|internship(?: experience)?|intern experience)",
                "相关项目经历",
                job.description,
                flags=re.IGNORECASE,
            )
            corrected.append(
                replace(
                    job,
                    description=normalized_description,
                    declared_group=f"2027届 校招 正式毕业生招聘 {job.declared_group}",
                    metadata={
                        **job.metadata,
                        "official_description": job.description,
                        "taxonomy_override": "official_2027_campus_page",
                    },
                )
            )
        return corrected
