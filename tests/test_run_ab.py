"""Tests for the A/B runner's input checks and evidence cache."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from evals import run_ab


@pytest.mark.parametrize("models", ["openruter:x", "openai:gpt-6-luna,bogus:y", "no-colon"])
def test_bad_model_specs_are_rejected_before_any_call(monkeypatch, models):
    """A typo found mid-run would abort after the earlier models had been paid for."""
    monkeypatch.setattr(sys, "argv", ["run_ab.py", "--models", models])
    monkeypatch.setattr(run_ab, "get_evidence", lambda claims: pytest.fail("ran past validation"))

    with pytest.raises(SystemExit) as excinfo:
        run_ab.main()

    assert excinfo.value.code == 2


def test_evidence_cache_is_invalidated_by_either_search_setting(monkeypatch, tmp_path):
    monkeypatch.setattr(run_ab, "EVIDENCE_CACHE", tmp_path / "cache.json")
    searches = []
    monkeypatch.setattr(
        run_ab, "search_web", lambda **kwargs: searches.append(kwargs) or [{"url": "u"}]
    )
    claims = [{"id": "c1", "claim": "A claim."}]

    run_ab.get_evidence(claims)
    run_ab.get_evidence(claims)
    assert len(searches) == 1  # second call came from the cache

    monkeypatch.setattr(run_ab, "SEARCH_NUM", run_ab.SEARCH_NUM + 1)
    run_ab.get_evidence(claims)
    assert len(searches) == 2

    monkeypatch.setattr(run_ab, "SEARCH_MODE", "advanced")
    run_ab.get_evidence(claims)
    assert len(searches) == 3
