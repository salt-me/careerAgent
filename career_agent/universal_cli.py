"""CLI for the universal, cross-job-family CareerAgent corpus."""

from __future__ import annotations

import argparse
import json

from .universal_corpus import corpus_summary
from .universal_vector_store import UniversalVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Universal CareerAgent corpus")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("index", help="Embed and rebuild the local Qdrant index")
    subparsers.add_parser("summary", help="Show corpus coverage and provenance totals")
    search = subparsers.add_parser("search", help="Semantic search across job families")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--job-family")
    search.add_argument("--artifact-type", choices=["public_jd", "job_family_profile"])
    search.add_argument("--actionable-only", action="store_true")
    args = parser.parse_args()

    if args.command == "summary":
        print(json.dumps(corpus_summary(), ensure_ascii=False, indent=2))
        return

    store = UniversalVectorStore()
    if args.command == "index":
        print(json.dumps(store.rebuild(), ensure_ascii=False, indent=2))
        return
    hits = store.search(
        args.query,
        limit=args.limit,
        job_family=args.job_family,
        artifact_type=args.artifact_type,
        actionable_only=args.actionable_only,
    )
    print(json.dumps([hit.to_dict() for hit in hits], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
