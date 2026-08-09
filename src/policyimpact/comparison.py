"""Deterministic change detection and rule extraction for the controlled scenario."""

from __future__ import annotations

import re

from .models import (
    CandidateRule,
    ChangeCategory,
    ClaimField,
    EvidenceReference,
    PolicyChange,
    PolicyDocument,
    RuleOperator,
    RuleType,
)


CHANGE_IDS = {
    "3": "CHG-DIAG-001",
    "4": "CHG-UNITS-002",
    "5": "CHG-MOD-003",
    "6": "CHG-AMB-004",
}
EXPECTED_CHANGED_SECTIONS = tuple(CHANGE_IDS)


class ControlledPolicyError(ValueError):
    """Raised when policy text falls outside the deterministic scenario grammar."""


def evidence_for(document: PolicyDocument, section_id: str) -> EvidenceReference:
    section = document.section(section_id)
    return EvidenceReference(
        policy_id=document.policy_id,
        policy_version=document.version,
        section_id=section.section_id,
        section_title=section.title,
        excerpt=section.text,
    )


def compare_policy_versions(
    old_policy: PolicyDocument, new_policy: PolicyDocument
) -> tuple[PolicyChange, ...]:
    if old_policy.policy_id != new_policy.policy_id:
        raise ControlledPolicyError("policy IDs must match for version comparison")

    changed_sections = tuple(
        old_section.section_id
        for old_section, new_section in zip(old_policy.sections, new_policy.sections)
        if old_section.text != new_section.text or old_section.title != new_section.title
    )
    if changed_sections != EXPECTED_CHANGED_SECTIONS:
        raise ControlledPolicyError(
            "controlled scenario requires exactly sections 3, 4, 5, and 6 to change; "
            f"found {changed_sections!r}"
        )

    old_rules = _rules_by_type(extract_candidate_rules(old_policy))
    new_rules = _rules_by_type(extract_candidate_rules(new_policy))

    return (
        PolicyChange(
            change_id=CHANGE_IDS["3"],
            section_id="3",
            category=ChangeCategory.DIAGNOSIS_CRITERIA,
            old_summary=_diagnosis_summary(old_rules[RuleType.DIAGNOSIS_INCLUSION]),
            new_summary=_diagnosis_summary(new_rules[RuleType.DIAGNOSIS_INCLUSION]),
            material=True,
            executable=True,
            human_review_required=False,
            old_evidence=evidence_for(old_policy, "3"),
            new_evidence=evidence_for(new_policy, "3"),
        ),
        PolicyChange(
            change_id=CHANGE_IDS["4"],
            section_id="4",
            category=ChangeCategory.MAXIMUM_SERVICE_UNITS,
            old_summary=_units_summary(old_rules[RuleType.MAXIMUM_UNITS]),
            new_summary=_units_summary(new_rules[RuleType.MAXIMUM_UNITS]),
            material=True,
            executable=True,
            human_review_required=False,
            old_evidence=evidence_for(old_policy, "4"),
            new_evidence=evidence_for(new_policy, "4"),
        ),
        PolicyChange(
            change_id=CHANGE_IDS["5"],
            section_id="5",
            category=ChangeCategory.MODIFIER_OR_DOCUMENTATION,
            old_summary=_modifier_summary(
                old_rules[RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW]
            ),
            new_summary=_modifier_summary(
                new_rules[RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW]
            ),
            material=True,
            executable=True,
            human_review_required=False,
            old_evidence=evidence_for(old_policy, "5"),
            new_evidence=evidence_for(new_policy, "5"),
        ),
        PolicyChange(
            change_id=CHANGE_IDS["6"],
            section_id="6",
            category=ChangeCategory.AMBIGUOUS_CLAUSE,
            old_summary="Contextual transition wording is undefined and non-executable.",
            new_summary="Revised contextual transition wording remains undefined and non-executable.",
            material=True,
            executable=False,
            human_review_required=True,
            old_evidence=evidence_for(old_policy, "6"),
            new_evidence=evidence_for(new_policy, "6"),
        ),
    )


def extract_candidate_rules(policy: PolicyDocument) -> tuple[CandidateRule, ...]:
    version_label = _version_label(policy.version)

    procedure_text = policy.section("2").text
    procedure_match = re.search(
        r"procedure code is `(?P<code>SYN-[A-Z0-9-]+)`", procedure_text
    )
    if procedure_match is None:
        raise ControlledPolicyError("section 2 does not contain the controlled procedure")

    diagnosis_text = policy.section("3").text
    diagnosis_match = re.search(
        r"eligible fictional diagnosis set is (?P<values>.+?)\.", diagnosis_text
    )
    if diagnosis_match is None:
        raise ControlledPolicyError("section 3 does not contain a diagnosis set")
    diagnosis_codes = tuple(
        re.findall(r"`(SYN-[A-Z0-9-]+)`", diagnosis_match.group("values"))
    )
    if not diagnosis_codes:
        raise ControlledPolicyError("section 3 diagnosis set is empty")

    units_text = policy.section("4").text
    units_match = re.search(
        r"maximum service units .*? are `(?P<limit>[0-9]+)` per claim line",
        units_text,
    )
    if units_match is None:
        raise ControlledPolicyError("section 4 does not contain a maximum-units value")

    modifier_text = policy.section("5").text
    if "no dedicated modifier requirement" in modifier_text:
        required_modifier: str | None = None
    else:
        modifier_match = re.search(
            r"must carry fictional modifier `(?P<code>SYN-[A-Z0-9-]+)`",
            modifier_text,
        )
        if modifier_match is None:
            raise ControlledPolicyError(
                "section 5 does not contain a supported modifier requirement"
            )
        required_modifier = modifier_match.group("code")

    ambiguous_text = policy.section("6").text
    ambiguous_match = re.search(
        r"modifier `(?P<code>SYN-[A-Z0-9-]+)`", ambiguous_text
    )
    if ambiguous_match is None:
        raise ControlledPolicyError("section 6 does not contain a review scope marker")

    return (
        CandidateRule(
            rule_id=f"SCOPE-{version_label}",
            policy_id=policy.policy_id,
            policy_version=policy.version,
            change_id=None,
            rule_type=RuleType.PROCEDURE_MATCHING,
            field=ClaimField.PROCEDURE_CODE,
            operator=RuleOperator.EQUALS,
            value=procedure_match.group("code"),
            executable=True,
            evidence=evidence_for(policy, "2"),
        ),
        CandidateRule(
            rule_id=f"DIAG-{version_label}",
            policy_id=policy.policy_id,
            policy_version=policy.version,
            change_id=CHANGE_IDS["3"],
            rule_type=RuleType.DIAGNOSIS_INCLUSION,
            field=ClaimField.DIAGNOSIS_CODES,
            operator=RuleOperator.INTERSECTS,
            value=diagnosis_codes,
            executable=True,
            evidence=evidence_for(policy, "3"),
        ),
        CandidateRule(
            rule_id=f"UNITS-{version_label}",
            policy_id=policy.policy_id,
            policy_version=policy.version,
            change_id=CHANGE_IDS["4"],
            rule_type=RuleType.MAXIMUM_UNITS,
            field=ClaimField.UNITS,
            operator=RuleOperator.LESS_THAN_OR_EQUAL,
            value=int(units_match.group("limit")),
            executable=True,
            evidence=evidence_for(policy, "4"),
        ),
        CandidateRule(
            rule_id=f"MOD-{version_label}",
            policy_id=policy.policy_id,
            policy_version=policy.version,
            change_id=CHANGE_IDS["5"],
            rule_type=RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW,
            field=ClaimField.MODIFIER,
            operator=RuleOperator.MISSING_REQUIRED_VALUE,
            value=required_modifier,
            executable=True,
            evidence=evidence_for(policy, "5"),
        ),
        CandidateRule(
            rule_id=f"AMB-{version_label}",
            policy_id=policy.policy_id,
            policy_version=policy.version,
            change_id=CHANGE_IDS["6"],
            rule_type=RuleType.AMBIGUOUS_HUMAN_REVIEW,
            field=ClaimField.MODIFIER,
            operator=RuleOperator.REVIEW_ONLY,
            value=ambiguous_match.group("code"),
            executable=False,
            evidence=evidence_for(policy, "6"),
        ),
    )


def _version_label(version: str) -> str:
    major = version.split(".", maxsplit=1)[0]
    return f"V{major}"


def _rules_by_type(rules: tuple[CandidateRule, ...]) -> dict[RuleType, CandidateRule]:
    return {rule.rule_type: rule for rule in rules}


def _diagnosis_summary(rule: CandidateRule) -> str:
    assert isinstance(rule.value, tuple)
    return "Eligible set: " + ", ".join(rule.value) + "."


def _units_summary(rule: CandidateRule) -> str:
    assert type(rule.value) is int
    return f"Maximum units per claim line: {rule.value}."


def _modifier_summary(rule: CandidateRule) -> str:
    if rule.value is None:
        return "No dedicated modifier requirement."
    return f"Missing {rule.value} routes to modifier or documentation review."

