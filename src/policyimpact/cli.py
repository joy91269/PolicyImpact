"""Command-line entry point for the complete reviewed demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agents import select_provider
from .scenario import load_scenario
from .workflow import (
    authorize_execution,
    execute_authorized_claim_review,
    load_human_approvals,
    run_agent_review,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the synthetic PolicyImpact reviewed demonstration."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (defaults to current directory).",
    )
    parser.add_argument(
        "--without-demo-approvals",
        action="store_true",
        help="Demonstrate that execution is blocked when approval records are absent.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.project_root.resolve()
    scenario = load_scenario(root)
    review = run_agent_review(scenario, select_provider(root))
    approvals = (
        ()
        if args.without_demo_approvals
        else load_human_approvals(
            root / "data/ground_truth/demo_human_approvals.json"
        )
    )
    authorization = authorize_execution(review, approvals)
    impacts = (
        execute_authorized_claim_review(scenario, review, authorization)
        if authorization.execution_allowed
        else ()
    )
    payload = {
        "project": "PolicyImpact",
        "synthetic_demonstration_data": True,
        "provider_mode": review.provider_mode.value,
        "live_model_invoked": review.live_model_invoked,
        "revision_round_count": review.revision_round_count,
        "final_audit": review.final_audit.model_dump(mode="json"),
        "authorization": authorization.model_dump(mode="json"),
        "claim_impacts": [item.model_dump(mode="json") for item in impacts],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
