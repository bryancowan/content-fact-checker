#!/usr/bin/env python3
"""A/B test models on the verdict step of the fact checker.

Each claim in evals/claims.jsonl has a known verdict. Web evidence is searched
once per claim and cached, so every model judges identical evidence and search
noise stays out of the comparison. Models are named provider:model, either inline
or as @file (one per line, # for comments; see evals/models.txt):

    python evals/run_ab.py --models @evals/models.txt --reasoning-effort high --workers 6

--reasoning-effort gives every model the same setting. --workers runs that many models
at once (calls within a model stay sequential, so its latencies are not queued behind
each other).
"""

import argparse
import json
import os
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from evals.scoring import (  # noqa: E402
    Attempt,
    parse_model_spec,
    price_tokens,
    render_markdown,
    summarize,
    total_usage,
)
from fact_checker.checker import judge_claim  # noqa: E402
from fact_checker.config import SUPPORTED_PROVIDERS  # noqa: E402
from fact_checker.llm import LLMCallError, llm_override, record_llm_calls  # noqa: E402
from fact_checker.search import search_web  # noqa: E402

REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")

EVALS = ROOT / "evals"
DEFAULT_CLAIMS = EVALS / "claims.jsonl"
DEFAULT_PRICING = EVALS / "pricing.json"
RESULTS = EVALS / "results"
EVIDENCE_CACHE = RESULTS / "evidence-cache.json"


def validate_specs(parser: argparse.ArgumentParser, models: str) -> list[str]:
    """Split --models and reject bad specs before any paid call.

    A typo found mid-run would abort after the earlier models had been paid for,
    with no report written. "@path" reads the specs from a file instead.
    """
    if models.startswith("@"):
        path = Path(models[1:])
        if not path.is_file():
            parser.error(f"Model list {str(path)!r} not found.")
        lines = (line.split("#", 1)[0] for line in path.read_text().splitlines())
        models = ",".join(line.strip() for line in lines if line.strip())
    specs = [s.strip() for s in models.split(",") if s.strip()]
    if not specs:
        parser.error("No models given.")
    for spec in specs:
        try:
            provider, _ = parse_model_spec(spec)
        except ValueError as exc:
            parser.error(str(exc))
        if provider not in SUPPORTED_PROVIDERS:
            parser.error(
                f"Unknown provider {provider!r} in {spec!r}; "
                f"expected one of {', '.join(SUPPORTED_PROVIDERS)}."
            )
    return specs


def run_per_model(specs: list[str], work: Callable[[str], list], workers: int) -> list:
    """Call work(spec) for each model, up to `workers` at a time; results keep spec order."""
    if workers <= 1:
        return [work(spec) for spec in specs]
    with ThreadPoolExecutor(max_workers=min(workers, len(specs))) as pool:
        return list(pool.map(work, specs))


def load_claims(path: Path, limit: int | None) -> list[dict]:
    claims = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if limit is None:
        return claims
    # Take an even slice of each label, so a small smoke test still sees all three.
    by_label: dict[str, list[dict]] = {}
    for claim in claims:
        by_label.setdefault(claim["label"], []).append(claim)
    per_label = max(1, limit // len(by_label))
    return [c for group in by_label.values() for c in group[:per_label]]


# Must match the search in checker.fact_check_single_claim, so the eval judges the
# evidence the app would have shown. Both settings are in the cache key, so changing
# either here can't serve stale results.
SEARCH_NUM = 6
SEARCH_MODE = "fast"


def get_evidence(claims: list[dict]) -> dict[str, list[dict]]:
    """Search results per claim id, from the cache where present."""
    cache = json.loads(EVIDENCE_CACHE.read_text()) if EVIDENCE_CACHE.exists() else {}
    keys = {c["id"]: f"{SEARCH_MODE}|{SEARCH_NUM}|{c['id']}|{c['claim']}" for c in claims}
    for claim in claims:
        if keys[claim["id"]] not in cache:
            print(f"  searching {claim['id']}: {claim['claim']}")
            cache[keys[claim["id"]]] = search_web(
                query=claim["claim"], num=SEARCH_NUM, mode=SEARCH_MODE
            )
            EVIDENCE_CACHE.write_text(json.dumps(cache))
    return {cid: cache[key] for cid, key in keys.items()}


def run_attempt(
    spec: str,
    claim: dict,
    results: list[dict],
    pricing: dict,
    reasoning_effort: str | None = None,
) -> Attempt:
    provider, model = parse_model_spec(spec)
    attempt = Attempt(
        model=spec, claim_id=claim["id"], label=claim["label"], category=claim.get("category")
    )
    with llm_override(provider, model, reasoning_effort), record_llm_calls() as calls:
        try:
            judged = judge_claim(claim["claim"], results)
        except LLMCallError as exc:
            attempt.error = str(exc)
        else:
            attempt.verdict = judged.verdict
            attempt.parse_failed = judged.parse_failed
    if calls:
        usage = total_usage(calls)
        attempt.latency_s = usage["latency_s"]
        attempt.prompt_tokens = usage["prompt_tokens"]
        attempt.completion_tokens = usage["completion_tokens"]
        attempt.reasoning_tokens = usage["reasoning_tokens"]
        attempt.cost_usd = usage["cost_usd"]
        attempt.served_by = calls[-1].served_by
        if attempt.cost_usd is None:
            attempt.cost_usd = price_tokens(
                usage["prompt_tokens"], usage["completion_tokens"], pricing.get(spec)
            )
    return attempt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--models", required=True, help="Comma-separated provider:model specs, or @file."
    )
    parser.add_argument("--repeats", type=int, default=3, help="Runs per claim per model.")
    parser.add_argument(
        "--reasoning-effort",
        choices=REASONING_EFFORTS,
        help="Give every model this reasoning effort (default: each provider's own setting).",
    )
    parser.add_argument("--workers", type=int, default=1, help="Models to run at once.")
    parser.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    parser.add_argument("--pricing", type=Path, default=DEFAULT_PRICING)
    parser.add_argument("--limit", type=int, help="Use about this many claims, spread by label.")
    parser.add_argument("--name", default="ab", help="Run name, used in the output filenames.")
    args = parser.parse_args()

    specs = validate_specs(parser, args.models)
    claims = load_claims(args.claims, args.limit)
    pricing = json.loads(args.pricing.read_text()) if args.pricing.exists() else {}

    print(f"Gathering evidence for {len(claims)} claims")
    evidence = get_evidence(claims)

    def run_model(spec: str) -> list[Attempt]:
        done = []
        for repeat in range(args.repeats):
            for claim in claims:
                attempt = run_attempt(
                    spec, claim, evidence[claim["id"]], pricing, args.reasoning_effort
                )
                done.append(attempt)
                mark = "ok " if attempt.correct else "BAD"
                got = attempt.verdict or ("ERROR" if attempt.error else "?")
                print(
                    f"{spec} [{repeat + 1}/{args.repeats}] {claim['id']} {mark} "
                    f"label={claim['label']} got={got}"
                    + (" (unparsed)" if attempt.parse_failed else "")
                    + (f" {attempt.error}" if attempt.error else ""),
                    flush=True,
                )
        return done

    attempts: list[Attempt] = [
        a for done in run_per_model(specs, run_model, args.workers) for a in done
    ]

    summaries = {s: summarize([a for a in attempts if a.model == s]) for s in specs}
    label_counts = ", ".join(
        f"{n} {label}"
        for label in ("true", "false", "uncertain")
        if (n := sum(c["label"] == label for c in claims))
    )
    meta = {
        "date": date.today().isoformat(),
        "claims": len(claims),
        "label_counts": label_counts,
        "claims_file": args.claims.name,
        "repeats": args.repeats,
        "reasoning_effort": args.reasoning_effort,
    }

    stem = f"{meta['date']}-{args.name}"
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{stem}.md").write_text(render_markdown(summaries, meta) + "\n")
    with open(RESULTS / f"{stem}.jsonl", "w") as f:
        for a in attempts:
            f.write(json.dumps(a.__dict__) + "\n")
    print(f"\nWrote {os.path.relpath(RESULTS / stem)}.md and .jsonl")


if __name__ == "__main__":
    main()
