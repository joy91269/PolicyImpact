from __future__ import annotations

from collections import Counter

import pytest

from policyimpact.engine import DeterministicRuleEngine, RuleConfigurationError
from policyimpact.models import AuditDecision, AuditStatus, RuleType


def test_all_sixteen_claim_impacts_match_manual_ground_truth(
    scenario: dict[str, object]
) -> None:
    impacts = scenario["impacts"]
    ground_truth = scenario["ground_truth"]
    expected = ground_truth["expected_claim_impacts"]
    assert len(impacts) == len(expected) == 16

    generated = [_compact_impact(impact) for impact in impacts]
    expected_without_category = [
        {key: value for key, value in item.items() if key != "scenario_category"}
        for item in expected
    ]
    assert generated == expected_without_category


def test_claim_distribution_matches_controlled_design(
    scenario: dict[str, object]
) -> None:
    expected = scenario["ground_truth"]["expected_claim_impacts"]
    counts = Counter(item["scenario_category"] for item in expected)
    assert counts == {
        "clearly_affected": 6,
        "clearly_unaffected": 6,
        "boundary": 2,
        "human_review": 2,
    }


def test_every_outcome_evidence_is_an_exact_policy_excerpt(
    scenario: dict[str, object]
) -> None:
    policies = {
        scenario["old_policy"].version: scenario["old_policy"],
        scenario["new_policy"].version: scenario["new_policy"],
    }
    for impact in scenario["impacts"]:
        for evidence in impact.evidence_references:
            policy = policies[evidence.policy_version]
            section = policy.section(evidence.section_id)
            assert evidence.policy_id == policy.policy_id
            assert evidence.section_title == section.title
            assert evidence.excerpt == section.text


def test_ambiguity_cases_abstain_before_executable_rules(
    scenario: dict[str, object]
) -> None:
    impacts = {impact.claim_id: impact for impact in scenario["impacts"]}
    for claim_id in ("CLM-015", "CLM-016"):
        impact = impacts[claim_id]
        assert impact.old_outcome.value == "ambiguous_human_review"
        assert impact.new_outcome.value == "ambiguous_human_review"
        assert impact.human_review_required is True
        assert impact.matched_rule_ids == ("AMB-V1", "AMB-V2")
        assert {item.section_id for item in impact.evidence_references} == {"6"}


def test_non_executable_rule_pair_cannot_be_marked_for_execution(
    scenario: dict[str, object]
) -> None:
    audits = list(scenario["audits"])
    original = next(
        decision for decision in audits if decision.change_id == "CHG-AMB-004"
    )
    replacement = AuditDecision(
        change_id=original.change_id,
        status=AuditStatus.ACCEPTED_FOR_EXECUTION,
        rule_ids=original.rule_ids,
        reviewer=original.reviewer,
        rationale="Invalid test configuration.",
    )
    audits[audits.index(original)] = replacement
    with pytest.raises(RuleConfigurationError, match="must remain in review"):
        DeterministicRuleEngine(
            scenario["old_rules"], scenario["new_rules"], audits
        )


def test_engine_rejects_missing_audit_decision(scenario: dict[str, object]) -> None:
    audits = [
        decision
        for decision in scenario["audits"]
        if decision.change_id != "CHG-UNITS-002"
    ]
    with pytest.raises(RuleConfigurationError, match="missing audit decision"):
        DeterministicRuleEngine(
            scenario["old_rules"], scenario["new_rules"], audits
        )


def test_all_codes_are_fictional_and_claims_have_no_person_fields(
    scenario: dict[str, object]
) -> None:
    for claim in scenario["claims"]:
        assert claim.procedure_code.startswith("SYN-")
        assert all(code.startswith("SYN-") for code in claim.diagnosis_codes)
        assert claim.modifier is None or claim.modifier.startswith("SYN-")
        assert set(type(claim).model_fields) == {
            "claim_id",
            "service_date",
            "procedure_code",
            "diagnosis_codes",
            "modifier",
            "units",
        }


def _compact_impact(impact: object) -> dict[str, object]:
    return {
        "claim_id": impact.claim_id,
        "old_outcome": impact.old_outcome.value,
        "new_outcome": impact.new_outcome.value,
        "affected": impact.affected,
        "human_review_required": impact.human_review_required,
        "matched_rule_ids": list(impact.matched_rule_ids),
        "expected_evidence": [
            {
                "policy_version": evidence.policy_version,
                "section_id": evidence.section_id,
            }
            for evidence in impact.evidence_references
        ],
        "reason": impact.reason,
    }
