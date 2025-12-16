"""
Main entry point for the ULearning question exporter
"""

import argparse
import sys
from pathlib import Path

from .config import Config
from .client import ULearningClient
from .formatter import QuestionFormatter
from .exporter import Exporter


def main():
    parser = argparse.ArgumentParser(
        description="Export questions from ULearning platform to 佛脚刷题 JSON format"
    )
    parser.add_argument(
        "--env", "-e",
        default=".env",
        help="Path to .env file (default: .env)"
    )
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
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory (default: from .env or 'output')"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Also export raw API response"
    )
    parser.add_argument(
        "--txt",
        action="store_true",
        help="Also export readable text format"
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        print(f"Loading configuration from {args.env}...")
        config = Config.load(env_file=args.env, cookie_file=args.cookie, practice_url=args.url)
        
        if args.output:
            config.output_dir = args.output
        
        print(f"Configuration loaded:")
        print(f"  - QT_ID: {config.qt_id}")
        print(f"  - OC_ID: {config.oc_id}")
        print(f"  - USER_ID: {config.user_id}")
        print(f"  - Output: {config.output_dir}")
        
        # Fetch questions
        client = ULearningClient(config)
        raw_questions = client.fetch_all_questions()
        
        # Format to 佛脚刷题 format
        print("Formatting questions...")
        formatted_questions = QuestionFormatter.format_all(raw_questions)
        print(f"Formatted {len(formatted_questions)} questions")
        
        # Export
        exporter = Exporter(config.output_dir)
        exporter.export_json(formatted_questions)
        
        if args.raw:
            exporter.export_raw_json(raw_questions)
        
        if args.txt:
            exporter.export_txt(formatted_questions)
        
        print("\nDone!")
        
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
