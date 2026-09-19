"""Command-line entrypoint for demo, evaluation and local web serving."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .api import serve
from .evaluation import evaluate_retrieval
from .workflow import CareerWorkflow


DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> None:
    parser = argparse.ArgumentParser(description="CareerAgent 本地演示")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("demo", help="使用内置匿名样例运行完整工作流")
    evaluation_parser = subparsers.add_parser("evaluate", help="运行内置检索离线评测")
    evaluation_parser.add_argument("--top-k", type=int, default=3)
    serve_parser = subparsers.add_parser("serve", help="启动浏览器演示")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "demo":
        result = CareerWorkflow().run(
            (DATA_DIR / "sample_resume.txt").read_text(encoding="utf-8"),
            (DATA_DIR / "sample_jd.txt").read_text(encoding="utf-8"),
            route="interview",
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif args.command == "evaluate":
        print(json.dumps(evaluate_retrieval(args.top_k), ensure_ascii=False, indent=2))
    else:
        serve(args.host, args.port)


if __name__ == "__main__":
    main()
