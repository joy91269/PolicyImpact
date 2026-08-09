# PolicyImpact video script

Target runtime: **4 minutes 30 seconds**. The timing includes short cursor and
tab transitions. Speak naturally rather than trying to fill every second.

## 0:00–0:18 — On camera

“Hello, I’m Jiuyi Zheng, a Ph.D. student at the University of Missouri. I built
PolicyImpact as a synthetic proof of concept for evidence-grounded policy
change-to-claim review. I’ll show the design, the controlled evaluation, and a
short offline demonstration.”

## 0:18–0:45 — Slide 1: problem and scope

“Policy changes are difficult to operationalize safely because the evidence,
the interpreted rule, and the downstream claim review can become disconnected.
PolicyImpact keeps that chain explicit. Everything shown here is invented: the
policies, codes, and sixteen claims contain no PHI. The system does not approve
or deny claims and makes no clinical or payment decision.”

## 0:45–1:10 — Slide 2: trend, opportunity, and threat

“The useful opportunity is governed interpretation, not autonomous
adjudication. A copilot can identify changes, propose typed rules, and organize
an expert review queue. The corresponding threats are unsupported rule fields,
silent automation, and scope drift. My main guardrail is simple: generative
output cannot execute until both the Auditor and a human approve it.”

## 1:10–1:35 — Slide 3: architecture

“The architecture has three layers. Interpret compares a controlled policy pair
and produces an Analyst proposal. Govern applies an isolated Auditor role, one
bounded revision, and an explicit human gate. Execute is deterministic: only
approved typed rules reach fixed Python operators, and every output retains the
exact policy evidence used.”

## 1:35–1:58 — Slide 4: two-agent workflow

“The Analyst initially proposes four changes. The Auditor can accept, reject,
request revision, or abstain, and it challenges one modifier qualification. The
Analyst gets exactly one revision—there is no open-ended debate. The final
review accepts three executable rule pairs and abstains on one ambiguous clause.
Only concise evidence-based records are stored; no hidden chain of thought is
requested or displayed.”

## 1:58–2:18 — Slide 5: controlled results

“The fixture replay checks workflow plumbing rather than live-model quality. All
sixteen expected impact records match the manual gold set, all twenty evaluated
outputs retain the expected evidence trace, the final review has three accepts
and one abstention, and it contains zero unsupported final assertions. These are
synthetic deterministic checks—not real-world healthcare accuracy or savings.”

## 2:18–2:38 — Slide 6: recommendation

“My recommendation is a small result-blind pilot: freeze approved policy pairs
and gold criteria before model runs, use independent experts for ground truth,
measure abstention, traceability, and overrides as well as accuracy, and define
stop gates in advance. This proof of concept is not production ready.”

## 2:38–2:52 — App: Overview

Switch to the running Streamlit app and select **1 · Overview**.

“The application mirrors the architecture and makes the synthetic-data and
no-decision boundaries prominent. Both policy versions are intentionally applied
to the same claims; service dates do not select the policy in this prototype.”

## 2:52–3:25 — App: Policy & Agent Discussion

Select **2 · Policy & Agent Discussion**. Keep **Replay reviewed offline
fixture** selected. Click **Run / replay analyst and auditor**.

“For a recording-safe demo I am replaying a reviewed, versioned offline fixture;
this is not presented as a live model response. Here are the initial audit, the
single revision, the final evidence decisions, and exact old and new section
references.”

Choose **Approve** for `CHG-DIAG-001`, `CHG-UNITS-002`, and `CHG-MOD-003`.
Leave `CHG-AMB-004` visibly non-executable. Click **Record decisions and evaluate
execution gate**.

“I explicitly approve the three accepted pairs. The ambiguous fourth change is
an Auditor abstention and cannot enter execution.”

## 3:25–3:58 — App: accepted rule and abstained case

Select **3 · Claim Impact**. Under **Inspect one claim**, choose `CLM-008`.

“For CLM-008, the old policy outcome is unchanged and the new outcome is unit
limit exceeded. The explanation identifies the matched typed rule and shows the
exact policy evidence. This is the deterministic primary review signal, not an
exhaustive adjudication analysis.”

Then set **View** to **Ambiguity review** and choose `CLM-015`.

“CLM-015 shows the opposite safety behavior: the ambiguous clause remains a
human-review case under both versions. The model abstention does not become an
executable rule or a claim decision.”

## 3:58–4:12 — App: Evaluation

Select **4 · Evaluation**.

“The evaluation tab separates the deterministic engine from the reviewed agent
fixture and explicitly states that no live model was invoked. The downloadable
JSON and CSV outputs are also generated from the approved deterministic path.”

## 4:12–4:30 — Closing, preferably on camera

“PolicyImpact demonstrates a narrow, auditable handoff from policy evidence to
human-reviewed claim-impact triage. The next step is an expert-authored,
multi-policy pilot with predefined stop criteria—not autonomous deployment.
Thank you for your consideration.”
