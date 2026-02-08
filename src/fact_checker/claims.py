import json
import re

import requests
from bs4 import BeautifulSoup

from .llm import call_cerebras_chat


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


def extract_claims_from_url(url: str, max_claims: int = 8) -> list[str]:
    """Fetch a URL's content and extract atomic factual claims from it."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        main_content = soup.find("article") or soup.find("main")
        if main_content:
            main_text = " ".join(p.get_text() for p in main_content.find_all("p"))
        else:
            elements = soup.find_all(["p", "h1", "h2", "h3"])
            main_text = " ".join(elem.get_text() for elem in elements)

        if not main_text or len(main_text.strip()) < 100:
            return []

        return extract_claims_from_text(main_text, max_claims=max_claims)
    except requests.exceptions.RequestException:
        return []
