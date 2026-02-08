import json
import re
import textwrap
from dataclasses import dataclass, field
from typing import Callable, Optional

from .claims import extract_claims_from_text, extract_claims_from_url
from .llm import call_cerebras_chat
from .search import search_web, build_evidence_context


@dataclass
class ClaimResult:
    claim: str
    verdict: str  # "true", "false", or "uncertain"
    reason: str
    sources: list[str] = field(default_factory=list)


def fact_check_single_claim(claim: str) -> ClaimResult:
    """Fact-check a single claim: search for evidence, then judge with the LLM."""
    # Search the web for evidence
    results = search_web(query=claim, num=6, mode="one-shot")
    evidence_context = build_evidence_context(results)

    system_prompt = (
        "You are a careful, skeptical fact-checking assistant.\n"
        "You get a factual claim and web search excerpts.\n"
        "Decide if the evidence supports, contradicts, or does not clearly resolve the claim.\n\n"
        "Respond with STRICT JSON:\n"
        "{\n"
        '  "verdict": "true" | "false" | "uncertain",\n'
        '  "reason": "short explanation",\n'
        '  "top_sources": ["url1", "url2", ...]\n'
        "}\n"
        "Use 'true' only when the evidence strongly supports the claim.\n"
        "Use 'false' only when it clearly contradicts the claim.\n"
        "Otherwise use 'uncertain'."
    )

    user_prompt = textwrap.dedent(f"""
    Claim:
    {claim}

    Evidence (web search excerpts):
    {evidence_context}
    """)

    raw = call_cerebras_chat(user_content=user_prompt, system_content=system_prompt)
    raw = raw.strip()

    # Strip markdown code fences
    raw = re.sub(r"^\s*```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```\s*$", "", raw)

    try:
        data = json.loads(raw)
    except Exception:
        data = {"verdict": "uncertain", "reason": "Could not parse model output.", "top_sources": []}

    verdict = str(data.get("verdict", "uncertain")).lower()
    if verdict not in {"true", "false", "uncertain"}:
        verdict = "uncertain"

    top_sources = data.get("top_sources") or []
    if not isinstance(top_sources, list):
        top_sources = [str(top_sources)]
    top_sources = [str(u) for u in top_sources][:5]

    return ClaimResult(
        claim=claim,
        verdict=verdict,
        reason=data.get("reason", ""),
        sources=top_sources,
    )


def fact_check_text(
    text: str,
    max_claims: int = 6,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
) -> list[ClaimResult]:
    """Full pipeline: extract claims from text, then fact-check each one.

    on_progress(message, current_index, total_claims) is called before each claim
    is checked, allowing the caller to display progress.
    """
    claims = extract_claims_from_text(text, max_claims=max_claims)
    if not claims:
        return []

    results = []
    for i, claim in enumerate(claims):
        if on_progress:
            on_progress(f"Checking claim {i + 1}/{len(claims)}: {claim}", i, len(claims))
        result = fact_check_single_claim(claim)
        results.append(result)

    return results


def fact_check_url(
    url: str,
    max_claims: int = 6,
    on_progress: Optional[Callable[[str, int, int], None]] = None,
) -> list[ClaimResult]:
    """Full pipeline: extract claims from a URL, then fact-check each one."""
    claims = extract_claims_from_url(url, max_claims=max_claims)
    if not claims:
        return []

    results = []
    for i, claim in enumerate(claims):
        if on_progress:
            on_progress(f"Checking claim {i + 1}/{len(claims)}: {claim}", i, len(claims))
        result = fact_check_single_claim(claim)
        results.append(result)

    return results
