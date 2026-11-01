"""The allowlist checker: flags backends that don't meet the US/Europe policy."""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_openrouter_providers.py"
_spec = importlib.util.spec_from_file_location("check_openrouter_providers", _SCRIPT)
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

PROVIDERS = [
    {"slug": "together", "headquarters": "US", "datacenters": []},
    {"slug": "nebius", "headquarters": "NL", "datacenters": ["FI"]},
    {"slug": "minimax", "headquarters": "SG", "datacenters": ["US"]},
    {"slug": "mystery", "headquarters": None, "datacenters": []},
    {"slug": "mixed", "headquarters": "US", "datacenters": ["US", "SG"]},
]


def test_backends_in_the_us_or_europe_pass():
    assert checker.find_problems(["together", "nebius"], PROVIDERS) == []


def test_a_backend_headquartered_elsewhere_is_flagged_even_with_a_us_data_centre():
    [problem] = checker.find_problems(["minimax"], PROVIDERS)

    assert "headquarters SG" in problem


def test_a_backend_with_no_recorded_headquarters_is_flagged():
    [problem] = checker.find_problems(["mystery"], PROVIDERS)

    assert "no headquarters" in problem


def test_a_data_centre_outside_the_us_or_europe_is_flagged():
    [problem] = checker.find_problems(["mixed"], PROVIDERS)

    assert "data centres in SG" in problem


def test_a_slug_openrouter_no_longer_lists_is_flagged():
    [problem] = checker.find_problems(["gone"], PROVIDERS)

    assert "not in OpenRouter's provider list" in problem
