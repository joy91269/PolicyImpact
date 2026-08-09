from __future__ import annotations

import json
from pathlib import Path

from policyimpact.evaluation import evaluate, render_markdown


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_evaluation_recomputes_all_required_metrics() -> None:
    results = evaluate(PROJECT_ROOT)
    metrics = results["metrics"]
    expected_fraction_metrics = {
        "policy_change_precision": (4, 4),
        "policy_change_recall": (4, 4),
        "rule_field_exact_match": (6, 6),
        "evidence_section_accuracy": (8, 8),
        "abstention_correctness": (1, 1),
        "deterministic_impact_accuracy": (16, 16),
        "traceability_coverage": (20, 20),
    }
    for name, (numerator, denominator) in expected_fraction_metrics.items():
        assert metrics[name]["numerator"] == numerator
        assert metrics[name]["denominator"] == denominator
        assert metrics[name]["value"] == 1.0
    assert metrics["unsupported_assertion_count"]["value"] == 0
    assert results["run_metadata"]["live_model_invoked"] is False
    assert results["run_metadata"]["execution_mode"] == "offline_reviewed_demo_fixture"


def test_checked_in_evaluation_artifact_matches_recomputation_except_time() -> None:
    checked_in = json.loads(
        (PROJECT_ROOT / "evaluation/evaluation_results.json").read_text(
            encoding="utf-8"
        )
    )
    recomputed = evaluate(PROJECT_ROOT)
    checked_in["run_metadata"].pop("generated_at_utc")
    recomputed["run_metadata"].pop("generated_at_utc")
    assert checked_in == recomputed


def test_evaluation_report_labels_fixture_limit() -> None:
    report = render_markdown(evaluate(PROJECT_ROOT))
    assert "no live model was invoked" in report
    assert "not an estimate of live-model accuracy" in report
    assert "three accepts and one abstention" in report
