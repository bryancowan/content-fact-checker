#!/usr/bin/env python3
"""Check the OpenRouter provider allowlist against OpenRouter's own location data.

config.OPENROUTER_ALLOWED_PROVIDERS limits OpenRouter to backends based in the US or
Europe. OpenRouter publishes each backend's headquarters and, for some, its data centres
at /api/v1/providers. This flags any allowlisted backend that OpenRouter no longer lists,
records no headquarters for, or places outside the US and Europe, and any that is on the
config.EXCLUDED_OPENROUTER_PROVIDERS list whatever OpenRouter's record says. It needs no
API key.

Run it when you change the list and now and then, since OpenRouter's data and backends
change. Exits 1 if anything is flagged.
"""

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fact_checker.config import (  # noqa: E402
    EXCLUDED_OPENROUTER_PROVIDERS,
    OPENROUTER_ALLOWED_PROVIDERS,
)

PROVIDERS_URL = "https://openrouter.ai/api/v1/providers"
# ISO country codes OpenRouter reports for places we accept: the US, plus European countries.
ALLOWED_COUNTRIES = {
    "US", "AT", "BE", "CH", "DE", "DK", "ES", "FI", "FR", "GB", "IE", "IT", "NL", "NO", "PL", "SE",
}  # fmt: skip


def find_problems(allowed: tuple[str, ...] | list[str], providers: list[dict]) -> list[str]:
    """One message per allowlisted slug whose OpenRouter record doesn't support the policy."""
    by_slug = {p["slug"]: p for p in providers}
    problems = []
    for slug in allowed:
        if slug in EXCLUDED_OPENROUTER_PROVIDERS:
            # Whatever OpenRouter's record says: these were excluded on ownership or how
            # they run, which a headquarters field doesn't show.
            problems.append(f"{slug}: on the excluded list (ownership or how it runs)")
        record = by_slug.get(slug)
        if record is None:
            problems.append(f"{slug}: not in OpenRouter's provider list (renamed or removed?)")
            continue
        hq = record.get("headquarters")
        if not hq:
            problems.append(f"{slug}: OpenRouter records no headquarters")
        elif hq not in ALLOWED_COUNTRIES:
            problems.append(f"{slug}: headquarters {hq}")
        outside = [dc for dc in record.get("datacenters") or [] if dc not in ALLOWED_COUNTRIES]
        if outside:
            problems.append(f"{slug}: data centres in {', '.join(outside)}")
    return problems


def main() -> int:
    with urllib.request.urlopen(PROVIDERS_URL, timeout=30) as response:
        providers = json.load(response)["data"]
    problems = find_problems(OPENROUTER_ALLOWED_PROVIDERS, providers)
    for problem in problems:
        print(problem)
    print(f"{len(OPENROUTER_ALLOWED_PROVIDERS)} allowlisted; {len(problems)} flagged.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
