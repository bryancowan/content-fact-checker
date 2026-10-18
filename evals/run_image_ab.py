#!/usr/bin/env python3
"""A/B test vision models on claim extraction from images.

Each image in evals/images.jsonl lists the claims it should yield and, for the
prompt-injection image, a marker that must not come back as a claim. Only vision
models belong here (not reflection/beam-1.0, which is text-only); one without
vision support records errors rather than stopping the run.

    python evals/run_image_ab.py --models openai:gpt-6-luna,openrouter:nvidia/nemotron-3.5-super-vl
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from evals.image_scoring import (  # noqa: E402
    ImageAttempt,
    render_markdown,
    reply_is_valid_claims_json,
    score_claims,
    summarize,
)
from evals.run_ab import DEFAULT_PRICING, RESULTS, validate_specs  # noqa: E402
from evals.scoring import parse_model_spec, price_tokens, total_usage  # noqa: E402
from fact_checker.claims import extract_claims_from_image  # noqa: E402
from fact_checker.llm import LLMCallError, llm_override, record_llm_calls  # noqa: E402

EVALS = ROOT / "evals"
DEFAULT_MANIFEST = EVALS / "images.jsonl"
MAX_CLAIMS = 8


def run_attempt(spec: str, entry: dict, image_bytes: bytes, pricing: dict) -> ImageAttempt:
    provider, model = parse_model_spec(spec)
    attempt = ImageAttempt(model=spec, image_id=entry["id"], expected=len(entry["expected"]))
    with llm_override(provider, model), record_llm_calls() as calls:
        try:
            attempt.claims = extract_claims_from_image(image_bytes, "image/png", MAX_CLAIMS)
        except LLMCallError as exc:
            attempt.error = str(exc)
    if calls:
        attempt.parse_failed = not reply_is_valid_claims_json(calls[-1].text)
        usage = total_usage(calls)
        attempt.latency_s = usage["latency_s"]
        attempt.prompt_tokens = usage["prompt_tokens"]
        attempt.completion_tokens = usage["completion_tokens"]
        attempt.reasoning_tokens = usage["reasoning_tokens"]
        attempt.cost_usd = usage["cost_usd"]
        if attempt.cost_usd is None:
            attempt.cost_usd = price_tokens(
                usage["prompt_tokens"], usage["completion_tokens"], pricing.get(spec)
            )
    attempt.found, attempt.extras, attempt.injected = score_claims(
        attempt.claims, entry["expected"], entry["forbidden"]
    )
    return attempt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--models", required=True, help="Comma-separated provider:model specs.")
    parser.add_argument("--repeats", type=int, default=3, help="Runs per image per model.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--pricing", type=Path, default=DEFAULT_PRICING)
    parser.add_argument("--name", default="images", help="Run name, used in the output filenames.")
    args = parser.parse_args()

    specs = validate_specs(parser, args.models)
    entries = [json.loads(line) for line in args.manifest.read_text().splitlines() if line.strip()]
    images = {e["id"]: (args.manifest.parent / "images" / e["file"]).read_bytes() for e in entries}
    pricing = json.loads(args.pricing.read_text()) if args.pricing.exists() else {}

    attempts: list[ImageAttempt] = []
    for spec in specs:
        print(f"\n{spec}")
        for repeat in range(args.repeats):
            for entry in entries:
                attempt = run_attempt(spec, entry, images[entry["id"]], pricing)
                attempts.append(attempt)
                print(
                    f"  [{repeat + 1}/{args.repeats}] {entry['id']}: "
                    f"found {attempt.found}/{attempt.expected}, extras {attempt.extras}"
                    + (" INJECTED" if attempt.injected else "")
                    + (" (unparsed)" if attempt.parse_failed else "")
                    + (f" {attempt.error}" if attempt.error else "")
                )

    summaries = {s: summarize([a for a in attempts if a.model == s]) for s in specs}
    meta = {
        "date": date.today().isoformat(),
        "images": len(entries),
        "manifest": args.manifest.name,
        "repeats": args.repeats,
    }
    stem = f"{meta['date']}-{args.name}"
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{stem}.md").write_text(render_markdown(summaries, meta))
    with open(RESULTS / f"{stem}.jsonl", "w") as f:
        for a in attempts:
            f.write(json.dumps(a.__dict__) + "\n")
    print(f"\nWrote evals/results/{stem}.md and .jsonl")


if __name__ == "__main__":
    main()
