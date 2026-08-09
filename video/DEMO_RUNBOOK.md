# PolicyImpact recording runbook

This runbook uses the deterministic reviewed fixture. It does not require a
network connection or an API key.

## Start the application

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
streamlit run streamlit_app.py --server.headless true
```

Open the local URL printed by Streamlit, normally
`http://localhost:8501`. Keep the terminal out of the recording frame.

## Pre-recording state

1. Refresh the app once so there are no decisions left from a practice run.
2. Confirm the banner says the data are synthetic and the app makes no payment
   or clinical decision.
3. Confirm the four tabs are visible.
4. In tab 2, confirm **Agent execution mode** defaults to **Replay reviewed
   offline fixture**.
5. Do not enter or show any API key, private document, email, terminal history,
   notification, or unrelated browser tab.

## Exact click sequence and expected output

1. **1 · Overview**
   - Show the five-stage workflow.
   - Expected metrics: 2 policy versions, 4 material changes, 3 executable rule
     pairs, and 16 synthetic claims.

2. **2 · Policy & Agent Discussion**
   - Policy pair: **SYN-PAY-042 · version 1.0 → version 2.0**.
   - Leave **Replay reviewed offline fixture** selected.
   - Click **Run / replay analyst and auditor**.
   - Expected banner: exactly 1 revision round; provider is labeled as an
     offline reviewed fixture.
   - Expected final decisions:
     - `CHG-DIAG-001`: accept;
     - `CHG-UNITS-002`: accept;
     - `CHG-MOD-003`: accept;
     - `CHG-AMB-004`: abstain and non-executable.
   - Select **Approve** for the three accepted changes. Do not change the
     abstained item.
   - Click **Record decisions and evaluate execution gate**.
   - Expected: success message saying all executable rules passed the Auditor
     and human gates.

3. **3 · Claim Impact**
   - Expected scenario totals: 6 clearly affected, 6 clearly unaffected, 2
     boundary, and 2 ambiguity-review fixtures. The caption also reports 7
     affected and 9 unchanged outcomes; four outputs route to some form of human
     review because two modifier-review results and two ambiguity results are
     retained.
   - Leave **View** as **All** and choose `CLM-008` under **Inspect one claim**.
   - Expected accepted-rule demonstration:
     - old outcome: `unchanged`;
     - new outcome: `unit_limit_exceeded`;
     - matched rule pair: `UNITS-V1` / `UNITS-V2`;
     - exact section evidence is shown.
   - Change **View** to **Ambiguity review** and choose `CLM-015` under
     **Inspect one claim**.
   - Expected abstention/human-review demonstration:
     - old and new outcomes: `ambiguous_human_review`;
     - human review remains required;
     - the ambiguous `CHG-AMB-004` proposal was not authorized for execution.
   - Do not click the download buttons during the timed recording unless there
     is spare time.

4. **4 · Evaluation**
   - Show the warning that agent metrics come from a reviewed offline fixture.
   - Expected mode: `offline_reviewed_demo_fixture`; live model invoked: `false`.
   - Point briefly to the deterministic and agent/evidence metrics.

## Fallback if live mode fails

Live mode is optional and should not be used in the default recording. If it was
selected accidentally or a credential/model call fails:

1. Return to tab 2.
2. Select **Replay reviewed offline fixture**.
3. Click **Run / replay analyst and auditor** again.
4. Repeat the three explicit approvals and record the decisions.

This fallback is the intended recording-safe path and must be described as a
fixture replay, not a live response.

## Reset after a practice run

Refresh the browser page. Streamlit session state resets; repeat the exact click
sequence above. No repository file is modified by the approval controls.
