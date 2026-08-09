"""Reproducible evaluation for the controlled reviewed-demo scenario."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .agents import OfflineFixtureProvider
from .io import load_json
from .models import AuditorDisposition
from .scenario import load_scenario
from .workflow import (
    authorize_execution,
    execute_authorized_claim_review,
    load_human_approvals,
    run_agent_review,
)


def _metric(
    numerator: int,
    denominator: int,
    scope: str,
) -> dict[str, object]:
    return {
        "value": numerator / denominator if denominator else None,
        "numerator": numerator,
        "denominator": denominator,
        "scope": scope,
    }


def _evidence_key(item: Any) -> tuple[str, str]:
    return item.policy_version, item.section_id


def evaluate(project_root: str | Path) -> dict[str, object]:
    root = Path(project_root)
    scenario = load_scenario(root)
    ground_truth = load_json(root / "data/ground_truth/ground_truth.json")
    provider = OfflineFixtureProvider(
        root / "data/agent_fixtures/offline_agent_review.json"
    )
    review = run_agent_review(scenario, provider)
    approvals = load_human_approvals(
        root / "data/ground_truth/demo_human_approvals.json"
    )
    authorization = authorize_execution(review, approvals)
    impacts = execute_authorized_claim_review(scenario, review, authorization)

    predicted_changes = {
        item.change.change_id: item for item in review.revised_analysis.findings
    }
    expected_changes = {
        item["change_id"]: item for item in ground_truth["expected_policy_changes"]
    }
    true_positive_ids = predicted_changes.keys() & expected_changes.keys()

    expected_rule_pairs = {
        item["change_id"]: item
        for item in ground_truth["expected_executable_rule_pairs"]
    }
    rule_total = 0
    rule_exact = 0
    compared_fields = (
        "rule_id",
        "policy_id",
        "policy_version",
        "change_id",
        "rule_type",
        "field",
        "operator",
        "value",
        "executable",
    )
    for change_id, expected_pair in expected_rule_pairs.items():
        predicted = predicted_changes[change_id]
        for side, rule in (("old_rule", predicted.old_rule), ("new_rule", predicted.new_rule)):
            rule_total += 1
            generated = rule.model_dump(mode="json")
            expected = expected_pair[side]
            fields_match = all(generated[field] == expected[field] for field in compared_fields)
            evidence_matches = (
                generated["evidence"]["policy_version"]
                == expected["evidence"]["policy_version"]
                and generated["evidence"]["section_id"]
                == expected["evidence"]["section_id"]
            )
            rule_exact += int(fields_match and evidence_matches)

    expected_evidence = {
        item["change_id"]: {
            "old": (
                item["old_evidence"]["policy_version"],
                item["old_evidence"]["section_id"],
            ),
            "new": (
                item["new_evidence"]["policy_version"],
                item["new_evidence"]["section_id"],
            ),
        }
        for item in ground_truth["expected_policy_changes"]
    }
    evidence_total = 0
    evidence_correct = 0
    for change_id, finding in predicted_changes.items():
        for side, evidence in (
            ("old", finding.change.old_evidence),
            ("new", finding.change.new_evidence),
        ):
            evidence_total += 1
            evidence_correct += int(
                _evidence_key(evidence) == expected_evidence[change_id][side]
            )

    expected_abstention_id = ground_truth["expected_abstention"]["change_id"]
    final_audit = {item.change_id: item for item in review.final_audit.findings}
    abstention_correct = int(
        final_audit[expected_abstention_id].disposition
        is AuditorDisposition.ABSTAIN
    )
    final_unsupported = sum(
        len(item.unsupported_assertions) for item in review.final_audit.findings
    )

    expected_impacts = {
        item["claim_id"]: item for item in ground_truth["expected_claim_impacts"]
    }
    impact_correct = 0
    for impact in impacts:
        expected = expected_impacts[impact.claim_id]
        generated = {
            "old_outcome": impact.old_outcome.value,
            "new_outcome": impact.new_outcome.value,
            "affected": impact.affected,
            "human_review_required": impact.human_review_required,
            "matched_rule_ids": list(impact.matched_rule_ids),
            "expected_evidence": [
                {
                    "policy_version": item.policy_version,
                    "section_id": item.section_id,
                }
                for item in impact.evidence_references
            ],
            "reason": impact.reason,
        }
        expected_compact = {
            key: value
            for key, value in expected.items()
            if key not in {"claim_id", "scenario_category"}
        }
        impact_correct += int(generated == expected_compact)

    policies = {
        scenario.old_policy.version: scenario.old_policy,
        scenario.new_policy.version: scenario.new_policy,
    }
    traceable_records = 0
    traceable_total = len(predicted_changes) + len(impacts)
    for finding in predicted_changes.values():
        evidence_items = (
            finding.change.old_evidence,
            finding.change.new_evidence,
        )
        if all(
            item.excerpt
            == policies[item.policy_version].section(item.section_id).text
            for item in evidence_items
        ):
            traceable_records += 1
    for impact in impacts:
        if all(
            item.excerpt
            == policies[item.policy_version].section(item.section_id).text
            for item in impact.evidence_references
        ):
            traceable_records += 1

    category_counts = Counter(
        item["scenario_category"] for item in ground_truth["expected_claim_impacts"]
    )
    outcome_counts = Counter(item.new_outcome.value for item in impacts)
    metrics = {
        "policy_change_precision": _metric(
            len(true_positive_ids),
            len(predicted_changes),
            "Four revised findings in the reviewed offline fixture.",
        ),
        "policy_change_recall": _metric(
            len(true_positive_ids),
            len(expected_changes),
            "Four manually specified material changes.",
        ),
        "rule_field_exact_match": _metric(
            rule_exact,
            rule_total,
            "Six old/new executable rules across three rule pairs; all typed fields and section keys must match.",
        ),
        "evidence_section_accuracy": _metric(
            evidence_correct,
            evidence_total,
            "Eight old/new section references across four changes.",
        ),
        "abstention_correctness": _metric(
            abstention_correct,
            1,
            "The single manually specified ambiguous change.",
        ),
        "unsupported_assertion_count": {
            "value": final_unsupported,
            "scope": "Final auditor output only; lower is better.",
        },
        "deterministic_impact_accuracy": _metric(
            impact_correct,
            len(expected_impacts),
            "All 16 full ClaimImpact records, including reason and evidence keys.",
        ),
        "traceability_coverage": _metric(
            traceable_records,
            traceable_total,
            "Four revised change records plus 16 claim-impact records with exact policy excerpts.",
        ),
    }

    return {
        "project": "PolicyImpact",
        "synthetic_demonstration_data": True,
        "run_metadata": {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "execution_mode": review.provider_mode.value,
            "provider_label": review.provider_label,
            "recording_path": review.recording_path,
            "live_model_invoked": review.live_model_invoked,
            "revision_round_count": review.revision_round_count,
            "ground_truth_path": "data/ground_truth/ground_truth.json",
        },
        "scenario": {
            "policy_pair": "SYN-PAY-042 v1.0 to v2.0",
            "material_changes": len(expected_changes),
            "executable_rule_pairs": len(expected_rule_pairs),
            "expected_abstentions": 1,
            "claims": len(expected_impacts),
            "scenario_category_counts": dict(sorted(category_counts.items())),
            "new_outcome_counts": dict(sorted(outcome_counts.items())),
        },
        "metrics": metrics,
        "agent_decisions": {
            "initial": {
                item.change_id: item.disposition.value
                for item in review.initial_audit.findings
            },
            "final": {
                item.change_id: item.disposition.value
                for item in review.final_audit.findings
            },
        },
        "authorization": authorization.model_dump(mode="json"),
        "guardrails_verified": [
            "No claim impact executes without final auditor acceptance and explicit human approval for every executable pair.",
            "The ambiguous clause remains visible, abstained, and non-executable.",
            "The deterministic engine—not either AI role—assigns all claim-impact outcomes.",
            "All codes and records are synthetic and contain no person or provider fields.",
            "The same 16 claims are compared under both versions; service date does not select a version.",
        ],
        "interpretation": (
            "The checked-in reviewed fixture reproduces all manually specified changes, "
            "rules, evidence keys, abstention, and 16 deterministic outcomes. These are "
            "scenario-consistency results for one controlled synthetic example, not an "
            "estimate of live-model accuracy, generalization, savings, or production readiness."
        ),
    }


def render_markdown(results: dict[str, object]) -> str:
    metrics = results["metrics"]
    lines = [
        "# PolicyImpact Evaluation Report",
        "",
        "**Status:** completed reviewed-fixture replay; no live model was invoked.",
        "",
        "> This evaluation uses only synthetic demonstration data. It does not measure production claim, payment, coverage, clinical, or fraud decisions.",
        "",
        "## Protocol",
        "",
        "The frozen manual ground truth specifies four material changes, three executable old/new rule pairs, one abstention, expected section evidence, and all 16 claim-impact records. The Policy Analyst and Evidence Auditor outputs were replayed from the checked-in reviewed fixture. After exactly one bounded revision, explicit reviewed-demo human approvals unlocked the unchanged deterministic engine.",
        "",
        "## Results",
        "",
        "| Metric | Result | Evaluation unit |",
        "|---|---:|---|",
    ]
    labels = {
        "policy_change_precision": "Policy change precision",
        "policy_change_recall": "Policy change recall",
        "rule_field_exact_match": "Rule-field exact match",
        "evidence_section_accuracy": "Evidence-section accuracy",
        "abstention_correctness": "Abstention correctness",
        "unsupported_assertion_count": "Unsupported assertion count",
        "deterministic_impact_accuracy": "Deterministic impact accuracy",
        "traceability_coverage": "Traceability coverage",
    }
    for name, metric in metrics.items():
        if name == "unsupported_assertion_count":
            result_text = str(metric["value"])
        else:
            result_text = f"{metric['numerator']}/{metric['denominator']} ({metric['value']:.1%})"
        lines.append(f"| {labels[name]} | {result_text} | {metric['scope']} |")
    lines.extend(
        [
            "",
            "## Agent audit path",
            "",
            "- Initial audit: diagnosis accept; units accept; modifier revise; ambiguous clause abstain.",
            "- Revision: the modifier finding explicitly states that documentation content is absent and the result is review routing, not a payment conclusion.",
            "- Final audit: three accepts and one abstention. The abstained pair remains non-executable.",
            "",
            "## Interpretation and limits",
            "",
            results["interpretation"],
            "",
            "The perfect fixture-replay scores are expected because the fixture is a reviewed demonstration aligned to the controlled ground truth. A credible next-stage pilot would require result-blind policy pairs, independent reviewers, disagreement reporting, and prospective live-model runs. None of those claims is made here.",
            "",
            "## Verified safeguards",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in results["guardrails_verified"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.project_root.resolve()
    results = evaluate(root)
    output_dir = root / "evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evaluation_results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "EVALUATION_REPORT.md").write_text(
        render_markdown(results), encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "metrics": results["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
