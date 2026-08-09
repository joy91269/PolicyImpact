"""Four-tab Streamlit demonstration for the controlled PolicyImpact scenario."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from policyimpact.agents import OfflineFixtureProvider, OpenAIResponsesProvider
from policyimpact.exports import impacts_as_records, impacts_to_json, records_to_csv
from policyimpact.io import load_json
from policyimpact.models import (
    AuditorDisposition,
    HumanApproval,
    HumanApprovalStatus,
)
from policyimpact.scenario import load_scenario
from policyimpact.workflow import (
    authorize_execution,
    execute_authorized_claim_review,
    run_agent_review,
)


ROOT = Path(__file__).resolve().parent
SCENARIO = load_scenario(ROOT)
GROUND_TRUTH = load_json(ROOT / "data/ground_truth/ground_truth.json")
CATEGORIES = {
    item["claim_id"]: item["scenario_category"]
    for item in GROUND_TRUTH["expected_claim_impacts"]
}


st.set_page_config(
    page_title="PolicyImpact",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1250px;}
      .pi-banner {background:#eff6ff;border-left:5px solid #2563eb;padding:0.85rem 1rem;border-radius:0.4rem;margin-bottom:1rem;}
      .pi-flow {display:flex;gap:0.45rem;align-items:stretch;flex-wrap:wrap;margin:1rem 0;}
      .pi-node {flex:1;min-width:145px;border:1px solid #cbd5e1;border-radius:0.6rem;padding:0.75rem;background:white;}
      .pi-arrow {align-self:center;color:#2563eb;font-weight:700;}
      .pi-small {color:#475569;font-size:0.88rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

if "agent_review" not in st.session_state:
    st.session_state.agent_review = None
if "authorization" not in st.session_state:
    st.session_state.authorization = None
if "impacts" not in st.session_state:
    st.session_state.impacts = None


st.title("PolicyImpact")
st.caption("Evidence-grounded policy change-to-claim review — controlled synthetic proof of concept")
st.markdown(
    """
    <div class="pi-banner"><strong>Synthetic demonstration only.</strong>
    This app uses invented policies, codes, and claims with no PHI. It does not
    approve or deny claims, determine payment or coverage, assess medical necessity,
    or identify fraud.</div>
    """,
    unsafe_allow_html=True,
)

overview_tab, policy_tab, impact_tab, evaluation_tab = st.tabs(
    ["1 · Overview", "2 · Policy & Agent Discussion", "3 · Claim Impact", "4 · Evaluation"]
)


with overview_tab:
    st.subheader("A narrow decision-support workflow")
    st.write(
        "PolicyImpact turns a controlled old/new policy comparison into evidence-linked "
        "candidate rules, subjects them to an independent audit and one bounded revision, "
        "then requires a human approval before a deterministic engine can compare the same "
        "16 synthetic claims under both versions."
    )
    st.markdown(
        """
        <div class="pi-flow">
          <div class="pi-node"><b>1 · Synthetic policies</b><div class="pi-small">Exact sections and controlled parser</div></div>
          <div class="pi-arrow">→</div>
          <div class="pi-node"><b>2 · Policy Analyst role</b><div class="pi-small">Changes, candidate rules, evidence, qualifications</div></div>
          <div class="pi-arrow">→</div>
          <div class="pi-node"><b>3 · Evidence Auditor role</b><div class="pi-small">Critique → one revision → accept/reject/abstain</div></div>
          <div class="pi-arrow">→</div>
          <div class="pi-node"><b>4 · Human gate</b><div class="pi-small">Explicit approve/reject; no silent execution</div></div>
          <div class="pi-arrow">→</div>
          <div class="pi-node"><b>5 · Deterministic engine</b><div class="pi-small">Fixed operators and exact evidence trace</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Policy versions", "2")
    c2.metric("Material changes", "4")
    c3.metric("Executable rule pairs", "3")
    c4.metric("Synthetic claims", "16")
    with st.expander("What the proof of concept deliberately does not do"):
        st.markdown(
            "- No arbitrary policy parsing, real codes, payer contracts, PHI, FHIR integration, or vector database.\n"
            "- No LLM performs arithmetic, claim matching, or outcome assignment.\n"
            "- Service dates are displayed but do not select a policy version; both versions are applied hypothetically to the same claims to isolate policy change.\n"
            "- The engine returns one primary review signal using a fixed controlled priority; it is not an exhaustive concurrent-impact analysis.\n"
            "- Review outcomes are selected-criterion signals, not final claim or payment decisions."
        )


with policy_tab:
    st.subheader("Controlled policy pair and role-isolated review")
    pair = st.selectbox(
        "Policy pair",
        ["SYN-PAY-042 · version 1.0 → version 2.0"],
        help="This proof of concept intentionally supports one controlled pair.",
    )
    st.caption(pair)
    for old_section, new_section in zip(
        SCENARIO.old_policy.sections[2:], SCENARIO.new_policy.sections[2:]
    ):
        change = next(
            item for item in SCENARIO.changes if item.section_id == old_section.section_id
        )
        with st.expander(f"Section {old_section.section_id} · {old_section.title}"):
            left, right = st.columns(2)
            left.markdown("**Version 1.0**")
            left.warning(f"Material wording: {change.old_summary}")
            left.info(old_section.text)
            right.markdown("**Version 2.0**")
            right.warning(f"Material wording: {change.new_summary}")
            right.info(new_section.text)

    mode_label = st.radio(
        "Agent execution mode",
        ["Replay reviewed offline fixture", "Live role calls (requires local credentials)"],
        horizontal=True,
    )
    if st.button("Run / replay analyst and auditor", type="primary"):
        try:
            if mode_label.startswith("Live"):
                provider = OpenAIResponsesProvider(
                    model=os.getenv("POLICYIMPACT_MODEL", "gpt-5.6-terra")
                )
            else:
                provider = OfflineFixtureProvider(
                    ROOT / "data/agent_fixtures/offline_agent_review.json"
                )
            st.session_state.agent_review = run_agent_review(SCENARIO, provider)
            st.session_state.authorization = None
            st.session_state.impacts = None
        except Exception as exc:
            st.error(f"Agent run could not start: {exc}")

    review = st.session_state.agent_review
    if review is None:
        st.info("Run or replay the role workflow to reveal the audit and approval controls.")
    else:
        st.success(
            f"Completed exactly {review.revision_round_count} revision round · {review.provider_label}"
        )
        if review.recording_path:
            st.caption(f"Offline recording: `{review.recording_path}`")

        st.markdown("#### Policy Analyst · initial proposal")
        st.caption(review.initial_analysis.concise_summary)
        for finding in review.initial_analysis.findings:
            with st.expander(
                f"{finding.change.change_id} · {finding.change.category.value} · initial candidate"
            ):
                old_col, new_col = st.columns(2)
                old_col.markdown("**Version 1.0 candidate rule**")
                old_col.json(finding.old_rule.model_dump(mode="json"))
                new_col.markdown("**Version 2.0 candidate rule**")
                new_col.json(finding.new_rule.model_dump(mode="json"))
                st.markdown(
                    "**Qualifications**  \n"
                    + "  \n".join(f"- {item}" for item in finding.qualifications)
                )
                st.markdown(
                    "**Exceptions**  \n"
                    + "  \n".join(f"- {item}" for item in finding.exceptions)
                )
                if finding.ambiguity_note:
                    st.warning(finding.ambiguity_note)
                evidence_left, evidence_right = st.columns(2)
                evidence_left.markdown(
                    f"**v{finding.change.old_evidence.policy_version} · Section "
                    f"{finding.change.old_evidence.section_id}**"
                )
                evidence_left.code(
                    finding.change.old_evidence.excerpt, language=None
                )
                evidence_right.markdown(
                    f"**v{finding.change.new_evidence.policy_version} · Section "
                    f"{finding.change.new_evidence.section_id}**"
                )
                evidence_right.code(
                    finding.change.new_evidence.excerpt, language=None
                )

        initial_rows = [
            {
                "change": item.change_id,
                "initial decision": item.disposition.value,
                "critique": item.concise_critique,
                "revision request": item.requested_revision or "—",
            }
            for item in review.initial_audit.findings
        ]
        st.markdown("#### Evidence Auditor · initial critique")
        st.dataframe(initial_rows, hide_index=True, width="stretch")

        st.markdown("#### Policy Analyst · one bounded revision")
        st.caption(review.revised_analysis.concise_summary)
        for finding in review.revised_analysis.findings:
            with st.expander(
                f"{finding.change.change_id} · revised/retained candidate and evidence"
            ):
                old_col, new_col = st.columns(2)
                old_col.markdown("**Revised/retained version 1.0 rule**")
                old_col.json(finding.old_rule.model_dump(mode="json"))
                new_col.markdown("**Revised/retained version 2.0 rule**")
                new_col.json(finding.new_rule.model_dump(mode="json"))
                st.markdown(
                    "**Qualifications**  \n"
                    + "  \n".join(f"- {item}" for item in finding.qualifications)
                )
                st.markdown(
                    "**Exceptions**  \n"
                    + "  \n".join(f"- {item}" for item in finding.exceptions)
                )
                evidence_left, evidence_right = st.columns(2)
                evidence_left.code(
                    finding.change.old_evidence.excerpt, language=None
                )
                evidence_right.code(
                    finding.change.new_evidence.excerpt, language=None
                )

        st.markdown("#### Evidence Auditor · final decision and human gate")
        approvals: list[HumanApproval] = []
        for item in review.final_audit.findings:
            finding = next(
                candidate
                for candidate in review.revised_analysis.findings
                if candidate.change.change_id == item.change_id
            )
            with st.container(border=True):
                left, right = st.columns([3, 1])
                left.markdown(
                    f"**{item.change_id} · {finding.change.category.value}**  \n"
                    f"Final auditor decision: `{item.disposition.value}`  \n"
                    f"{item.concise_critique}"
                )
                left.caption(
                    f"Evidence: v{finding.change.old_evidence.policy_version} §{finding.change.old_evidence.section_id} "
                    f"and v{finding.change.new_evidence.policy_version} §{finding.change.new_evidence.section_id}"
                )
                with left.expander("Exact cited evidence"):
                    st.markdown(
                        f"**v{finding.change.old_evidence.policy_version} · Section "
                        f"{finding.change.old_evidence.section_id}**"
                    )
                    st.code(finding.change.old_evidence.excerpt, language=None)
                    st.markdown(
                        f"**v{finding.change.new_evidence.policy_version} · Section "
                        f"{finding.change.new_evidence.section_id}**"
                    )
                    st.code(finding.change.new_evidence.excerpt, language=None)
                if item.disposition is AuditorDisposition.ACCEPT:
                    choice = right.radio(
                        "Human decision",
                        ["Pending", "Approve", "Reject"],
                        key=f"approval_{item.change_id}",
                    )
                    if choice != "Pending":
                        approvals.append(
                            HumanApproval(
                                change_id=item.change_id,
                                status=(
                                    HumanApprovalStatus.APPROVED
                                    if choice == "Approve"
                                    else HumanApprovalStatus.REJECTED
                                ),
                                reviewer="Streamlit demo reviewer",
                                rationale=f"Explicit {choice.lower()} selection in the demo UI.",
                            )
                        )
                else:
                    right.warning("Non-executable\n\nHuman review only")

        if st.button("Record decisions and evaluate execution gate"):
            authorization = authorize_execution(review, approvals)
            st.session_state.authorization = authorization
            st.session_state.impacts = (
                execute_authorized_claim_review(SCENARIO, review, authorization)
                if authorization.execution_allowed
                else None
            )
        if st.session_state.authorization is not None:
            authorization = st.session_state.authorization
            if authorization.execution_allowed:
                st.success(authorization.reason)
            else:
                st.error(authorization.reason)
                st.caption(
                    "Blocked change IDs: " + ", ".join(authorization.blocked_change_ids)
                )


with impact_tab:
    st.subheader("Deterministic old/new comparison")
    st.caption(
        "Both policy versions are applied to the same synthetic claims. Service date does not select the version in this proof of concept."
    )
    impacts = st.session_state.impacts
    if impacts is None:
        st.warning(
            "Claim comparison is locked. In tab 2, replay the workflow, explicitly approve all three accepted rule pairs, and record the decisions."
        )
    else:
        records = impacts_as_records(impacts, SCENARIO.claims, CATEGORIES)
        df = pd.DataFrame(records)
        f1, f2, f3, f4 = st.columns(4)
        f1.metric(
            "Clearly affected scenarios",
            int((df["scenario_category"] == "clearly_affected").sum()),
        )
        f2.metric(
            "Clearly unaffected scenarios",
            int((df["scenario_category"] == "clearly_unaffected").sum()),
        )
        f3.metric(
            "Boundary scenarios",
            int((df["scenario_category"] == "boundary").sum()),
        )
        f4.metric(
            "Ambiguity-review scenarios",
            int((df["scenario_category"] == "human_review").sum()),
        )
        st.caption(
            f"Outcome comparison: {int(df['affected'].sum())} affected and "
            f"{int((~df['affected']).sum())} unchanged; "
            f"{int(df['human_review_required'].sum())} outputs route to some form of human review."
        )
        filter_name = st.selectbox(
            "View",
            [
                "All",
                "Clearly affected",
                "Clearly unaffected",
                "Boundary",
                "Ambiguity review",
                "Any output routed to review",
            ],
        )
        filtered = df
        if filter_name == "Clearly affected":
            filtered = df[df["scenario_category"] == "clearly_affected"]
        elif filter_name == "Clearly unaffected":
            filtered = df[df["scenario_category"] == "clearly_unaffected"]
        elif filter_name == "Boundary":
            filtered = df[df["scenario_category"] == "boundary"]
        elif filter_name == "Ambiguity review":
            filtered = df[df["scenario_category"] == "human_review"]
        elif filter_name == "Any output routed to review":
            filtered = df[df["human_review_required"]]
        st.dataframe(
            filtered[
                [
                    "claim_id",
                    "scenario_category",
                    "old_outcome",
                    "new_outcome",
                    "affected",
                    "human_review_required",
                ]
            ],
            hide_index=True,
            width="stretch",
        )
        selected_id = st.selectbox("Inspect one claim", list(df["claim_id"]))
        impact = next(item for item in impacts if item.claim_id == selected_id)
        claim = next(item for item in SCENARIO.claims if item.claim_id == selected_id)
        left, right = st.columns(2)
        left.markdown("**Synthetic claim fields**")
        left.json(claim.model_dump(mode="json"))
        old_metric, new_metric = right.columns(2)
        old_metric.metric("Old outcome", impact.old_outcome.value)
        new_metric.metric("New outcome", impact.new_outcome.value)
        right.markdown(
            f"**Affected:** `{str(impact.affected).lower()}` · "
            f"**Human review required:** `{str(impact.human_review_required).lower()}`"
        )
        right.markdown("**Matched trace/rule IDs**")
        right.code("\n".join(impact.matched_rule_ids), language=None)
        right.markdown(f"**Deterministic explanation**  \n{impact.reason}")
        for evidence in impact.evidence_references:
            right.markdown(
                f"**v{evidence.policy_version} · Section {evidence.section_id} · {evidence.section_title}**"
            )
            right.code(evidence.excerpt, language=None)
        d1, d2 = st.columns(2)
        d1.download_button(
            "Download all impacts as CSV",
            data=records_to_csv(records),
            file_name="policyimpact_synthetic_claim_impacts.csv",
            mime="text/csv",
        )
        d2.download_button(
            "Download all impacts as JSON",
            data=impacts_to_json(impacts),
            file_name="policyimpact_synthetic_claim_impacts.json",
            mime="application/json",
        )


with evaluation_tab:
    st.subheader("Controlled evaluation")
    results_path = ROOT / "evaluation/evaluation_results.json"
    if not results_path.exists():
        st.info("Evaluation artifacts have not been generated yet.")
    else:
        results = json.loads(results_path.read_text(encoding="utf-8"))
        st.warning(
            "Agent metrics below are from a reviewed offline demonstration fixture, not a live-model benchmark or production accuracy estimate."
        )
        st.caption(
            f"Mode: {results['run_metadata']['execution_mode']} · live model invoked: {results['run_metadata']['live_model_invoked']}"
        )
        def metric_rows(metric_names: tuple[str, ...]) -> list[dict[str, object]]:
            rows: list[dict[str, object]] = []
            for name in metric_names:
                metric = results["metrics"][name]
                rows.append(
                    {
                        "metric": name,
                        "value": metric["value"],
                        "numerator": str(metric.get("numerator", "—")),
                        "denominator": str(metric.get("denominator", "—")),
                        "scope": metric["scope"],
                    }
                )
            return rows

        st.markdown("#### AI-agent extraction and audit · reviewed offline fixture")
        st.dataframe(
            metric_rows(
                (
                    "policy_change_precision",
                    "policy_change_recall",
                    "rule_field_exact_match",
                    "evidence_section_accuracy",
                    "abstention_correctness",
                    "unsupported_assertion_count",
                )
            ),
            hide_index=True,
            width="stretch",
        )
        st.markdown("#### Deterministic engine and end-to-end evidence")
        st.dataframe(
            metric_rows(
                (
                    "deterministic_impact_accuracy",
                    "traceability_coverage",
                )
            ),
            hide_index=True,
            width="stretch",
        )
        st.markdown("#### Live-mode results")
        st.info(
            "Not executed. The optional live provider is implemented, but no live-model "
            "performance result is reported or implied."
        )
        st.markdown("#### Interpretation")
        st.write(results["interpretation"])
        st.markdown("#### Guardrails verified")
        st.markdown("\n".join(f"- {item}" for item in results["guardrails_verified"]))
