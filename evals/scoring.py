"""Scoring and reporting for the model A/B test. Pure functions, no network."""

import math
from dataclasses import dataclass

VERDICTS = ("true", "false", "uncertain")


@dataclass
class Attempt:
    """One model judging one claim once."""

    model: str  # "provider:model", as given on the command line
    claim_id: str
    label: str
    category: str | None = None  # from the claims file, when it has one
    verdict: str | None = None  # None when the call itself failed
    parse_failed: bool = False  # the model answered, but not with valid JSON
    error: str | None = None  # an LLMCallError message
    latency_s: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    cost_usd: float | None = None

    @property
    def correct(self) -> bool:
        return self.verdict == self.label and not self.parse_failed and self.error is None


def parse_model_spec(spec: str) -> tuple[str, str]:
    """Split "provider:model" on the first colon (OpenRouter slugs can hold more, e.g. ":free")."""
    provider, sep, model = spec.partition(":")
    if not sep or not provider or not model:
        raise ValueError(f"Model spec {spec!r} must look like provider:model.")
    return provider, model


def price_tokens(
    prompt_tokens: int | None, completion_tokens: int | None, pricing: dict | None
) -> float | None:
    """Cost from a per-million-token price entry, or None if anything needed is unknown."""
    if not pricing or prompt_tokens is None or completion_tokens is None:
        return None
    input_price, output_price = pricing.get("input_per_m"), pricing.get("output_per_m")
    if input_price is None or output_price is None:
        return None
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000


def _sum_or_none(values: list) -> float | int | None:
    return None if any(v is None for v in values) else sum(values)


def total_usage(calls: list) -> dict:
    """Sum what a block of recorded LLM calls cost: a truncation retry makes two.

    A figure is None unless every call reported it, so a partial total can't pass
    for a real one.
    """
    return {
        "latency_s": _sum_or_none([c.latency_s for c in calls]),
        "prompt_tokens": _sum_or_none([c.prompt_tokens for c in calls]),
        "completion_tokens": _sum_or_none([c.completion_tokens for c in calls]),
        "reasoning_tokens": _sum_or_none([c.reasoning_tokens for c in calls]),
        "cost_usd": _sum_or_none([c.cost_usd for c in calls]),
    }


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile; None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def summarize(attempts: list[Attempt]) -> dict:
    """Aggregate one model's attempts.

    Accuracy counts every attempt, so a failed call or unparseable answer is wrong
    rather than dropped; they are also counted on their own, because "the model
    was wrong" and "the model could not answer in the required format" are
    different findings.
    """
    total = len(attempts)
    answered = [a for a in attempts if a.error is None and not a.parse_failed]
    correct = [a for a in attempts if a.correct]

    per_class = {}
    for verdict in VERDICTS:
        predicted = [a for a in answered if a.verdict == verdict]
        actual = [a for a in attempts if a.label == verdict]
        hits = [a for a in predicted if a.label == verdict]
        per_class[verdict] = {
            "precision": _ratio(len(hits), len(predicted)),
            "recall": _ratio(len(hits), len(actual)),
            "predicted": len(predicted),
            "actual": len(actual),
        }

    # Where each label ended up. Reading across a row shows what a model confuses.
    confusion = {label: dict.fromkeys((*VERDICTS, "unparsed", "error"), 0) for label in VERDICTS}
    for a in attempts:
        if a.error is not None:
            outcome = "error"
        elif a.parse_failed:
            outcome = "unparsed"
        else:
            outcome = a.verdict
        confusion[a.label][outcome] += 1

    # Repeats of the same claim that disagree are noise, not signal.
    by_claim: dict[str, list[Attempt]] = {}
    for a in attempts:
        by_claim.setdefault(a.claim_id, []).append(a)
    repeated = [group for group in by_claim.values() if len(group) > 1]
    stable = [g for g in repeated if len({(a.verdict, a.parse_failed) for a in g}) == 1]

    categories: dict[str, dict[str, int]] = {}
    for a in attempts:
        if a.category:
            tally = categories.setdefault(a.category, {"attempts": 0, "correct": 0})
            tally["attempts"] += 1
            tally["correct"] += a.correct

    latencies = [a.latency_s for a in attempts if a.latency_s is not None]
    costs = [a.cost_usd for a in attempts if a.cost_usd is not None]
    cost_known = len(costs) == total and total > 0
    total_cost = sum(costs) if cost_known else None

    return {
        "attempts": total,
        "correct": len(correct),
        "accuracy": _ratio(len(correct), total),
        "parse_failures": sum(a.parse_failed for a in attempts),
        "errors": sum(a.error is not None for a in attempts),
        "per_class": per_class,
        "confusion": confusion,
        "categories": categories,
        "consistency": _ratio(len(stable), len(repeated)),
        "latency_mean_s": _mean(latencies),
        "latency_p50_s": percentile(latencies, 50),
        "latency_p95_s": percentile(latencies, 95),
        "prompt_tokens_mean": _mean([a.prompt_tokens for a in attempts if a.prompt_tokens]),
        "completion_tokens_mean": _mean(
            [a.completion_tokens for a in attempts if a.completion_tokens]
        ),
        "reasoning_tokens_mean": _mean(
            [a.reasoning_tokens for a in attempts if a.reasoning_tokens is not None]
        ),
        "cost_total_usd": total_cost,
        "cost_per_claim_usd": total_cost / total if total_cost is not None else None,
        "cost_per_1k_claims_usd": total_cost / total * 1000 if total_cost is not None else None,
        "cost_per_correct_usd": (
            total_cost / len(correct) if total_cost is not None and correct else None
        ),
    }


def fmt(value: float | None, spec: str = ".3f", prefix: str = "", suffix: str = "") -> str:
    return "n/a" if value is None else f"{prefix}{value:{spec}}{suffix}"


def pct(value: float | None) -> str:
    return fmt(None if value is None else value * 100, ".1f", suffix="%")


def render_markdown(summaries: dict[str, dict], meta: dict) -> str:
    """The results report: a headline table, then per-class detail and confusion."""
    models = list(summaries)
    lines = [
        f"# Model A/B results, {meta['date']}",
        "",
        f"- Claims: {meta['claims']} ({meta['label_counts']}), from `{meta['claims_file']}`",
        f"- Repeats per claim: {meta['repeats']}",
        "- Reasoning effort, sampling and prompts are each provider's defaults from "
        "`src/fact_checker/config.py`",
        "- Every model saw the same cached web evidence per claim.",
        "",
        "## Headline",
        "",
        "| Model | Accuracy | Unparsed | Errors | Consistency | Latency mean / p95 | "
        "Cost per 1k claims | Cost per correct |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in models:
        s = summaries[m]
        lines.append(
            f"| `{m}` | {pct(s['accuracy'])} ({s['correct']}/{s['attempts']}) "
            f"| {s['parse_failures']} | {s['errors']} | {pct(s['consistency'])} "
            f"| {fmt(s['latency_mean_s'], '.1f', suffix='s')} / "
            f"{fmt(s['latency_p95_s'], '.1f', suffix='s')} "
            f"| {fmt(s['cost_per_1k_claims_usd'], '.2f', prefix='$')} "
            f"| {fmt(s['cost_per_correct_usd'], '.5f', prefix='$')} |"
        )

    lines += [
        "",
        "Accuracy counts failed calls and unparseable answers as wrong. Consistency is the "
        "share of claims where every repeat gave the same result. Cost is n/a when a "
        "provider reports no cost and `evals/pricing.json` has no price for it.",
        "",
        "## Tokens per call (mean)",
        "",
        "| Model | Prompt | Completion | of which reasoning |",
        "|---|---|---|---|",
    ]
    for m in models:
        s = summaries[m]
        lines.append(
            f"| `{m}` | {fmt(s['prompt_tokens_mean'], '.0f')} "
            f"| {fmt(s['completion_tokens_mean'], '.0f')} "
            f"| {fmt(s['reasoning_tokens_mean'], '.0f')} |"
        )

    lines += ["", "## Precision and recall by verdict", ""]
    lines += [
        "| Model | Verdict | Precision | Recall | Predicted | Actual |",
        "|---|---|---|---|---|---|",
    ]
    for m in models:
        for verdict in VERDICTS:
            c = summaries[m]["per_class"][verdict]
            lines.append(
                f"| `{m}` | {verdict} | {pct(c['precision'])} | {pct(c['recall'])} "
                f"| {c['predicted']} | {c['actual']} |"
            )

    category_names = sorted({c for m in models for c in summaries[m]["categories"]})
    if category_names:
        lines += ["", "## Accuracy by category", ""]
        lines += ["| Model | " + " | ".join(category_names) + " |"]
        lines += ["|---|" + "---|" * len(category_names)]
        for m in models:
            cells = []
            for name in category_names:
                tally = summaries[m]["categories"].get(name)
                cells.append(
                    "n/a"
                    if not tally
                    else f"{pct(tally['correct'] / tally['attempts'])} "
                    f"({tally['correct']}/{tally['attempts']})"
                )
            lines.append(f"| `{m}` | " + " | ".join(cells) + " |")

    lines += ["", "## Confusion (rows: true label; columns: what the model returned)", ""]
    for m in models:
        lines += [f"`{m}`", "", "| Label | true | false | uncertain | unparsed | error |"]
        lines.append("|---|---|---|---|---|---|")
        for label in VERDICTS:
            row = summaries[m]["confusion"][label]
            lines.append(
                f"| {label} | {row['true']} | {row['false']} | {row['uncertain']} "
                f"| {row['unparsed']} | {row['error']} |"
            )
        lines.append("")
    return "\n".join(lines)
