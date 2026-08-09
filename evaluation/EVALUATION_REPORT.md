# PolicyImpact Evaluation Report

**Status:** completed reviewed-fixture replay; no live model was invoked.

> This evaluation uses only synthetic demonstration data. It does not measure production claim, payment, coverage, clinical, or fraud decisions.

## Protocol

The frozen manual ground truth specifies four material changes, three executable old/new rule pairs, one abstention, expected section evidence, and all 16 claim-impact records. The Policy Analyst and Evidence Auditor outputs were replayed from the checked-in reviewed fixture. After exactly one bounded revision, explicit reviewed-demo human approvals unlocked the unchanged deterministic engine.

## Results

| Metric | Result | Evaluation unit |
|---|---:|---|
| Policy change precision | 4/4 (100.0%) | Four revised findings in the reviewed offline fixture. |
| Policy change recall | 4/4 (100.0%) | Four manually specified material changes. |
| Rule-field exact match | 6/6 (100.0%) | Six old/new executable rules across three rule pairs; all typed fields and section keys must match. |
| Evidence-section accuracy | 8/8 (100.0%) | Eight old/new section references across four changes. |
| Abstention correctness | 1/1 (100.0%) | The single manually specified ambiguous change. |
| Unsupported assertion count | 0 | Final auditor output only; lower is better. |
| Deterministic impact accuracy | 16/16 (100.0%) | All 16 full ClaimImpact records, including reason and evidence keys. |
| Traceability coverage | 20/20 (100.0%) | Four revised change records plus 16 claim-impact records with exact policy excerpts. |

## Agent audit path

- Initial audit: diagnosis accept; units accept; modifier revise; ambiguous clause abstain.
- Revision: the modifier finding explicitly states that documentation content is absent and the result is review routing, not a payment conclusion.
- Final audit: three accepts and one abstention. The abstained pair remains non-executable.

## Interpretation and limits

The checked-in reviewed fixture reproduces all manually specified changes, rules, evidence keys, abstention, and 16 deterministic outcomes. These are scenario-consistency results for one controlled synthetic example, not an estimate of live-model accuracy, generalization, savings, or production readiness.

The perfect fixture-replay scores are expected because the fixture is a reviewed demonstration aligned to the controlled ground truth. A credible next-stage pilot would require result-blind policy pairs, independent reviewers, disagreement reporting, and prospective live-model runs. None of those claims is made here.

## Verified safeguards

- No claim impact executes without final auditor acceptance and explicit human approval for every executable pair.
- The ambiguous clause remains visible, abstained, and non-executable.
- The deterministic engine—not either AI role—assigns all claim-impact outcomes.
- All codes and records are synthetic and contain no person or provider fields.
- The same 16 claims are compared under both versions; service date does not select a version.
