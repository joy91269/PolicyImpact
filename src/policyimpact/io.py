"""JSON loading helpers that validate all controlled inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from .models import AuditDecision, Claim


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_claims(path: str | Path) -> tuple[Claim, ...]:
    claims = TypeAdapter(tuple[Claim, ...]).validate_python(load_json(path))
    claim_ids = [claim.claim_id for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("claim IDs must be unique")
    return claims


def load_audit_decisions(path: str | Path) -> tuple[AuditDecision, ...]:
    raw = load_json(path)
    if not isinstance(raw, dict) or "audit_decisions" not in raw:
        raise ValueError("ground truth must contain audit_decisions")
    return TypeAdapter(tuple[AuditDecision, ...]).validate_python(
        raw["audit_decisions"]
    )

