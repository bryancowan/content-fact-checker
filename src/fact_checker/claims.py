import json
import re

import requests
from bs4 import BeautifulSoup

from .llm import call_cerebras_chat
from .url_guard import UnsafeURLError, validate_public_url

# Cap how much of a response we read, to avoid memory abuse from a hostile or
# huge response. Generous for real articles.
MAX_RESPONSE_BYTES = 3 * 1024 * 1024
# Cap manual redirect following.
MAX_REDIRECTS = 5


def extract_claims_from_text(text: str, max_claims: int = 8) -> list[str]:
    """Use Cerebras LLM to extract atomic factual claims from text."""
    system_prompt = (
        "You are an information extraction assistant.\n"
        f"From the user's text, extract up to {max_claims} atomic factual claims.\n"
        "Each claim should:\n"
        "- Be checkable against external sources (dates, numbers, named entities)\n"
        "- Be concrete and not an opinion.\n\n"
        "Return STRICT JSON:\n"
        "{\n"
        '  "claims": ["...", "..."]\n'
        "}\n"
    )

    user_prompt = f"Text:\n\n{text}\n\nExtract up to {max_claims} factual claims."

    raw = call_cerebras_chat(user_content=user_prompt, system_content=system_prompt)
    raw = raw.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^\s*```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```\s*$", "", raw)

    try:
        data = json.loads(raw)
        claims = data.get("claims", [])
        claims = [c.strip() for c in claims if isinstance(c, str) and c.strip()]
        return claims[:max_claims]
    except Exception:
        return []


def _safe_get_text(url: str) -> str:
    """Fetch a URL's body as text with SSRF protection.

    Validates the target against the SSRF guard before each request, and follows
    redirects manually so every hop's destination is re-validated (the default
    requests redirect handling would otherwise let a public URL redirect into an
    internal address). Reads at most MAX_RESPONSE_BYTES of the body.
    """
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        validate_public_url(current)
        response = requests.get(
            current, timeout=15, allow_redirects=False, stream=True
        )
        try:
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise UnsafeURLError("Redirect with no Location header")
                # Resolve relative redirects against the current URL.
                current = requests.compat.urljoin(current, location)
                continue

            response.raise_for_status()
            # Bound the amount we read into memory.
            content = response.raw.read(MAX_RESPONSE_BYTES + 1, decode_content=True)
            if len(content) > MAX_RESPONSE_BYTES:
                raise UnsafeURLError("Response exceeds maximum allowed size")
            encoding = response.encoding or response.apparent_encoding or "utf-8"
            return content.decode(encoding, errors="replace")
        finally:
            response.close()

    raise UnsafeURLError("Too many redirects")


def extract_claims_from_url(url: str, max_claims: int = 8) -> list[str]:
    """Fetch a URL's content and extract atomic factual claims from it."""
    try:
        html = _safe_get_text(url)
        soup = BeautifulSoup(html, "html.parser")

        main_content = soup.find("article") or soup.find("main")
        if main_content:
            main_text = " ".join(p.get_text() for p in main_content.find_all("p"))
        else:
            elements = soup.find_all(["p", "h1", "h2", "h3"])
            main_text = " ".join(elem.get_text() for elem in elements)

        if not main_text or len(main_text.strip()) < 100:
            return []

        return extract_claims_from_text(main_text, max_claims=max_claims)
    except (requests.exceptions.RequestException, UnsafeURLError):
        return []
