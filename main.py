"""Root entrypoint.

This script exports ULearning question training data to the 佛脚刷题 JSON format.

Usage:
  uv run python main.py

Optional:
  uv run python main.py --env .env --cookie cookie.json --url <practice_url> --output output --txt --raw
"""

from __future__ import annotations

import argparse
import sys

from python.config import Config
from python.client import ULearningClient
from python.exporter import Exporter
from python.formatter import QuestionFormatter


def run(
    env_path: str,
    cookie_file: str | None,
    practice_url: str | None,
    output_dir: str | None,
    export_raw: bool,
    export_txt: bool,
) -> int:
    try:
        config = Config.load(env_file=env_path, cookie_file=cookie_file, practice_url=practice_url)
        if output_dir:
            config.output_dir = output_dir

        client = ULearningClient(config)
        raw_questions = client.fetch_all_questions()

        formatted_questions = QuestionFormatter.format_all(raw_questions)

        exporter = Exporter(config.output_dir)
        exporter.export_json(formatted_questions)

        if export_raw:
            exporter.export_raw_json(raw_questions)

        if export_txt:
            exporter.export_txt(formatted_questions)

        return 0
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Export 佛脚刷题 JSON from ULearning")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    parser.add_argument(
        "--cookie",
        default=None,
        help="Path to cookie file (cookie.json or cookie.jsonc). If omitted, auto-detect in repo root.",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Practice URL like https://lms.dgut.edu.cn/utest/index.html?...#/questionTrain/practice/QT_ID/OC_ID/QT_TYPE",
    )
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--raw", action="store_true", help="Also export raw API JSON")
    parser.add_argument("--txt", action="store_true", help="Also export a readable txt")

    args = parser.parse_args()
    raise SystemExit(run(args.env, args.cookie, args.url, args.output, args.raw, args.txt))


if __name__ == "__main__":
    main()
