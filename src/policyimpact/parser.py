"""Strict Markdown parser for the two controlled synthetic policies."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from .models import PolicyDocument, PolicySection


TITLE_PATTERN = re.compile(r"^#\s+(?P<title>.+?)\s*$")
METADATA_PATTERN = re.compile(
    r"^\*\*(?P<key>Policy ID|Version|Effective Date):\*\*\s+`(?P<value>[^`]+)`\s*$"
)
SECTION_PATTERN = re.compile(r"^##\s+(?P<section_id>[1-9][0-9]*)\.\s+(?P<title>.+?)\s*$")
REQUIRED_SECTION_IDS = ("1", "2", "3", "4", "5", "6")


class PolicyParseError(ValueError):
    """Raised when a controlled policy does not match the strict format."""


def parse_policy_file(path: str | Path) -> PolicyDocument:
    policy_path = Path(path)
    return parse_policy_text(policy_path.read_text(encoding="utf-8"))


def parse_policy_text(text: str) -> PolicyDocument:
    lines = text.splitlines()
    if not lines:
        raise PolicyParseError("policy document is empty")

    title: str | None = None
    metadata: dict[str, str] = {}
    notice_lines: list[str] = []
    section_records: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None

    for line in lines:
        title_match = TITLE_PATTERN.match(line)
        if title_match and title is None:
            title = title_match.group("title")
            continue

        metadata_match = METADATA_PATTERN.match(line)
        if metadata_match and current is None:
            metadata[metadata_match.group("key")] = metadata_match.group("value")
            continue

        section_match = SECTION_PATTERN.match(line)
        if section_match:
            if current is not None:
                section_records.append(current)
            current = (
                section_match.group("section_id"),
                section_match.group("title"),
                [],
            )
            continue

        if current is None:
            if "synthetic demonstration data" in line.lower():
                notice_lines.append(line.lstrip("> ").strip())
        else:
            current[2].append(line)

    if current is not None:
        section_records.append(current)

    if title is None:
        raise PolicyParseError("policy title is missing")
    required_metadata = {"Policy ID", "Version", "Effective Date"}
    missing_metadata = required_metadata - metadata.keys()
    if missing_metadata:
        missing = ", ".join(sorted(missing_metadata))
        raise PolicyParseError(f"policy metadata is missing: {missing}")
    if not notice_lines:
        raise PolicyParseError("explicit synthetic demonstration data notice is missing")

    actual_ids = tuple(record[0] for record in section_records)
    if actual_ids != REQUIRED_SECTION_IDS:
        raise PolicyParseError(
            "controlled policy must contain numbered sections 1 through 6 in order; "
            f"found {actual_ids!r}"
        )

    sections: list[PolicySection] = []
    for section_id, section_title, body_lines in section_records:
        body = "\n".join(body_lines).strip()
        if not body:
            raise PolicyParseError(f"policy section {section_id} has no content")
        sections.append(
            PolicySection(section_id=section_id, title=section_title, text=body)
        )

    try:
        effective_date = date.fromisoformat(metadata["Effective Date"])
        return PolicyDocument(
            policy_id=metadata["Policy ID"],
            version=metadata["Version"],
            effective_date=effective_date,
            title=title,
            synthetic=True,
            synthetic_notice=" ".join(notice_lines),
            sections=tuple(sections),
        )
    except (ValueError, ValidationError) as exc:
        raise PolicyParseError(f"policy validation failed: {exc}") from exc

