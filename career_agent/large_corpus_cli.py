"""Report the verified 10,000-JD all-job corpus."""

from __future__ import annotations

import argparse
import json

from .large_corpus import OPEN_JOBS_MANIFEST, large_coverage_report, load_large_job_records


def main() -> None:
    parser = argparse.ArgumentParser(description="CareerAgent licensed all-job corpus")
    parser.add_argument("command", choices=("report", "manifest"))
    args = parser.parse_args()
    if args.command == "manifest":
        print(OPEN_JOBS_MANIFEST.read_text(encoding="utf-8"))
        return
    records, deduplication = load_large_job_records()
    report = large_coverage_report(records)
    report["deduplication"] = deduplication
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
