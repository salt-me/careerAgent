"""Command-line entry point for the expanded 12-JD vector collection."""

from __future__ import annotations

import argparse
import json

from .curated_vector_store import CuratedJDVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="CareerAgent 扩展公开 JD 向量库")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("index")
    search = subparsers.add_parser("search")
    search.add_argument("query")
    args = parser.parse_args()
    store = CuratedJDVectorStore()
    if args.command == "index":
        print(json.dumps(store.rebuild(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps([hit.__dict__ for hit in store.search(args.query)], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
