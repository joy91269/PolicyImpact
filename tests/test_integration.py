from __future__ import annotations

import json
from pathlib import Path

from app import run_demo


def test_demo_runs_end_to_end(scenario: dict[str, object]) -> None:
    root = scenario["root"]
    result = run_demo(Path(root))
    assert result["project"] == "PolicyImpact"
    assert result["synthetic_demonstration_data"] is True
    assert result["material_change_count"] == 4
    assert result["claim_count"] == 16
    assert result["revision_round_count"] == 1
    assert result["authorization"]["execution_allowed"] is True
    assert len(result["changes"]) == 4
    assert len(result["claim_impacts"]) == 16
    json.dumps(result)


def test_top_level_demo_cannot_bypass_human_approval(
    scenario: dict[str, object],
) -> None:
    result = run_demo(Path(scenario["root"]), include_demo_approvals=False)
    assert result["authorization"]["execution_allowed"] is False
    assert result["claim_count"] == 0
    assert result["claim_impacts"] == []
