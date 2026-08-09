"""Typed domain models and validation for the controlled demonstration."""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SYNTHETIC_CODE_PATTERN = re.compile(r"^SYN-[A-Z0-9]+(?:-[A-Z0-9]+)*$")


class StrictModel(BaseModel):
    """Base model that rejects undeclared input and remains immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ChangeCategory(StrEnum):
    DIAGNOSIS_CRITERIA = "diagnosis_criteria"
    MAXIMUM_SERVICE_UNITS = "maximum_service_units"
    MODIFIER_OR_DOCUMENTATION = "modifier_or_documentation"
    AMBIGUOUS_CLAUSE = "ambiguous_clause"


class RuleType(StrEnum):
    PROCEDURE_MATCHING = "procedure_matching"
    DIAGNOSIS_INCLUSION = "diagnosis_inclusion"
    MAXIMUM_UNITS = "maximum_units"
    MODIFIER_OR_DOCUMENTATION_REVIEW = "modifier_or_documentation_review"
    AMBIGUOUS_HUMAN_REVIEW = "ambiguous_human_review"


class ClaimField(StrEnum):
    PROCEDURE_CODE = "procedure_code"
    DIAGNOSIS_CODES = "diagnosis_codes"
    UNITS = "units"
    MODIFIER = "modifier"


class RuleOperator(StrEnum):
    EQUALS = "equals"
    INTERSECTS = "intersects"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    MISSING_REQUIRED_VALUE = "missing_required_value"
    REVIEW_ONLY = "review_only"


class AuditStatus(StrEnum):
    ACCEPTED_FOR_EXECUTION = "accepted_for_execution"
    REJECTED_FOR_EXECUTION = "rejected_for_execution"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class SafeOutcome(StrEnum):
    UNCHANGED = "unchanged"
    NEWLY_MATCHES_SELECTED_CRITERION = "newly_matches_selected_criterion"
    NO_LONGER_MATCHES_SELECTED_CRITERION = "no_longer_matches_selected_criterion"
    UNIT_LIMIT_EXCEEDED = "unit_limit_exceeded"
    MODIFIER_OR_DOCUMENTATION_REVIEW_REQUIRED = (
        "modifier_or_documentation_review_required"
    )
    AMBIGUOUS_HUMAN_REVIEW = "ambiguous_human_review"


class AgentRound(StrEnum):
    INITIAL = "initial"
    REVISED = "revised"
    FINAL = "final"


class AuditorDisposition(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    REVISE = "revise"
    ABSTAIN = "abstain"


class ProviderMode(StrEnum):
    OFFLINE_REVIEWED_FIXTURE = "offline_reviewed_demo_fixture"
    LIVE_MODEL = "live_model"


class HumanApprovalStatus(StrEnum):
    APPROVED = "approved_for_demo_execution"
    REJECTED = "rejected_for_demo_execution"


class PolicySection(StrictModel):
    section_id: str = Field(pattern=r"^[1-9][0-9]*$")
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


class PolicyDocument(StrictModel):
    policy_id: str = Field(pattern=r"^SYN-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    effective_date: date
    title: str = Field(min_length=1)
    synthetic: Literal[True]
    synthetic_notice: str = Field(min_length=1)
    sections: tuple[PolicySection, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sections(self) -> "PolicyDocument":
        ids = [int(section.section_id) for section in self.sections]
        if len(ids) != len(set(ids)):
            raise ValueError("policy section IDs must be unique")
        if ids != list(range(1, max(ids) + 1)):
            raise ValueError("policy sections must be consecutive and begin with section 1")
        if "synthetic demonstration data" not in self.synthetic_notice.lower():
            raise ValueError("policy must contain an explicit synthetic data notice")
        return self

    def section(self, section_id: str) -> PolicySection:
        for section in self.sections:
            if section.section_id == section_id:
                return section
        raise KeyError(f"policy section {section_id!r} is missing")


class EvidenceReference(StrictModel):
    policy_id: str = Field(pattern=r"^SYN-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
    policy_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    section_id: str = Field(pattern=r"^[1-9][0-9]*$")
    section_title: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)


class PolicyChange(StrictModel):
    change_id: str = Field(pattern=r"^CHG-[A-Z]+-[0-9]{3}$")
    section_id: str = Field(pattern=r"^[1-9][0-9]*$")
    category: ChangeCategory
    old_summary: str = Field(min_length=1)
    new_summary: str = Field(min_length=1)
    material: Literal[True]
    executable: bool
    human_review_required: bool
    old_evidence: EvidenceReference
    new_evidence: EvidenceReference

    @model_validator(mode="after")
    def validate_execution_boundary(self) -> "PolicyChange":
        is_ambiguous = self.category is ChangeCategory.AMBIGUOUS_CLAUSE
        if is_ambiguous and (self.executable or not self.human_review_required):
            raise ValueError("ambiguous changes must be non-executable and require review")
        if not is_ambiguous and (not self.executable or self.human_review_required):
            raise ValueError("controlled non-ambiguous changes must be executable")
        if self.old_evidence.section_id != self.section_id:
            raise ValueError("old evidence must reference the changed section")
        if self.new_evidence.section_id != self.section_id:
            raise ValueError("new evidence must reference the changed section")
        return self


RuleValue = str | int | tuple[str, ...] | None


class CandidateRule(StrictModel):
    rule_id: str = Field(pattern=r"^[A-Z]+-V[0-9]+$")
    policy_id: str = Field(pattern=r"^SYN-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
    policy_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    change_id: str | None = Field(pattern=r"^CHG-[A-Z]+-[0-9]{3}$")
    rule_type: RuleType
    field: ClaimField
    operator: RuleOperator
    value: RuleValue
    executable: bool
    evidence: EvidenceReference

    @model_validator(mode="after")
    def validate_rule_shape(self) -> "CandidateRule":
        combinations = {
            RuleType.PROCEDURE_MATCHING: (
                ClaimField.PROCEDURE_CODE,
                RuleOperator.EQUALS,
            ),
            RuleType.DIAGNOSIS_INCLUSION: (
                ClaimField.DIAGNOSIS_CODES,
                RuleOperator.INTERSECTS,
            ),
            RuleType.MAXIMUM_UNITS: (
                ClaimField.UNITS,
                RuleOperator.LESS_THAN_OR_EQUAL,
            ),
            RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW: (
                ClaimField.MODIFIER,
                RuleOperator.MISSING_REQUIRED_VALUE,
            ),
            RuleType.AMBIGUOUS_HUMAN_REVIEW: (
                ClaimField.MODIFIER,
                RuleOperator.REVIEW_ONLY,
            ),
        }
        expected_field, expected_operator = combinations[self.rule_type]
        if self.field is not expected_field or self.operator is not expected_operator:
            raise ValueError("rule type, field, and operator are incompatible")

        if self.rule_type is RuleType.PROCEDURE_MATCHING:
            self._require_synthetic_code(self.value, "procedure rule value")
        elif self.rule_type is RuleType.DIAGNOSIS_INCLUSION:
            if not isinstance(self.value, tuple) or not self.value:
                raise ValueError("diagnosis rule value must be a non-empty code tuple")
            for code in self.value:
                self._require_synthetic_code(code, "diagnosis rule value")
            if len(self.value) != len(set(self.value)):
                raise ValueError("diagnosis rule codes must be unique")
        elif self.rule_type is RuleType.MAXIMUM_UNITS:
            if type(self.value) is not int or self.value < 1:
                raise ValueError("maximum-units rule value must be a positive integer")
        elif self.rule_type is RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW:
            if self.value is not None:
                self._require_synthetic_code(self.value, "modifier rule value")
        elif self.rule_type is RuleType.AMBIGUOUS_HUMAN_REVIEW:
            self._require_synthetic_code(self.value, "ambiguous scope marker")

        if self.rule_type is RuleType.AMBIGUOUS_HUMAN_REVIEW:
            if self.executable:
                raise ValueError("ambiguous review rules cannot be executable")
        elif not self.executable:
            raise ValueError("controlled executable rule types must be marked executable")

        if self.evidence.policy_id != self.policy_id:
            raise ValueError("rule evidence policy ID does not match the rule")
        if self.evidence.policy_version != self.policy_version:
            raise ValueError("rule evidence version does not match the rule")
        return self

    @staticmethod
    def _require_synthetic_code(value: object, label: str) -> None:
        if not isinstance(value, str) or not SYNTHETIC_CODE_PATTERN.fullmatch(value):
            raise ValueError(f"{label} must be a fictional SYN-prefixed code")


class AuditDecision(StrictModel):
    change_id: str = Field(pattern=r"^CHG-[A-Z]+-[0-9]{3}$")
    status: AuditStatus
    rule_ids: tuple[str, ...] = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    rationale: str = Field(min_length=1)

    @field_validator("rule_ids")
    @classmethod
    def unique_rule_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("audit rule IDs must be unique")
        return value


class Claim(StrictModel):
    claim_id: str = Field(pattern=r"^CLM-[0-9]{3}$")
    service_date: date
    procedure_code: str
    diagnosis_codes: tuple[str, ...] = Field(min_length=1)
    modifier: str | None
    units: int = Field(ge=1, le=99)

    @field_validator("procedure_code")
    @classmethod
    def validate_procedure_code(cls, value: str) -> str:
        if not SYNTHETIC_CODE_PATTERN.fullmatch(value):
            raise ValueError("procedure code must be a fictional SYN-prefixed code")
        return value

    @field_validator("diagnosis_codes")
    @classmethod
    def validate_diagnosis_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("diagnosis codes must be unique")
        if any(not SYNTHETIC_CODE_PATTERN.fullmatch(code) for code in value):
            raise ValueError("diagnosis codes must be fictional SYN-prefixed codes")
        return value

    @field_validator("modifier")
    @classmethod
    def validate_modifier(cls, value: str | None) -> str | None:
        if value is not None and not SYNTHETIC_CODE_PATTERN.fullmatch(value):
            raise ValueError("modifier must be a fictional SYN-prefixed code")
        return value


class ClaimImpact(StrictModel):
    claim_id: str = Field(pattern=r"^CLM-[0-9]{3}$")
    old_outcome: SafeOutcome
    new_outcome: SafeOutcome
    affected: bool
    human_review_required: bool
    matched_rule_ids: tuple[str, ...] = Field(min_length=1)
    evidence_references: tuple[EvidenceReference, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)

    @field_validator("matched_rule_ids")
    @classmethod
    def unique_matched_rules(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("matched rule IDs must be unique")
        return value

    @model_validator(mode="after")
    def validate_derived_flags(self) -> "ClaimImpact":
        if self.affected != (self.old_outcome is not self.new_outcome):
            raise ValueError("affected must reflect whether old and new outcomes differ")
        review_outcomes = {
            SafeOutcome.MODIFIER_OR_DOCUMENTATION_REVIEW_REQUIRED,
            SafeOutcome.AMBIGUOUS_HUMAN_REVIEW,
        }
        expected_review = (
            self.old_outcome in review_outcomes or self.new_outcome in review_outcomes
        )
        if self.human_review_required != expected_review:
            raise ValueError("human-review flag is inconsistent with the outcomes")
        return self


class AnalystFinding(StrictModel):
    """A concise, evidence-grounded proposal from the Policy Analyst role."""

    change: PolicyChange
    old_rule: CandidateRule
    new_rule: CandidateRule
    qualifications: tuple[str, ...] = Field(min_length=1)
    exceptions: tuple[str, ...] = Field(min_length=1)
    ambiguity_note: str | None
    execution_recommendation: Literal["candidate_for_execution", "human_review_only"]

    @model_validator(mode="after")
    def validate_alignment(self) -> "AnalystFinding":
        if self.old_rule.change_id != self.change.change_id:
            raise ValueError("old rule must match the proposed change")
        if self.new_rule.change_id != self.change.change_id:
            raise ValueError("new rule must match the proposed change")
        if self.old_rule.rule_type is not self.new_rule.rule_type:
            raise ValueError("proposed rule pair must share a rule type")
        if self.change.executable:
            if self.execution_recommendation != "candidate_for_execution":
                raise ValueError("an explicit controlled change must remain a candidate")
        else:
            if self.execution_recommendation != "human_review_only":
                raise ValueError("an ambiguous change must remain human-review only")
            if not self.ambiguity_note:
                raise ValueError("an ambiguous change requires an ambiguity note")
        return self


class AnalystResponse(StrictModel):
    role: Literal["policy_analyst"]
    round: Literal[AgentRound.INITIAL, AgentRound.REVISED]
    findings: tuple[AnalystFinding, ...] = Field(min_length=1)
    concise_summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_findings(self) -> "AnalystResponse":
        ids = [finding.change.change_id for finding in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError("analyst findings must have unique change IDs")
        return self


class AuditorFinding(StrictModel):
    change_id: str = Field(pattern=r"^CHG-[A-Z]+-[0-9]{3}$")
    disposition: AuditorDisposition
    evidence_supported: bool
    rule_pair_supported: bool
    unsupported_assertions: tuple[str, ...]
    concise_critique: str = Field(min_length=1)
    requested_revision: str | None

    @model_validator(mode="after")
    def validate_disposition(self) -> "AuditorFinding":
        if self.disposition is AuditorDisposition.REVISE and not self.requested_revision:
            raise ValueError("a revise decision requires a bounded revision request")
        if self.disposition is not AuditorDisposition.REVISE and self.requested_revision:
            raise ValueError("only revise decisions may request a revision")
        if self.unsupported_assertions and self.evidence_supported:
            raise ValueError("unsupported assertions conflict with evidence_supported")
        return self


class AuditorResponse(StrictModel):
    role: Literal["evidence_auditor"]
    round: Literal[AgentRound.INITIAL, AgentRound.FINAL]
    findings: tuple[AuditorFinding, ...] = Field(min_length=1)
    concise_summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_round(self) -> "AuditorResponse":
        ids = [finding.change_id for finding in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError("auditor findings must have unique change IDs")
        if self.round is AgentRound.FINAL and any(
            item.disposition is AuditorDisposition.REVISE for item in self.findings
        ):
            raise ValueError("the final audit cannot request another revision round")
        return self


class AgentReviewRun(StrictModel):
    provider_mode: ProviderMode
    provider_label: str = Field(min_length=1)
    recording_path: str | None = None
    live_model_invoked: bool
    revision_round_count: Literal[1]
    initial_analysis: AnalystResponse
    initial_audit: AuditorResponse
    revised_analysis: AnalystResponse
    final_audit: AuditorResponse

    @model_validator(mode="after")
    def validate_sequence(self) -> "AgentReviewRun":
        if self.initial_analysis.round is not AgentRound.INITIAL:
            raise ValueError("initial analysis has the wrong round")
        if self.initial_audit.round is not AgentRound.INITIAL:
            raise ValueError("initial audit has the wrong round")
        if self.revised_analysis.round is not AgentRound.REVISED:
            raise ValueError("revised analysis has the wrong round")
        if self.final_audit.round is not AgentRound.FINAL:
            raise ValueError("final audit has the wrong round")
        expected = {
            finding.change.change_id for finding in self.initial_analysis.findings
        }
        observed_sets = (
            {finding.change_id for finding in self.initial_audit.findings},
            {finding.change.change_id for finding in self.revised_analysis.findings},
            {finding.change_id for finding in self.final_audit.findings},
        )
        if any(observed != expected for observed in observed_sets):
            raise ValueError("all review stages must cover the same change IDs")
        if self.provider_mode is ProviderMode.LIVE_MODEL and not self.live_model_invoked:
            raise ValueError("live provider mode must record a live invocation")
        if (
            self.provider_mode is ProviderMode.OFFLINE_REVIEWED_FIXTURE
            and self.live_model_invoked
        ):
            raise ValueError("offline fixture replay cannot claim a live invocation")
        return self


class HumanApproval(StrictModel):
    change_id: str = Field(pattern=r"^CHG-[A-Z]+-[0-9]{3}$")
    status: HumanApprovalStatus
    reviewer: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class ExecutionAuthorization(StrictModel):
    execution_allowed: bool
    approved_change_ids: tuple[str, ...]
    blocked_change_ids: tuple[str, ...]
    audit_decisions: tuple[AuditDecision, ...]
    reason: str = Field(min_length=1)


class ControlledExecutionContext(StrictModel):
    """Non-candidate context for scope checks and mandatory abstention routing.

    The procedure scope is unchanged between policy versions. The ambiguity
    marker identifies records that must be routed to human review; it does not
    encode or execute the undefined clause. Keeping both outside the executable
    candidate-rule collection makes the Phase 3 approval boundary explicit.
    """

    procedure_code: str
    procedure_trace_ids: tuple[str, str]
    procedure_evidence: tuple[EvidenceReference, EvidenceReference]
    ambiguity_marker: str
    ambiguity_change_id: str = Field(pattern=r"^CHG-[A-Z]+-[0-9]{3}$")
    ambiguity_trace_ids: tuple[str, str]
    ambiguity_evidence: tuple[EvidenceReference, EvidenceReference]

    @field_validator("procedure_code", "ambiguity_marker")
    @classmethod
    def validate_synthetic_context_code(cls, value: str) -> str:
        if not SYNTHETIC_CODE_PATTERN.fullmatch(value):
            raise ValueError("execution context codes must be fictional SYN-prefixed codes")
        return value

    @field_validator("procedure_trace_ids", "ambiguity_trace_ids")
    @classmethod
    def validate_context_trace_ids(cls, value: tuple[str, str]) -> tuple[str, str]:
        if len(set(value)) != 2:
            raise ValueError("execution context trace IDs must be a unique old/new pair")
        return value

    @model_validator(mode="after")
    def validate_context_evidence(self) -> "ControlledExecutionContext":
        for evidence_pair in (self.procedure_evidence, self.ambiguity_evidence):
            if evidence_pair[0].policy_id != evidence_pair[1].policy_id:
                raise ValueError("execution context evidence must share a policy ID")
            if evidence_pair[0].policy_version == evidence_pair[1].policy_version:
                raise ValueError("execution context evidence must cover two policy versions")
        return self
