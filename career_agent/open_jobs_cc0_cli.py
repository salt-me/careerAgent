"""Command line entry point for the bounded CC0 10,000-JD import."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .open_jobs_cc0_import import DEFAULT_MANIFEST, DEFAULT_OUTPUT, import_subset


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a bounded 10,000-record CC0 JD subset")
    parser.add_argument("--target", type=int, default=10_000)
    parser.add_argument("--min-companies", type=int, default=10)
    parser.add_argument("--max-row-groups", type=int, default=12)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    summary = import_subset(
        target_records=args.target,
        min_companies_per_position=args.min_companies,
        max_row_groups=args.max_row_groups,
        output_path=args.output,
        manifest_path=args.manifest,
        overwrite=args.overwrite,
    )
    print(json.dumps(summary.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
