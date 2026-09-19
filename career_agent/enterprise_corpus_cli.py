"""Report the official-enterprise augmented JD corpus."""

from __future__ import annotations

import json

from .enterprise_corpus import enterprise_report, load_enterprise_job_records


def main() -> None:
    records, deduplication = load_enterprise_job_records()
    report = enterprise_report(records)
    report["deduplication"] = deduplication
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

