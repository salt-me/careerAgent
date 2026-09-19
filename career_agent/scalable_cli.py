"""Commands for large-corpus validation and coverage reporting."""

from __future__ import annotations

import argparse
import json

from .scalable_corpus import coverage_report, load_scalable_job_records


def main() -> None:
    parser = argparse.ArgumentParser(description="CareerAgent scalable public JD corpus")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("report", help="Validate source files and print 10,000-record coverage gaps")
    subparsers.add_parser("records", help="Print normalised records for inspection")
    args = parser.parse_args()
    records, deduplication = load_scalable_job_records()
    if args.command == "records":
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return
    report = coverage_report(records)
    report["deduplication"] = deduplication
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
