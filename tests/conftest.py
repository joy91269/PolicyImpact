from __future__ import annotations

from pathlib import Path

import pytest

from policyimpact.comparison import compare_policy_versions, extract_candidate_rules
from policyimpact.engine import DeterministicRuleEngine
from policyimpact.io import load_audit_decisions, load_claims, load_json
from policyimpact.parser import parse_policy_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def scenario() -> dict[str, object]:
    old_policy = parse_policy_file(PROJECT_ROOT / "data/policies/policy_v1.md")
    new_policy = parse_policy_file(PROJECT_ROOT / "data/policies/policy_v2.md")
    old_rules = extract_candidate_rules(old_policy)
    new_rules = extract_candidate_rules(new_policy)
    claims = load_claims(PROJECT_ROOT / "data/claims/claims.json")
    ground_truth_path = PROJECT_ROOT / "data/ground_truth/ground_truth.json"
    audits = load_audit_decisions(ground_truth_path)
    ground_truth = load_json(ground_truth_path)
    changes = compare_policy_versions(old_policy, new_policy)
    impacts = DeterministicRuleEngine(old_rules, new_rules, audits).compare_claims(
        claims
    )
    return {
        "root": PROJECT_ROOT,
        "old_policy": old_policy,
        "new_policy": new_policy,
        "old_rules": old_rules,
        "new_rules": new_rules,
        "claims": claims,
        "audits": audits,
        "ground_truth": ground_truth,
        "changes": changes,
        "impacts": impacts,
    }

