"""Load the single controlled PolicyImpact demonstration scenario."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .comparison import compare_policy_versions, extract_candidate_rules
from .io import load_claims
from .models import CandidateRule, Claim, PolicyChange, PolicyDocument
from .parser import parse_policy_file


@dataclass(frozen=True)
class ScenarioBundle:
    old_policy: PolicyDocument
    new_policy: PolicyDocument
    changes: tuple[PolicyChange, ...]
    old_rules: tuple[CandidateRule, ...]
    new_rules: tuple[CandidateRule, ...]
    claims: tuple[Claim, ...]


def load_scenario(project_root: str | Path) -> ScenarioBundle:
    root = Path(project_root)
    old_policy = parse_policy_file(root / "data/policies/policy_v1.md")
    new_policy = parse_policy_file(root / "data/policies/policy_v2.md")
    return ScenarioBundle(
        old_policy=old_policy,
        new_policy=new_policy,
        changes=compare_policy_versions(old_policy, new_policy),
        old_rules=extract_candidate_rules(old_policy),
        new_rules=extract_candidate_rules(new_policy),
        claims=load_claims(root / "data/claims/claims.json"),
    )
