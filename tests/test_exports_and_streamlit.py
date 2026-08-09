from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from policyimpact.exports import impacts_as_records, impacts_to_json, records_to_csv
from policyimpact.agents import OfflineFixtureProvider
from policyimpact.io import load_json
from policyimpact.scenario import load_scenario
from policyimpact.workflow import (
    authorize_execution,
    execute_authorized_claim_review,
    load_human_approvals,
    run_agent_review,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_csv_and_json_exports_are_complete() -> None:
    scenario = load_scenario(PROJECT_ROOT)
    review = run_agent_review(
        scenario,
        OfflineFixtureProvider(
            PROJECT_ROOT / "data/agent_fixtures/offline_agent_review.json"
        ),
    )
    authorization = authorize_execution(
        review,
        load_human_approvals(
            PROJECT_ROOT / "data/ground_truth/demo_human_approvals.json"
        ),
    )
    impacts = execute_authorized_claim_review(scenario, review, authorization)
    ground_truth = load_json(PROJECT_ROOT / "data/ground_truth/ground_truth.json")
    categories = {
        item["claim_id"]: item["scenario_category"]
        for item in ground_truth["expected_claim_impacts"]
    }
    records = impacts_as_records(impacts, scenario.claims, categories)
    csv_text = records_to_csv(records)
    json_text = impacts_to_json(impacts)
    assert len(records) == 16
    assert csv_text.count("\n") == 17
    assert '"claim_id": "CLM-016"' in json_text
    assert all(record["procedure_code"].startswith("SYN-") for record in records)


def test_streamlit_initial_view_smoke() -> None:
    app = AppTest.from_file(str(PROJECT_ROOT / "streamlit_app.py"))
    app.run(timeout=30)
    assert not app.exception
    assert app.title[0].value == "PolicyImpact"
    assert len(app.tabs) == 4


def test_streamlit_full_offline_approval_path() -> None:
    app = AppTest.from_file(str(PROJECT_ROOT / "streamlit_app.py"))
    app.run(timeout=30)
    app.button[0].click().run(timeout=30)
    assert len(app.radio) == 4
    for approval_radio in app.radio[1:4]:
        approval_radio.set_value("Approve")
    app.run(timeout=30)
    app.button[1].click().run(timeout=30)
    assert not app.exception
    assert any(
        "explicit human demo approval" in item.value for item in app.success
    )
    assert len(app.get("download_button")) == 2
    scenario_metrics = {item.label: item.value for item in app.metric}
    assert scenario_metrics["Clearly affected scenarios"] == "6"
    assert scenario_metrics["Clearly unaffected scenarios"] == "6"
    assert scenario_metrics["Boundary scenarios"] == "2"
    assert scenario_metrics["Ambiguity-review scenarios"] == "2"
