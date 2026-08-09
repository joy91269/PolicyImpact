"""One-revision agent workflow and explicit human execution gate."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from pydantic import TypeAdapter

from .agents import AgentProvider
from .engine import DeterministicRuleEngine, controlled_execution_context
from .models import (
    AgentReviewRun,
    AgentRound,
    AuditDecision,
    AuditorDisposition,
    AuditStatus,
    ClaimImpact,
    ExecutionAuthorization,
    HumanApproval,
    HumanApprovalStatus,
)
from .scenario import ScenarioBundle


class HumanApprovalRequiredError(RuntimeError):
    """Raised when code attempts execution without the complete approval gate."""


def run_agent_review(
    scenario: ScenarioBundle, provider: AgentProvider
) -> AgentReviewRun:
    """Run exactly one analyst/auditor revision cycle."""

    initial_analysis = provider.analyze(
        scenario, round_name=AgentRound.INITIAL
    )
    initial_audit = provider.audit(
        scenario, initial_analysis, round_name=AgentRound.INITIAL
    )
    revised_analysis = provider.analyze(
        scenario,
        round_name=AgentRound.REVISED,
        audit_feedback=initial_audit,
    )
    final_audit = provider.audit(
        scenario, revised_analysis, round_name=AgentRound.FINAL
    )
    review = AgentReviewRun(
        provider_mode=provider.mode,
        provider_label=provider.label,
        recording_path=provider.recording_path,
        live_model_invoked=provider.live_model_invoked,
        revision_round_count=1,
        initial_analysis=initial_analysis,
        initial_audit=initial_audit,
        revised_analysis=revised_analysis,
        final_audit=final_audit,
    )
    expected_ids = {item.change_id for item in scenario.changes}
    observed_ids = {
        item.change.change_id for item in review.revised_analysis.findings
    }
    if observed_ids != expected_ids:
        raise ValueError(
            "agent review must cover exactly the controlled scenario change IDs"
        )
    expected_changes = {item.change_id: item for item in scenario.changes}
    expected_old_rules = {
        item.change_id: item for item in scenario.old_rules if item.change_id is not None
    }
    expected_new_rules = {
        item.change_id: item for item in scenario.new_rules if item.change_id is not None
    }
    policies = {
        scenario.old_policy.version: scenario.old_policy,
        scenario.new_policy.version: scenario.new_policy,
    }
    for analysis in (review.initial_analysis, review.revised_analysis):
        for finding in analysis.findings:
            change_id = finding.change.change_id
            expected_change = expected_changes[change_id]
            if (
                finding.change.section_id != expected_change.section_id
                or finding.change.category is not expected_change.category
                or finding.change.executable != expected_change.executable
                or finding.change.human_review_required
                != expected_change.human_review_required
            ):
                raise ValueError(
                    f"agent finding {change_id} conflicts with the controlled change boundary"
                )
            for evidence in (
                finding.change.old_evidence,
                finding.change.new_evidence,
                finding.old_rule.evidence,
                finding.new_rule.evidence,
            ):
                policy = policies.get(evidence.policy_version)
                if policy is None or evidence.policy_id != policy.policy_id:
                    raise ValueError(
                        f"agent finding {change_id} cites an unknown policy version"
                    )
                section = policy.section(evidence.section_id)
                if (
                    evidence.section_title != section.title
                    or evidence.excerpt != section.text
                ):
                    raise ValueError(
                        f"agent finding {change_id} does not preserve exact policy evidence"
                    )
            if finding.old_rule.evidence != finding.change.old_evidence:
                raise ValueError(f"agent finding {change_id} has mismatched old evidence")
            if finding.new_rule.evidence != finding.change.new_evidence:
                raise ValueError(f"agent finding {change_id} has mismatched new evidence")
            if (
                finding.old_rule.rule_type
                is not expected_old_rules[change_id].rule_type
                or finding.new_rule.rule_type
                is not expected_new_rules[change_id].rule_type
            ):
                raise ValueError(
                    f"agent finding {change_id} uses an unsupported rule type for the section"
                )
    return review


def load_human_approvals(path: str | Path) -> tuple[HumanApproval, ...]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return TypeAdapter(tuple[HumanApproval, ...]).validate_python(raw)


def authorize_execution(
    review: AgentReviewRun,
    human_approvals: Iterable[HumanApproval],
) -> ExecutionAuthorization:
    """Translate final decisions into the deterministic-engine execution gate.

    Every executable pair needs both an auditor ``accept`` and an explicit human
    ``approved_for_demo_execution`` record. Reject, abstain, or missing approval
    remains visible and blocks execution. Non-executable ambiguity is retained as
    ``requires_human_review`` and never converted into an executable rule.
    """

    approval_items = tuple(human_approvals)
    approvals = {item.change_id: item for item in approval_items}
    if len(approvals) != len(approval_items):
        raise HumanApprovalRequiredError("human approvals contain duplicate change IDs")
    final = {item.change_id: item for item in review.final_audit.findings}
    findings = {
        item.change.change_id: item for item in review.revised_analysis.findings
    }
    unknown_approval_ids = approvals.keys() - findings.keys()
    if unknown_approval_ids:
        raise HumanApprovalRequiredError(
            "human approvals contain unknown change IDs: "
            + ", ".join(sorted(unknown_approval_ids))
        )
    decisions: list[AuditDecision] = []
    approved: list[str] = []
    blocked: list[str] = []

    for change_id, finding in findings.items():
        auditor = final[change_id]
        rule_ids = (finding.old_rule.rule_id, finding.new_rule.rule_id)
        if not finding.change.executable:
            decisions.append(
                AuditDecision(
                    change_id=change_id,
                    status=AuditStatus.REQUIRES_HUMAN_REVIEW,
                    rule_ids=rule_ids,
                    reviewer="Evidence Auditor role; non-executable boundary",
                    rationale=auditor.concise_critique,
                )
            )
            continue

        approval = approvals.get(change_id)
        is_authorized = (
            auditor.disposition is AuditorDisposition.ACCEPT
            and auditor.evidence_supported
            and auditor.rule_pair_supported
            and approval is not None
            and approval.status is HumanApprovalStatus.APPROVED
        )
        if is_authorized:
            approved.append(change_id)
            decisions.append(
                AuditDecision(
                    change_id=change_id,
                    status=AuditStatus.ACCEPTED_FOR_EXECUTION,
                    rule_ids=rule_ids,
                    reviewer=approval.reviewer,
                    rationale=(
                        "Evidence Auditor accepted the pair; explicit human demo "
                        f"approval recorded: {approval.rationale}"
                    ),
                )
            )
        else:
            blocked.append(change_id)
            human_rationale = (
                approval.rationale if approval is not None else "No human approval recorded."
            )
            decisions.append(
                AuditDecision(
                    change_id=change_id,
                    status=AuditStatus.REJECTED_FOR_EXECUTION,
                    rule_ids=rule_ids,
                    reviewer=(approval.reviewer if approval else "Approval gate"),
                    rationale=(
                        f"Final auditor disposition={auditor.disposition.value}; "
                        f"{human_rationale}"
                    ),
                )
            )

    allowed = not blocked
    reason = (
        "All three executable rule pairs passed final evidence audit and explicit "
        "human demo approval; the ambiguity pair remains non-executable."
        if allowed
        else "Execution blocked because one or more executable rule pairs lacks both "
        "final auditor acceptance and explicit human approval."
    )
    return ExecutionAuthorization(
        execution_allowed=allowed,
        approved_change_ids=tuple(approved),
        blocked_change_ids=tuple(blocked),
        audit_decisions=tuple(decisions),
        reason=reason,
    )


def execute_authorized_claim_review(
    scenario: ScenarioBundle,
    review: AgentReviewRun,
    authorization: ExecutionAuthorization,
) -> tuple[ClaimImpact, ...]:
    if not authorization.execution_allowed:
        raise HumanApprovalRequiredError(authorization.reason)

    approved_ids = set(authorization.approved_change_ids)
    revised_findings = {
        item.change.change_id: item for item in review.revised_analysis.findings
    }
    old_rules = tuple(
        revised_findings[change_id].old_rule
        for change_id in authorization.approved_change_ids
    )
    new_rules = tuple(
        revised_findings[change_id].new_rule
        for change_id in authorization.approved_change_ids
    )
    if any(rule.change_id not in approved_ids for rule in (*old_rules, *new_rules)):
        raise HumanApprovalRequiredError(
            "the executable rule collection contains an unapproved change"
        )
    return DeterministicRuleEngine(
        old_rules,
        new_rules,
        authorization.audit_decisions,
        context=controlled_execution_context(
            scenario.old_rules, scenario.new_rules
        ),
    ).compare_claims(scenario.claims)
