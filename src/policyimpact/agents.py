"""Role-isolated policy analysis and evidence-audit providers.

The offline provider replays a reviewed demonstration recording. The optional
live provider makes stateless, schema-constrained calls for the two roles. No
provider performs claim calculations or authorizes execution.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .models import (
    AgentRound,
    AnalystResponse,
    AuditorResponse,
    ProviderMode,
)
from .scenario import ScenarioBundle


class AgentProviderError(RuntimeError):
    """Raised when an agent provider cannot return a valid typed response."""


class AgentProvider(Protocol):
    mode: ProviderMode
    label: str
    recording_path: str | None
    live_model_invoked: bool

    def analyze(
        self,
        scenario: ScenarioBundle,
        *,
        round_name: AgentRound,
        audit_feedback: AuditorResponse | None = None,
    ) -> AnalystResponse: ...

    def audit(
        self,
        scenario: ScenarioBundle,
        analysis: AnalystResponse,
        *,
        round_name: AgentRound,
    ) -> AuditorResponse: ...


class OfflineFixtureProvider:
    """Replay the checked-in reviewed-demo fixture without network access."""

    mode = ProviderMode.OFFLINE_REVIEWED_FIXTURE
    label = "Reviewed offline demonstration fixture (not a live model run)"
    live_model_invoked = False

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        data_dir = next(
            (parent for parent in self.path.parents if parent.name == "data"),
            None,
        )
        self.recording_path = (
            self.path.relative_to(data_dir.parent).as_posix()
            if data_dir is not None
            else self.path.name
        )
        self._raw = json.loads(self.path.read_text(encoding="utf-8"))

    def analyze(
        self,
        scenario: ScenarioBundle,
        *,
        round_name: AgentRound,
        audit_feedback: AuditorResponse | None = None,
    ) -> AnalystResponse:
        del scenario, audit_feedback
        key = (
            "initial_analysis"
            if round_name is AgentRound.INITIAL
            else "revised_analysis"
        )
        return AnalystResponse.model_validate(self._raw[key])

    def audit(
        self,
        scenario: ScenarioBundle,
        analysis: AnalystResponse,
        *,
        round_name: AgentRound,
    ) -> AuditorResponse:
        del scenario, analysis
        key = "initial_audit" if round_name is AgentRound.INITIAL else "final_audit"
        return AuditorResponse.model_validate(self._raw[key])


ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class OpenAIResponsesProvider:
    """Optional live structured-output provider for stateless role calls.

    This adapter is deliberately outside the deterministic execution path.
    Install the ``live`` extra and set ``OPENAI_API_KEY`` plus
    ``POLICYIMPACT_AGENT_MODE=live`` to enable it.
    """

    mode = ProviderMode.LIVE_MODEL
    label = "Live OpenAI Responses API role calls"
    recording_path = None

    def __init__(self, model: str) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise AgentProviderError("OPENAI_API_KEY is required for live mode")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise AgentProviderError(
                "live mode requires: python -m pip install -e '.[live]'"
            ) from exc
        self._client = OpenAI()
        self.model = model
        self.live_model_invoked = False

    def analyze(
        self,
        scenario: ScenarioBundle,
        *,
        round_name: AgentRound,
        audit_feedback: AuditorResponse | None = None,
    ) -> AnalystResponse:
        context = {
            "old_policy": scenario.old_policy.model_dump(mode="json"),
            "new_policy": scenario.new_policy.model_dump(mode="json"),
            "deterministically_identified_changes": [
                item.model_dump(mode="json") for item in scenario.changes
            ],
            "controlled_old_rules": [
                item.model_dump(mode="json") for item in scenario.old_rules
                if item.change_id is not None
            ],
            "controlled_new_rules": [
                item.model_dump(mode="json") for item in scenario.new_rules
                if item.change_id is not None
            ],
            "audit_feedback": (
                audit_feedback.model_dump(mode="json") if audit_feedback else None
            ),
            "round": round_name.value,
        }
        instruction = (
            "You are the Policy Analyst role in a synthetic, controlled proof of "
            "concept. Compare only the supplied policy sections and controlled rule "
            "candidates. Preserve exact evidence. State qualifications, exceptions, "
            "and ambiguity. Never approve or deny claims and never infer medical "
            "necessity. Return only the requested concise structured fields; do not "
            "provide chain-of-thought."
        )
        return self._request(AnalystResponse, instruction, context, "analyst_response")

    def audit(
        self,
        scenario: ScenarioBundle,
        analysis: AnalystResponse,
        *,
        round_name: AgentRound,
    ) -> AuditorResponse:
        context = {
            "old_policy": scenario.old_policy.model_dump(mode="json"),
            "new_policy": scenario.new_policy.model_dump(mode="json"),
            "analyst_response": analysis.model_dump(mode="json"),
            "round": round_name.value,
        }
        instruction = (
            "You are the Evidence Auditor role. Independently check each analyst "
            "proposal against the supplied section evidence and rule shape. Choose "
            "accept, reject, revise, or abstain. Ambiguous undefined language must "
            "remain non-executable. Give only concise critique and bounded revision "
            "requests; do not provide chain-of-thought and do not make claim, payment, "
            "fraud, coverage, or clinical decisions."
        )
        return self._request(AuditorResponse, instruction, context, "auditor_response")

    def _request(
        self,
        model_type: type[ResponseModel],
        instruction: str,
        context: dict[str, object],
        schema_name: str,
    ) -> ResponseModel:
        self.live_model_invoked = True
        response = self._client.responses.create(
            model=self.model,
            instructions=instruction,
            input=json.dumps(context),
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": model_type.model_json_schema(),
                    "strict": True,
                }
            },
        )
        try:
            return model_type.model_validate_json(response.output_text)
        except Exception as exc:  # pragma: no cover - live network path
            raise AgentProviderError("live provider returned invalid structured output") from exc


def select_provider(project_root: str | Path) -> AgentProvider:
    """Select live mode only when explicitly requested and credentialed."""

    root = Path(project_root)
    requested = os.getenv("POLICYIMPACT_AGENT_MODE", "offline").strip().lower()
    if requested == "live":
        model = os.getenv("POLICYIMPACT_MODEL", "gpt-5.6-terra")
        return OpenAIResponsesProvider(model=model)
    if requested == "offline":
        return OfflineFixtureProvider(
            root / "data/agent_fixtures/offline_agent_review.json"
        )
    raise AgentProviderError(
        "POLICYIMPACT_AGENT_MODE must be either 'offline' or 'live'"
    )
