"""Portable exports for evidence-linked synthetic claim impacts."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Mapping

from .models import Claim, ClaimImpact


def impacts_as_records(
    impacts: Iterable[ClaimImpact],
    claims: Iterable[Claim],
    categories: Mapping[str, str],
) -> list[dict[str, object]]:
    claim_by_id = {item.claim_id: item for item in claims}
    records: list[dict[str, object]] = []
    for impact in impacts:
        claim = claim_by_id[impact.claim_id]
        records.append(
            {
                "claim_id": impact.claim_id,
                "scenario_category": categories[impact.claim_id],
                "service_date": claim.service_date.isoformat(),
                "procedure_code": claim.procedure_code,
                "diagnosis_codes": "|".join(claim.diagnosis_codes),
                "modifier": claim.modifier or "",
                "units": claim.units,
                "old_outcome": impact.old_outcome.value,
                "new_outcome": impact.new_outcome.value,
                "affected": impact.affected,
                "human_review_required": impact.human_review_required,
                "matched_rule_ids": "|".join(impact.matched_rule_ids),
                "evidence_sections": "|".join(
                    f"v{item.policy_version}:s{item.section_id}"
                    for item in impact.evidence_references
                ),
                "reason": impact.reason,
            }
        )
    return records


def records_to_csv(records: Iterable[Mapping[str, object]]) -> str:
    rows = list(records)
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def impacts_to_json(impacts: Iterable[ClaimImpact]) -> str:
    return json.dumps(
        [item.model_dump(mode="json") for item in impacts], indent=2
    ) + "\n"
