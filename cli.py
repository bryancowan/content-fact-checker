#!/usr/bin/env python3
"""Content Fact-Checker CLI — check claims from text or URLs."""

import argparse
import sys
import os

# Add src to path so the fact_checker package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fact_checker import fact_check_text, fact_check_url, ClaimResult


# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

VERDICT_COLORS = {
    "true": GREEN,
    "false": RED,
    "uncertain": YELLOW,
}


def print_progress(message: str, current: int, total: int):
    print(f"\n{'=' * 60}")
    print(f"  [{current + 1}/{total}] {message}")
    print(f"{'=' * 60}")


def print_results(results: list[ClaimResult]):
    print(f"\n{BOLD}{'=' * 60}")
    print(f"  FACT-CHECK RESULTS")
    print(f"{'=' * 60}{RESET}\n")

    for i, r in enumerate(results, 1):
        color = VERDICT_COLORS.get(r.verdict, RESET)
        print(f"{BOLD}Claim {i}:{RESET} {r.claim}")
        print(f"  Verdict: {color}{BOLD}{r.verdict.upper()}{RESET}")
        print(f"  Reason:  {r.reason}")
        if r.sources:
            print(f"  Sources:")
            for s in r.sources:
                print(f"    - {s}")
        print()


def interactive_mode():
    print(f"{BOLD}Content Fact-Checker{RESET}")
    print("Enter text to fact-check, or type a URL starting with http.\n")

    while True:
        try:
            user_input = input(f"{BOLD}> {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if user_input.startswith("http://") or user_input.startswith("https://"):
            print(f"\nFetching and analyzing URL: {user_input}")
            results = fact_check_url(user_input, on_progress=print_progress)
        else:
            results = fact_check_text(user_input, on_progress=print_progress)

        if results:
            print_results(results)
        else:
            print("\nNo claims could be extracted. Try different text or a different URL.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Content Fact-Checker — extract and verify claims from text or URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --text "Albert Einstein was born in Germany in 1879."
  python cli.py --url "https://www.snopes.com/fact-check/drinking-at-disney-world/"
  python cli.py                   # interactive mode
        """,
    )
    parser.add_argument("--text", "-t", type=str, help="Text to fact-check")
    parser.add_argument("--url", "-u", type=str, help="URL to fact-check")

    args = parser.parse_args()

    if args.text:
        results = fact_check_text(args.text, on_progress=print_progress)
        if results:
            print_results(results)
        else:
            print("No claims could be extracted from the provided text.")
    elif args.url:
        print(f"Fetching and analyzing URL: {args.url}")
        results = fact_check_url(args.url, on_progress=print_progress)
        if results:
            print_results(results)
        else:
            print("No claims could be extracted from the URL.")
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
