"""CLI to validate authorised JD exports before adding them to the corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .source_import import iter_csv_records, validate_records, write_jsonl_batch


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an authorised JD CSV export")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--source-name", required=True, choices=["liepin", "nowcoder", "boss", "official_company"])
    parser.add_argument("--output", type=Path, help="Destination JSONL batch; omit to validate only")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    accepted, result = validate_records(iter_csv_records(args.csv_path, source_name=args.source_name))
    output = {"accepted": result.accepted, "rejected": result.rejected, "errors": result.errors[:20]}
    if args.output and result.rejected == 0:
        write_jsonl_batch(accepted, args.output, overwrite=args.overwrite)
        output["written_to"] = str(args.output)
    elif args.output:
        output["written_to"] = None
        output["reason"] = "No file written because one or more rows failed validation."
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
