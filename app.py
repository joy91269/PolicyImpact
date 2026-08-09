"""Top-level demonstrator for the complete reviewed PolicyImpact workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from policyimpact.agents import select_provider
from policyimpact.scenario import load_scenario
from policyimpact.workflow import (
    authorize_execution,
    execute_authorized_claim_review,
    load_human_approvals,
    run_agent_review,
)


PROJECT_ROOT = Path(__file__).resolve().parent


def run_demo(
    project_root: Path = PROJECT_ROOT,
    *,
    include_demo_approvals: bool = True,
) -> dict[str, Any]:
    """Run the bounded role workflow, both gates, and deterministic comparison."""

    scenario = load_scenario(project_root)
    review = run_agent_review(scenario, select_provider(project_root))
    approvals = (
        load_human_approvals(
            project_root / "data/ground_truth/demo_human_approvals.json"
        )
        if include_demo_approvals
        else ()
    )
    authorization = authorize_execution(review, approvals)
    impacts = (
        execute_authorized_claim_review(scenario, review, authorization)
        if authorization.execution_allowed
        else ()
    )

    return {
        "project": "PolicyImpact",
        "synthetic_demonstration_data": True,
        "policy_id": scenario.old_policy.policy_id,
        "old_version": scenario.old_policy.version,
        "new_version": scenario.new_policy.version,
        "provider_mode": review.provider_mode.value,
        "live_model_invoked": review.live_model_invoked,
        "revision_round_count": review.revision_round_count,
        "material_change_count": len(scenario.changes),
        "claim_count": len(impacts),
        "changes": [
            finding.change.model_dump(mode="json")
            for finding in review.revised_analysis.findings
        ],
        "final_audit": review.final_audit.model_dump(mode="json"),
        "authorization": authorization.model_dump(mode="json"),
        "claim_impacts": [impact.model_dump(mode="json") for impact in impacts],
    }


def main() -> int:
    print(json.dumps(run_demo(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
