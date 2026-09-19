"""Report the canonical production all-job corpus."""

from __future__ import annotations

import json

from .production_corpus import load_production_job_records, production_report


def main() -> None:
    records, deduplication = load_production_job_records()
    report = production_report(records)
    report["deduplication"] = deduplication
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

