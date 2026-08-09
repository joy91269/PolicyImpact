"""PolicyImpact typed, gated policy-review proof of concept."""

from .comparison import compare_policy_versions, extract_candidate_rules
from .engine import DeterministicRuleEngine, RuleConfigurationError
from .models import (
    AuditDecision,
    CandidateRule,
    Claim,
    ClaimImpact,
    EvidenceReference,
    PolicyChange,
    PolicyDocument,
    PolicySection,
)
from .parser import PolicyParseError, parse_policy_file, parse_policy_text

__all__ = [
    "AuditDecision",
    "CandidateRule",
    "Claim",
    "ClaimImpact",
    "DeterministicRuleEngine",
    "EvidenceReference",
    "PolicyChange",
    "PolicyDocument",
    "PolicyParseError",
    "PolicySection",
    "RuleConfigurationError",
    "compare_policy_versions",
    "extract_candidate_rules",
    "parse_policy_file",
    "parse_policy_text",
]
