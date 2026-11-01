"""Tests for the A/B runner's input checks and evidence cache."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import argparse
import threading
import time

import pytest

from evals import run_ab
from evals.scoring import Attempt
from fact_checker import checker, llm


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


# --- model lists and parallel runs -------------------------------------------


def _parser():
    return argparse.ArgumentParser(prog="run_ab.py")


def test_models_can_be_read_from_a_file_with_comments(tmp_path):
    path = tmp_path / "models.txt"
    path.write_text(
        "# the set\n\nopenai:gpt-6-luna   # baseline\n"
        "openrouter:qwen/qwen3.8-27b\n   \n# openrouter:nobody/off\n"
    )

    specs = run_ab.validate_specs(_parser(), f"@{path}")

    assert specs == ["openai:gpt-6-luna", "openrouter:qwen/qwen3.8-27b"]


def test_a_missing_or_empty_model_file_is_rejected(tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_text("# nothing here\n")

    for models in (f"@{tmp_path / 'nope.txt'}", f"@{empty}"):
        with pytest.raises(SystemExit):
            run_ab.validate_specs(_parser(), models)


def test_the_committed_model_list_is_valid():
    specs = run_ab.validate_specs(_parser(), f"@{run_ab.EVALS / 'models.txt'}")

    assert len(specs) == len(set(specs))
    assert "openai:gpt-6-luna" in specs
    assert not any("beam" in spec for spec in specs)


def test_run_per_model_keeps_spec_order_whether_or_not_it_runs_in_parallel():
    def work(spec):
        time.sleep(0.05 if spec == "slow" else 0)
        return [spec]

    specs = ["slow", "fast", "faster"]

    assert run_ab.run_per_model(specs, work, workers=1) == [["slow"], ["fast"], ["faster"]]
    assert run_ab.run_per_model(specs, work, workers=3) == [["slow"], ["fast"], ["faster"]]


def test_run_per_model_really_runs_models_at_the_same_time():
    barrier = threading.Barrier(3, timeout=5)

    def work(spec):
        barrier.wait()  # only returns once all three are running at once
        return [spec]

    assert run_ab.run_per_model(["a", "b", "c"], work, workers=3) == [["a"], ["b"], ["c"]]


def test_run_attempt_gives_the_model_the_requested_reasoning_effort(monkeypatch):
    seen = []

    def fake_judge(claim, results):
        seen.append(llm._override.get())
        return checker.ClaimResult(claim=claim, verdict="true", reason="r")

    monkeypatch.setattr(run_ab, "judge_claim", fake_judge)
    claim = {"id": "c1", "claim": "A claim.", "label": "true"}

    attempt = run_ab.run_attempt("openrouter:qwen/qwen3.8-27b", claim, [], {}, "low")

    assert seen == [("openrouter", "qwen/qwen3.8-27b", "low")]
    assert isinstance(attempt, Attempt)
    assert attempt.correct
