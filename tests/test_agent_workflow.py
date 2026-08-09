from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from policyimpact.agents import OfflineFixtureProvider
from policyimpact.models import (
    AgentRound,
    AuditorDisposition,
    HumanApproval,
    HumanApprovalStatus,
    ProviderMode,
)
from policyimpact.scenario import load_scenario
from policyimpact.workflow import (
    HumanApprovalRequiredError,
    authorize_execution,
    execute_authorized_claim_review,
    load_human_approvals,
    run_agent_review,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def agent_scenario():
    scenario = load_scenario(PROJECT_ROOT)
    provider = OfflineFixtureProvider(
        PROJECT_ROOT / "data/agent_fixtures/offline_agent_review.json"
    )
    review = run_agent_review(scenario, provider)
    return scenario, review


def test_offline_recording_runs_exactly_one_revision_round(agent_scenario) -> None:
    _, review = agent_scenario
    assert review.provider_mode is ProviderMode.OFFLINE_REVIEWED_FIXTURE
    assert review.live_model_invoked is False
    assert review.revision_round_count == 1
    assert review.initial_analysis.round is AgentRound.INITIAL
    assert review.revised_analysis.round is AgentRound.REVISED
    assert review.final_audit.round is AgentRound.FINAL
    assert review.recording_path == "data/agent_fixtures/offline_agent_review.json"


def test_auditor_requests_bounded_revision_then_closes(agent_scenario) -> None:
    _, review = agent_scenario
    initial = {item.change_id: item for item in review.initial_audit.findings}
    final = {item.change_id: item for item in review.final_audit.findings}
    assert initial["CHG-MOD-003"].disposition is AuditorDisposition.REVISE
    assert initial["CHG-MOD-003"].requested_revision
    assert final["CHG-MOD-003"].disposition is AuditorDisposition.ACCEPT
    assert final["CHG-AMB-004"].disposition is AuditorDisposition.ABSTAIN
    assert all(item.disposition is not AuditorDisposition.REVISE for item in final.values())


def test_typed_fixture_rejects_undeclared_fields() -> None:
    raw = {
        "role": "evidence_auditor",
        "round": "final",
        "findings": [],
        "concise_summary": "Synthetic test.",
        "hidden_reasoning": "must not be accepted",
    }
    from policyimpact.models import AuditorResponse

    with pytest.raises(ValidationError, match="extra"):
        AuditorResponse.model_validate(raw)


def test_no_human_approval_means_no_execution(agent_scenario) -> None:
    scenario, review = agent_scenario
    authorization = authorize_execution(review, ())
    assert authorization.execution_allowed is False
    assert set(authorization.blocked_change_ids) == {
        "CHG-DIAG-001",
        "CHG-UNITS-002",
        "CHG-MOD-003",
    }
    with pytest.raises(HumanApprovalRequiredError):
        execute_authorized_claim_review(scenario, review, authorization)


def test_explicit_demo_approvals_unlock_only_accepted_pairs(agent_scenario) -> None:
    scenario, review = agent_scenario
    approvals = load_human_approvals(
        PROJECT_ROOT / "data/ground_truth/demo_human_approvals.json"
    )
    authorization = authorize_execution(review, approvals)
    assert authorization.execution_allowed is True
    assert set(authorization.approved_change_ids) == {
        "CHG-DIAG-001",
        "CHG-UNITS-002",
        "CHG-MOD-003",
    }
    decisions = {item.change_id: item.status.value for item in authorization.audit_decisions}
    assert decisions["CHG-AMB-004"] == "requires_human_review"
    impacts = execute_authorized_claim_review(scenario, review, authorization)
    assert len(impacts) == 16
    assert set(authorization.approved_change_ids) == {
        rule.change_id
        for finding in review.revised_analysis.findings
        for rule in (finding.old_rule, finding.new_rule)
        if finding.change.executable
    }


def test_human_rejection_blocks_an_auditor_accepted_rule(agent_scenario) -> None:
    _, review = agent_scenario
    approvals = list(
        load_human_approvals(
            PROJECT_ROOT / "data/ground_truth/demo_human_approvals.json"
        )
    )
    approvals[0] = HumanApproval(
        change_id=approvals[0].change_id,
        status=HumanApprovalStatus.REJECTED,
        reviewer="Unit test reviewer",
        rationale="Deliberate rejection verifies the gate.",
    )
    authorization = authorize_execution(review, approvals)
    assert authorization.execution_allowed is False
    assert approvals[0].change_id in authorization.blocked_change_ids


def test_unknown_human_approval_is_rejected(agent_scenario) -> None:
    _, review = agent_scenario
    approval = HumanApproval(
        change_id="CHG-FAKE-999",
        status=HumanApprovalStatus.APPROVED,
        reviewer="Unit test reviewer",
        rationale="Unknown change IDs must not pass the gate.",
    )
    with pytest.raises(HumanApprovalRequiredError, match="unknown change IDs"):
        authorize_execution(review, (approval,))


def test_offline_recording_path_is_stable_when_parent_is_named_data(
    tmp_path: Path,
) -> None:
    source = PROJECT_ROOT / "data/agent_fixtures/offline_agent_review.json"
    nested = (
        tmp_path
        / "data"
        / "PolicyImpact"
        / "data"
        / "agent_fixtures"
        / "offline_agent_review.json"
    )
    nested.parent.mkdir(parents=True)
    nested.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    provider = OfflineFixtureProvider(nested)

    assert provider.recording_path == "data/agent_fixtures/offline_agent_review.json"
