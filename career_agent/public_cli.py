"""CLI for initializing and querying the public-JD vector collection."""

from __future__ import annotations

import argparse
import json

from .public_jds import load_public_jds
from .vector_retrieval import PublicJDVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="CareerAgent 公开 JD 向量库")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("index", help="下载 embedding 模型并建立本地 Qdrant 索引")
    search = commands.add_parser("search", help="对本地公开 JD 索引执行语义搜索")
    search.add_argument("query")
    commands.add_parser("list", help="列出来源已记录的公开 JD")
    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps(load_public_jds(), ensure_ascii=False, indent=2))
        return
    store = PublicJDVectorStore()
    if args.command == "index":
        print(json.dumps(store.rebuild(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps([hit.__dict__ for hit in store.search(args.query)], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
