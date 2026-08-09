from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from policyimpact.models import (
    CandidateRule,
    Claim,
    ClaimField,
    EvidenceReference,
    PolicyDocument,
    PolicySection,
    RuleOperator,
    RuleType,
    SafeOutcome,
)


VALID_CLAIM = {
    "claim_id": "CLM-900",
    "service_date": "2026-07-10",
    "procedure_code": "SYN-PROC-A1",
    "diagnosis_codes": ["SYN-DX-A1"],
    "modifier": None,
    "units": 1,
}


@pytest.mark.parametrize(
    ("replacement", "expected_fragment"),
    [
        ({"units": 0}, "greater than or equal"),
        ({"procedure_code": "NOT-SYNTHETIC"}, "SYN-prefixed"),
        ({"diagnosis_codes": ["SYN-DX-A1", "SYN-DX-A1"]}, "unique"),
        ({"modifier": "MISSING-PREFIX"}, "SYN-prefixed"),
        ({"patient_name": "Example Person"}, "extra"),
    ],
)
def test_malformed_claims_are_rejected(
    replacement: dict[str, object], expected_fragment: str
) -> None:
    payload = VALID_CLAIM | replacement
    with pytest.raises(ValidationError, match=expected_fragment):
        Claim.model_validate(payload)


def test_modifier_field_is_required_even_when_null_is_valid() -> None:
    payload = dict(VALID_CLAIM)
    payload.pop("modifier")
    with pytest.raises(ValidationError, match="modifier"):
        Claim.model_validate(payload)


def test_unsupported_rule_operator_is_rejected() -> None:
    payload = _valid_rule_payload()
    payload["operator"] = "contains_any"
    with pytest.raises(ValidationError, match="operator"):
        CandidateRule.model_validate(payload)


def test_rule_type_operator_mismatch_is_rejected() -> None:
    payload = _valid_rule_payload()
    payload["operator"] = RuleOperator.EQUALS
    with pytest.raises(ValidationError, match="incompatible"):
        CandidateRule.model_validate(payload)


def test_non_executable_ambiguity_boundary_is_enforced() -> None:
    payload = _valid_rule_payload()
    payload.update(
        {
            "rule_id": "AMB-V1",
            "change_id": "CHG-AMB-004",
            "rule_type": RuleType.AMBIGUOUS_HUMAN_REVIEW,
            "field": ClaimField.MODIFIER,
            "operator": RuleOperator.REVIEW_ONLY,
            "value": "SYN-MOD-TRN",
            "executable": True,
        }
    )
    with pytest.raises(ValidationError, match="cannot be executable"):
        CandidateRule.model_validate(payload)


def test_policy_document_rejects_missing_middle_section() -> None:
    sections = (
        PolicySection(section_id="1", title="One", text="Synthetic content."),
        PolicySection(section_id="3", title="Three", text="Synthetic content."),
    )
    with pytest.raises(ValidationError, match="consecutive"):
        PolicyDocument(
            policy_id="SYN-PAY-TEST",
            version="1.0",
            effective_date=date(2026, 1, 1),
            title="Synthetic test policy",
            synthetic=True,
            synthetic_notice="Synthetic demonstration data only.",
            sections=sections,
        )


def test_safe_outcome_vocabulary_is_exact() -> None:
    assert {outcome.value for outcome in SafeOutcome} == {
        "unchanged",
        "newly_matches_selected_criterion",
        "no_longer_matches_selected_criterion",
        "unit_limit_exceeded",
        "modifier_or_documentation_review_required",
        "ambiguous_human_review",
    }


def _valid_rule_payload() -> dict[str, object]:
    evidence = EvidenceReference(
        policy_id="SYN-PAY-TEST",
        policy_version="1.0",
        section_id="3",
        section_title="Eligible Diagnosis Criterion",
        excerpt="Synthetic evidence.",
    )
    return {
        "rule_id": "DIAG-V1",
        "policy_id": "SYN-PAY-TEST",
        "policy_version": "1.0",
        "change_id": "CHG-DIAG-001",
        "rule_type": RuleType.DIAGNOSIS_INCLUSION,
        "field": ClaimField.DIAGNOSIS_CODES,
        "operator": RuleOperator.INTERSECTS,
        "value": ("SYN-DX-A1",),
        "executable": True,
        "evidence": evidence,
    }

