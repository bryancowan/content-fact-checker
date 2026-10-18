import json
import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field

from .claims import extract_claims_from_image, extract_claims_from_text, extract_claims_from_url
from .llm import LLMTruncatedError, call_llm_chat
from .search import build_evidence_context, search_web

_VERDICT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "claim_verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["true", "false", "uncertain"]},
                "reason": {"type": "string"},
                "top_sources": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["verdict", "reason", "top_sources"],
            "additionalProperties": False,
        },
    },
}


def _error_result(claim: str, problem: str) -> "ClaimResult":
    return ClaimResult(
        claim=claim,
        verdict="error",
        reason=f"{problem} No verdict could be reached for this claim; try checking it again.",
        parse_failed=True,
    )


def _filter_to_evidence_urls(candidates: list, evidence_urls: set[str]) -> list[str]:
    """Keep only cited URLs that actually appeared in the search evidence.

    The model returns top_sources as free-form strings, which are rendered in the
    UI. Restricting them to URLs the search actually returned drops both
    hallucinated citations and any link injected via untrusted input (e.g. text
    embedded in an uploaded image).
    """
    kept = []
    for candidate in candidates:
        url = str(candidate).strip()
        if url in evidence_urls and url.startswith(("http://", "https://")):
            kept.append(url)
    return kept


@dataclass
class ClaimResult:
    claim: str
    # "true", "false" or "uncertain" -- the model's judgement -- or "error" when no
    # usable answer came back. "error" is kept apart from "uncertain" so a technical
    # failure is never shown to the user as the model being unsure.
    verdict: str
    reason: str
    sources: list[str] = field(default_factory=list)
    # The reply was cut off or wasn't valid JSON, so there is no model verdict
    # (verdict is "error"). Evals count these apart from wrong verdicts.
    parse_failed: bool = False


def fact_check_single_claim(claim: str) -> ClaimResult:
    """Fact-check a single claim: search for evidence, then judge with the LLM."""
    results = search_web(query=claim, num=6, mode="fast")
    return judge_claim(claim, results)


def judge_claim(claim: str, results: list[dict]) -> ClaimResult:
    """Judge a claim against search results already in hand.

    Split from the search so an eval can reuse one set of results across models.
    """
    evidence_context = build_evidence_context(results)
    evidence_urls = {str(r["url"]) for r in results if r.get("url")}

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

    try:
        raw = call_llm_chat(
            user_content=user_prompt,
            system_content=system_prompt,
            response_format=_VERDICT_RESPONSE_FORMAT,
        )
    except LLMTruncatedError:
        return _error_result(claim, "The model's reply was cut off before it finished.")

    try:
        data = json.loads(raw.strip())
    except Exception:
        return _error_result(claim, "The model's reply wasn't in the expected format.")

    verdict = str(data.get("verdict", "uncertain")).lower()
    if verdict not in {"true", "false", "uncertain"}:
        verdict = "uncertain"

    top_sources = data.get("top_sources") or []
    if not isinstance(top_sources, list):
        top_sources = [top_sources]
    top_sources = _filter_to_evidence_urls(top_sources, evidence_urls)[:5]

    return ClaimResult(
        claim=claim,
        verdict=verdict,
        reason=data.get("reason", ""),
        sources=top_sources,
    )


def fact_check_text(
    text: str,
    max_claims: int = 6,
    on_progress: Callable[[str, int, int], None] | None = None,
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
    on_progress: Callable[[str, int, int], None] | None = None,
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


def fact_check_image(
    image_bytes: bytes,
    mime_type: str,
    max_claims: int = 6,
    on_progress: Callable[[str, int, int], None] | None = None,
) -> list[ClaimResult]:
    """Full pipeline: extract claims from an image, then fact-check each one."""
    claims = extract_claims_from_image(image_bytes, mime_type, max_claims=max_claims)
    if not claims:
        return []

    results = []
    for i, claim in enumerate(claims):
        if on_progress:
            on_progress(f"Checking claim {i + 1}/{len(claims)}: {claim}", i, len(claims))
        result = fact_check_single_claim(claim)
        results.append(result)

    return results
