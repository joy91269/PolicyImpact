"""Deterministic old-versus-new claim comparison with evidence tracing."""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    AuditDecision,
    AuditStatus,
    CandidateRule,
    Claim,
    ClaimImpact,
    ControlledExecutionContext,
    EvidenceReference,
    RuleType,
    SafeOutcome,
)


class RuleConfigurationError(ValueError):
    """Raised when rules or human audit decisions are incomplete or inconsistent."""


class DeterministicRuleEngine:
    """Evaluate only the fixed operators supported by the controlled scenario."""

    def __init__(
        self,
        old_rules: Iterable[CandidateRule],
        new_rules: Iterable[CandidateRule],
        audit_decisions: Iterable[AuditDecision],
        *,
        context: ControlledExecutionContext | None = None,
    ) -> None:
        old_rule_items = tuple(old_rules)
        new_rule_items = tuple(new_rules)
        if context is None:
            # Backward-compatible Phase 1-2 construction. Candidate scope and
            # ambiguity records are converted to non-candidate execution context
            # before any matching occurs.
            context = self._context_from_controlled_rules(
                old_rule_items, new_rule_items
            )
            old_rule_items = self._executable_change_rules(old_rule_items)
            new_rule_items = self._executable_change_rules(new_rule_items)
        elif any(
            rule.rule_type
            in {RuleType.PROCEDURE_MATCHING, RuleType.AMBIGUOUS_HUMAN_REVIEW}
            for rule in (*old_rule_items, *new_rule_items)
        ):
            raise RuleConfigurationError(
                "the reviewed execution path accepts only approved executable candidate rules"
            )

        self.context = context
        self.old_rules = self._index_rules(old_rule_items, "old")
        self.new_rules = self._index_rules(new_rule_items, "new")
        self.audit_decisions = self._index_audits(tuple(audit_decisions))
        self._validate_configuration()

    def compare_claims(self, claims: Iterable[Claim]) -> tuple[ClaimImpact, ...]:
        claim_list = tuple(claims)
        claim_ids = [claim.claim_id for claim in claim_list]
        if len(claim_ids) != len(set(claim_ids)):
            raise RuleConfigurationError("claim IDs must be unique")
        return tuple(self.compare_claim(claim) for claim in claim_list)

    def compare_claim(self, claim: Claim) -> ClaimImpact:
        if claim.procedure_code != self.context.procedure_code:
            return self._impact(
                claim=claim,
                old_outcome=SafeOutcome.UNCHANGED,
                new_outcome=SafeOutcome.UNCHANGED,
                rule_ids=self.context.procedure_trace_ids,
                evidence=self.context.procedure_evidence,
                reason=(
                    f"Procedure {claim.procedure_code} is outside the {self.context.procedure_code} "
                    "scope in both versions."
                ),
            )

        if claim.modifier == self.context.ambiguity_marker:
            return self._impact(
                claim=claim,
                old_outcome=SafeOutcome.AMBIGUOUS_HUMAN_REVIEW,
                new_outcome=SafeOutcome.AMBIGUOUS_HUMAN_REVIEW,
                rule_ids=self.context.ambiguity_trace_ids,
                evidence=self.context.ambiguity_evidence,
                reason=(
                    f"Modifier {claim.modifier} invokes a non-executable clause in both "
                    "versions; deterministic evaluation abstains pending human review."
                ),
            )

        old_diagnosis, new_diagnosis = self._pair(RuleType.DIAGNOSIS_INCLUSION)
        assert isinstance(old_diagnosis.value, tuple)
        assert isinstance(new_diagnosis.value, tuple)
        claim_diagnoses = set(claim.diagnosis_codes)
        old_diagnosis_match = bool(claim_diagnoses.intersection(old_diagnosis.value))
        new_diagnosis_match = bool(claim_diagnoses.intersection(new_diagnosis.value))
        if old_diagnosis_match and not new_diagnosis_match:
            return self._impact(
                claim=claim,
                old_outcome=SafeOutcome.UNCHANGED,
                new_outcome=SafeOutcome.NO_LONGER_MATCHES_SELECTED_CRITERION,
                rule_ids=(old_diagnosis.rule_id, new_diagnosis.rule_id),
                evidence=(old_diagnosis.evidence, new_diagnosis.evidence),
                reason=(
                    "Diagnosis codes intersect the version 1.0 set but not the "
                    "version 2.0 set."
                ),
            )
        if not old_diagnosis_match and new_diagnosis_match:
            return self._impact(
                claim=claim,
                old_outcome=SafeOutcome.UNCHANGED,
                new_outcome=SafeOutcome.NEWLY_MATCHES_SELECTED_CRITERION,
                rule_ids=(old_diagnosis.rule_id, new_diagnosis.rule_id),
                evidence=(old_diagnosis.evidence, new_diagnosis.evidence),
                reason=(
                    "Diagnosis codes do not intersect the version 1.0 set and intersect "
                    "the version 2.0 set."
                ),
            )

        old_units, new_units = self._pair(RuleType.MAXIMUM_UNITS)
        assert type(old_units.value) is int
        assert type(new_units.value) is int
        old_units_exceeded = claim.units > old_units.value
        new_units_exceeded = claim.units > new_units.value
        if old_units_exceeded or new_units_exceeded:
            old_outcome = (
                SafeOutcome.UNIT_LIMIT_EXCEEDED
                if old_units_exceeded
                else SafeOutcome.UNCHANGED
            )
            new_outcome = (
                SafeOutcome.UNIT_LIMIT_EXCEEDED
                if new_units_exceeded
                else SafeOutcome.UNCHANGED
            )
            if old_units_exceeded and new_units_exceeded:
                reason = (
                    f"Units exceed both version 1.0 maximum of {old_units.value} and "
                    f"version 2.0 maximum of {new_units.value}."
                )
            elif new_units_exceeded:
                reason = (
                    f"Units are within the version 1.0 maximum of {old_units.value} and "
                    f"exceed the version 2.0 maximum of {new_units.value}."
                )
            else:
                reason = (
                    f"Units exceed the version 1.0 maximum of {old_units.value} and are "
                    f"within the version 2.0 maximum of {new_units.value}."
                )
            return self._impact(
                claim=claim,
                old_outcome=old_outcome,
                new_outcome=new_outcome,
                rule_ids=(old_units.rule_id, new_units.rule_id),
                evidence=(old_units.evidence, new_units.evidence),
                reason=reason,
            )

        old_modifier, new_modifier = self._pair(
            RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW
        )
        old_modifier_missing = (
            isinstance(old_modifier.value, str) and claim.modifier != old_modifier.value
        )
        new_modifier_missing = (
            isinstance(new_modifier.value, str) and claim.modifier != new_modifier.value
        )
        if old_modifier_missing or new_modifier_missing:
            old_outcome = (
                SafeOutcome.MODIFIER_OR_DOCUMENTATION_REVIEW_REQUIRED
                if old_modifier_missing
                else SafeOutcome.UNCHANGED
            )
            new_outcome = (
                SafeOutcome.MODIFIER_OR_DOCUMENTATION_REVIEW_REQUIRED
                if new_modifier_missing
                else SafeOutcome.UNCHANGED
            )
            required = new_modifier.value if new_modifier_missing else old_modifier.value
            reason = (
                f"No {required} modifier is present; version 2.0 routes the claim to "
                "modifier or documentation review, while version 1.0 has no dedicated "
                "modifier requirement."
            )
            return self._impact(
                claim=claim,
                old_outcome=old_outcome,
                new_outcome=new_outcome,
                rule_ids=(old_modifier.rule_id, new_modifier.rule_id),
                evidence=(old_modifier.evidence, new_modifier.evidence),
                reason=reason,
            )

        if claim.units == new_units.value and old_units.value != new_units.value:
            return self._impact(
                claim=claim,
                old_outcome=SafeOutcome.UNCHANGED,
                new_outcome=SafeOutcome.UNCHANGED,
                rule_ids=(old_units.rule_id, new_units.rule_id),
                evidence=(old_units.evidence, new_units.evidence),
                reason=(
                    f"Units equal the version 2.0 maximum of {new_units.value} and do "
                    "not exceed either version's limit."
                ),
            )

        if old_diagnosis_match and new_diagnosis_match:
            diagnosis_reason = (
                "Diagnosis codes intersect both versions' eligible diagnosis sets."
            )
        else:
            diagnosis_reason = (
                "Diagnosis codes intersect neither version's eligible diagnosis set."
            )
        return self._impact(
            claim=claim,
            old_outcome=SafeOutcome.UNCHANGED,
            new_outcome=SafeOutcome.UNCHANGED,
            rule_ids=(old_diagnosis.rule_id, new_diagnosis.rule_id),
            evidence=(old_diagnosis.evidence, new_diagnosis.evidence),
            reason=diagnosis_reason,
        )

    def _impact(
        self,
        *,
        claim: Claim,
        old_outcome: SafeOutcome,
        new_outcome: SafeOutcome,
        rule_ids: tuple[str, str],
        evidence: tuple[EvidenceReference, EvidenceReference],
        reason: str,
    ) -> ClaimImpact:
        return ClaimImpact(
            claim_id=claim.claim_id,
            old_outcome=old_outcome,
            new_outcome=new_outcome,
            affected=old_outcome is not new_outcome,
            human_review_required=(
                old_outcome
                in {
                    SafeOutcome.MODIFIER_OR_DOCUMENTATION_REVIEW_REQUIRED,
                    SafeOutcome.AMBIGUOUS_HUMAN_REVIEW,
                }
                or new_outcome
                in {
                    SafeOutcome.MODIFIER_OR_DOCUMENTATION_REVIEW_REQUIRED,
                    SafeOutcome.AMBIGUOUS_HUMAN_REVIEW,
                }
            ),
            matched_rule_ids=rule_ids,
            evidence_references=evidence,
            reason=reason,
        )

    @staticmethod
    def _index_rules(
        rules: tuple[CandidateRule, ...], label: str
    ) -> dict[RuleType, CandidateRule]:
        by_type = {rule.rule_type: rule for rule in rules}
        if len(by_type) != len(rules):
            raise RuleConfigurationError(f"{label} rules contain duplicate rule types")
        required = {
            RuleType.DIAGNOSIS_INCLUSION,
            RuleType.MAXIMUM_UNITS,
            RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW,
        }
        missing = required - by_type.keys()
        if missing:
            names = ", ".join(sorted(rule_type.value for rule_type in missing))
            raise RuleConfigurationError(f"{label} rules are missing: {names}")
        return by_type

    @staticmethod
    def _index_audits(
        decisions: tuple[AuditDecision, ...],
    ) -> dict[str, AuditDecision]:
        indexed = {decision.change_id: decision for decision in decisions}
        if len(indexed) != len(decisions):
            raise RuleConfigurationError("audit decisions contain duplicate change IDs")
        return indexed

    def _validate_configuration(self) -> None:
        for rule_type in (
            RuleType.DIAGNOSIS_INCLUSION,
            RuleType.MAXIMUM_UNITS,
            RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW,
        ):
            old_rule, new_rule = self._pair(rule_type)
            if old_rule.policy_id != new_rule.policy_id:
                raise RuleConfigurationError("old and new rules must share a policy ID")
            if old_rule.change_id != new_rule.change_id:
                raise RuleConfigurationError("paired rules must share a change ID")
            if old_rule.change_id is None:
                continue
            decision = self.audit_decisions.get(old_rule.change_id)
            if decision is None:
                raise RuleConfigurationError(
                    f"missing audit decision for {old_rule.change_id}"
                )
            expected_ids = {old_rule.rule_id, new_rule.rule_id}
            if set(decision.rule_ids) != expected_ids:
                raise RuleConfigurationError(
                    f"audit decision {decision.change_id} does not cover the rule pair"
                )
            if old_rule.executable and new_rule.executable:
                if decision.status is not AuditStatus.ACCEPTED_FOR_EXECUTION:
                    raise RuleConfigurationError(
                        f"executable rule pair {decision.change_id} was not accepted"
                    )
            else:
                if decision.status is not AuditStatus.REQUIRES_HUMAN_REVIEW:
                    raise RuleConfigurationError(
                        f"non-executable rule pair {decision.change_id} must remain in review"
                    )

        ambiguity_decision = self.audit_decisions.get(
            self.context.ambiguity_change_id
        )
        if ambiguity_decision is None:
            raise RuleConfigurationError(
                f"missing audit decision for {self.context.ambiguity_change_id}"
            )
        if ambiguity_decision.status is not AuditStatus.REQUIRES_HUMAN_REVIEW:
            raise RuleConfigurationError(
                "the ambiguity boundary must remain in review and non-executable"
            )

    def _pair(self, rule_type: RuleType) -> tuple[CandidateRule, CandidateRule]:
        return self.old_rules[rule_type], self.new_rules[rule_type]

    @staticmethod
    def _executable_change_rules(
        rules: tuple[CandidateRule, ...],
    ) -> tuple[CandidateRule, ...]:
        return tuple(
            rule
            for rule in rules
            if rule.rule_type
            in {
                RuleType.DIAGNOSIS_INCLUSION,
                RuleType.MAXIMUM_UNITS,
                RuleType.MODIFIER_OR_DOCUMENTATION_REVIEW,
            }
        )

    @classmethod
    def _context_from_controlled_rules(
        cls,
        old_rules: tuple[CandidateRule, ...],
        new_rules: tuple[CandidateRule, ...],
    ) -> ControlledExecutionContext:
        old = {rule.rule_type: rule for rule in old_rules}
        new = {rule.rule_type: rule for rule in new_rules}
        try:
            old_scope = old[RuleType.PROCEDURE_MATCHING]
            new_scope = new[RuleType.PROCEDURE_MATCHING]
            old_ambiguity = old[RuleType.AMBIGUOUS_HUMAN_REVIEW]
            new_ambiguity = new[RuleType.AMBIGUOUS_HUMAN_REVIEW]
        except KeyError as exc:
            raise RuleConfigurationError(
                "controlled rules are missing procedure or ambiguity context"
            ) from exc
        if old_scope.value != new_scope.value or not isinstance(old_scope.value, str):
            raise RuleConfigurationError("procedure scope changes are not supported")
        if (
            old_ambiguity.value != new_ambiguity.value
            or not isinstance(old_ambiguity.value, str)
        ):
            raise RuleConfigurationError("ambiguity markers must match across versions")
        if old_ambiguity.change_id is None:
            raise RuleConfigurationError("ambiguity context must retain its change ID")
        return ControlledExecutionContext(
            procedure_code=old_scope.value,
            procedure_trace_ids=(old_scope.rule_id, new_scope.rule_id),
            procedure_evidence=(old_scope.evidence, new_scope.evidence),
            ambiguity_marker=old_ambiguity.value,
            ambiguity_change_id=old_ambiguity.change_id,
            ambiguity_trace_ids=(old_ambiguity.rule_id, new_ambiguity.rule_id),
            ambiguity_evidence=(old_ambiguity.evidence, new_ambiguity.evidence),
        )


def controlled_execution_context(
    old_rules: Iterable[CandidateRule],
    new_rules: Iterable[CandidateRule],
) -> ControlledExecutionContext:
    """Build trusted non-candidate scope/review context before engine entry."""

    return DeterministicRuleEngine._context_from_controlled_rules(
        tuple(old_rules), tuple(new_rules)
    )
