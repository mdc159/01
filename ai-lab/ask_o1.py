"""
ask_o1.py — Direct O1 API call from the command line.

Submit structured strategic questions to O1 and get JSON responses.

Usage:
    # Ask a question directly
    uv run ask_o1.py "What is the minimal viable improvement loop?"

    # Submit the strategy document for adjudication
    uv run ask_o1.py --file ../docs/lab/o1-strategy-prompt.md

    # Lower reasoning effort for cheaper/faster queries
    uv run ask_o1.py --effort medium "Quick question here"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import llm
from config import Models, O1Settings


def main():
    parser = argparse.ArgumentParser(description="Direct O1 strategic query")
    parser.add_argument("question", nargs="?", help="Question to ask O1")
    parser.add_argument("--file", "-f", type=Path, help="Read question from a markdown file")
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high"],
        default=None,
        help="Override reasoning effort (default: from .env)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Override model (default: {Models.STRATEGIC})",
    )
    parser.add_argument(
        "--system",
        "-s",
        type=Path,
        help="System prompt file (default: o1_system_prompt.md)",
    )
    args = parser.parse_args()

    # Resolve the question
    if args.file:
        if not args.file.exists():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        question = args.file.read_text()
    elif args.question:
        question = args.question
    else:
        parser.print_help()
        sys.exit(1)

    # Override reasoning effort if specified
    if args.effort:
        O1Settings.REASONING_EFFORT = args.effort

    # Load system prompt
    system_prompt = None
    if args.system:
        system_prompt = args.system.read_text()
    else:
        default_system = Path(__file__).parent / "o1_system_prompt.md"
        if default_system.exists():
            system_prompt = default_system.read_text()

    # Also load CANON.md as context
    canon_path = Path(__file__).parent.parent / "CANON.md"
    if canon_path.exists() and system_prompt:
        system_prompt += "\n\n=== PRODUCT CANON (AUTHORITATIVE) ===\n" + canon_path.read_text()

    model = args.model or Models.STRATEGIC
    print(f"Calling {model} (effort={O1Settings.REASONING_EFFORT})...", file=sys.stderr)
    print(f"Question: {len(question)} chars", file=sys.stderr)

    messages = [{"role": "user", "content": question}]
    response = llm.call(messages, model=model, system_prompt=system_prompt)

    # Try to pretty-print if JSON
    try:
        parsed = json.loads(response)
        print(json.dumps(parsed, indent=2))
    except json.JSONDecodeError:
        print(response)


if __name__ == "__main__":
    main()
