"""CLI for the verified net-new company direct-ATS import."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .official_ats_import import DEFAULT_MANIFEST, DEFAULT_OUTPUT, import_new_company_row_group


def main() -> None:
    parser = argparse.ArgumentParser(description="Import direct-ATS JDs from at least 100 new companies")
    parser.add_argument("--row-group", type=int, default=3)
    parser.add_argument("--min-new-companies", type=int, default=100)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = import_new_company_row_group(
        row_group=args.row_group,
        min_new_companies=args.min_new_companies,
        output_path=args.output,
        manifest_path=args.manifest,
        overwrite=args.overwrite,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

