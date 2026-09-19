"""CLI for bounded importing from a user-visible public Nowcoder careers page."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .nowcoder_page_import import DEFAULT_OUTPUT, DEFAULT_PAGE_URL, import_public_career_page, summary_as_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="Import one public Nowcoder careers page as historical JD summaries")
    parser.add_argument("--page-url", default=DEFAULT_PAGE_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-records", type=int)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = import_public_career_page(
        page_url=args.page_url,
        output_path=args.output,
        max_records=args.max_records,
        overwrite=args.overwrite,
    )
    print(json.dumps(summary_as_dict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

