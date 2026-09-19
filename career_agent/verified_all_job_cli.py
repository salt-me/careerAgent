"""Commands for the canonical verified 10k all-job corpus."""

from __future__ import annotations

import argparse
import json

from .verified_all_job_corpus import OPEN_JOBS_MANIFEST, large_coverage_report, load_verified_all_job_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Verified CareerAgent 10k all-job corpus")
    parser.add_argument("command", choices=("report", "manifest"))
    args = parser.parse_args()
    if args.command == "manifest":
        print(OPEN_JOBS_MANIFEST.read_text(encoding="utf-8"))
        return
    records, deduplication = load_verified_all_job_records()
    report = large_coverage_report(records)
    report["deduplication"] = deduplication
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

