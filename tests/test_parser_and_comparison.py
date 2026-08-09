from __future__ import annotations

from collections import Counter

import pytest

from policyimpact.comparison import extract_candidate_rules
from policyimpact.models import CandidateRule, PolicyChange, RuleType
from policyimpact.parser import PolicyParseError, parse_policy_text


def test_policy_metadata_and_sections_parse(scenario: dict[str, object]) -> None:
    old_policy = scenario["old_policy"]
    new_policy = scenario["new_policy"]
    assert old_policy.policy_id == new_policy.policy_id == "SYN-PAY-042"
    assert old_policy.version == "1.0"
    assert new_policy.version == "2.0"
    assert [section.section_id for section in old_policy.sections] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
    ]
    assert old_policy.synthetic is True
    assert new_policy.synthetic is True


def test_missing_controlled_policy_section_is_rejected(
    scenario: dict[str, object]
) -> None:
    root = scenario["root"]
    text = (root / "data/policies/policy_v1.md").read_text(encoding="utf-8")
    malformed = text.replace(
        "## 6. Contextual Transition Clause", "### 6. Contextual Transition Clause"
    )
    with pytest.raises(PolicyParseError, match="sections 1 through 6"):
        parse_policy_text(malformed)


def test_exactly_four_material_changes_match_ground_truth(
    scenario: dict[str, object]
) -> None:
    changes = scenario["changes"]
    ground_truth = scenario["ground_truth"]
    expected = ground_truth["expected_policy_changes"]
    assert len(changes) == len(expected) == 4
    assert [_compact_change(change) for change in changes] == expected


def test_three_executable_pairs_and_one_abstention_match_ground_truth(
    scenario: dict[str, object]
) -> None:
    old_rules = {rule.rule_type: rule for rule in scenario["old_rules"]}
    new_rules = {rule.rule_type: rule for rule in scenario["new_rules"]}
    ground_truth = scenario["ground_truth"]

    executable_types = (
        RuleType.DIAGNOSIS_INCLUSION,
        RuleType.MAXIMUM_UNITS,
        RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW,
    )
    generated_pairs = [
        {
            "change_id": old_rules[rule_type].change_id,
            "old_rule": _compact_rule(old_rules[rule_type]),
            "new_rule": _compact_rule(new_rules[rule_type]),
        }
        for rule_type in executable_types
    ]
    assert generated_pairs == ground_truth["expected_executable_rule_pairs"]

    abstention = {
        "change_id": old_rules[RuleType.AMBIGUOUS_HUMAN_REVIEW].change_id,
        "old_rule": _compact_rule(old_rules[RuleType.AMBIGUOUS_HUMAN_REVIEW]),
        "new_rule": _compact_rule(new_rules[RuleType.AMBIGUOUS_HUMAN_REVIEW]),
        "expected_outcome": "ambiguous_human_review",
    }
    assert abstention == ground_truth["expected_abstention"]
    assert abstention["old_rule"]["executable"] is False
    assert abstention["new_rule"]["executable"] is False


def test_each_version_extracts_one_rule_of_each_supported_type(
    scenario: dict[str, object]
) -> None:
    for policy in (scenario["old_policy"], scenario["new_policy"]):
        counts = Counter(rule.rule_type for rule in extract_candidate_rules(policy))
        assert counts == Counter({rule_type: 1 for rule_type in RuleType})


def _evidence_key(evidence: object) -> dict[str, str]:
    return {
        "policy_version": evidence.policy_version,
        "section_id": evidence.section_id,
    }


def _compact_change(change: PolicyChange) -> dict[str, object]:
    return {
        "change_id": change.change_id,
        "section_id": change.section_id,
        "category": change.category.value,
        "old_summary": change.old_summary,
        "new_summary": change.new_summary,
        "executable": change.executable,
        "human_review_required": change.human_review_required,
        "old_evidence": _evidence_key(change.old_evidence),
        "new_evidence": _evidence_key(change.new_evidence),
    }


def _compact_rule(rule: CandidateRule) -> dict[str, object]:
    data = rule.model_dump(mode="json")
    data["evidence"] = _evidence_key(rule.evidence)
    return data

