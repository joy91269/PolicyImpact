# PolicyImpact report source notes

Last verified: 2026-08-08. These notes support the two-page report body and the bibliography page. The assessment prompt itself is not reproduced or distributed.

## Primary organizational and regulatory sources

1. **Cotiviti — Responsible AI use.** Cotiviti publicly describes AI governance, secure controlled environments, human expert responsibility, and a boundary against using AI for medical-necessity determinations or denial of care. This directly supports the proposed human-gated, no-care-decision architecture.  
   Source: [Cotiviti, AI that drives value responsibly](https://www.cotiviti.com/about/responsible-ai-use)

2. **Cotiviti — Payment accuracy.** Cotiviti describes policy/rule content, deterministic rules, analytics, and human-vetted workflows within payment accuracy. The report uses this only to establish organizational fit, not to claim PolicyImpact duplicates a product or creates savings.  
   Source: [Cotiviti, Payment Accuracy](https://www.cotiviti.com/solutions/payment-accuracy)

3. **NIST AI RMF 1.0.** The voluntary framework organizes trustworthy-AI risk work around governance, mapping, measurement, and management across the lifecycle. The report maps its pilot recommendation to those functions.  
   Source: [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)  
   Publication: [NIST AI 100-1](https://doi.org/10.6028/NIST.AI.100-1)  
   Current-status note: NIST's framework page states that AI RMF 1.0 is being revised; the report cites the published 1.0 baseline, and any later pilot should check the successor release.

4. **NIST Generative AI Profile.** The cross-sectoral profile identifies risks that are novel to or exacerbated by generative AI and proposes lifecycle actions. It supports separating model suggestions from deterministic execution and measuring unsupported assertions.  
   Source: [NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)

5. **CMS Interoperability and Prior Authorization Final Rule (CMS-0057-F).** CMS states that impacted payers must implement specified FHIR APIs to improve healthcare data exchange and streamline prior authorization. The report cites this as evidence that versioned, computable, interoperable content is strategically relevant; PolicyImpact itself does not implement prior authorization or FHIR.  
   Source: [CMS fact sheet, January 17, 2024](https://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f)

6. **ONC HTI-1 / Decision Support Interventions.** ONC's certification materials emphasize source attributes, plain-language access, limited identified users, feedback, and risk-management practices for covered decision-support interventions. The report treats this as a transparency design signal, not a claim that PolicyImpact is certified health IT or legally subject to the criterion.  
   Sources: [ONC HTI-1 Final Rule page](https://healthit.gov/regulations/hti-rules/hti-1-final-rule/) and [ONC DSI test method](https://healthit.gov/test-method/decision-support-interventions/)

7. **HL7 FHIR R4 Provenance.** The Provenance resource describes entities, processes, and agents involved in producing or influencing a resource and frames provenance as a basis for authenticity, trust, and reproducibility. The report uses this to motivate evidence/version traceability, while making clear that the POC does not implement FHIR.  
   Source: [HL7 FHIR R4 Provenance](https://hl7.org/fhir/R4/provenance.html)

8. **HHS HIPAA Security Rule risk-analysis guidance.** HHS states that covered risk analysis must consider confidentiality, availability, and integrity risks to e-PHI across electronic media. The report notes that this repository has no PHI; a future e-PHI pilot would require organization-specific privacy, security, and legal review.  
   Source: [HHS, Guidance on Risk Analysis](https://www.hhs.gov/hipaa/for-professionals/security/guidance/guidance-risk-analysis/index.html)

## Peer-reviewed primary research

9. **Singhal et al. (2023).** MultiMedQA and human evaluation show promise but also gaps, and the authors argue that safety-critical healthcare uses need multidimensional evaluation rather than a single automated score. This supports narrow tasks, human review, and explicit limits.  
   Source: [Nature, 620, 172–180](https://doi.org/10.1038/s41586-023-06291-2)

10. **Li et al. (2023).** HaluEval provides generated and human-annotated hallucination examples and finds that LLMs can fabricate unverifiable content and struggle to recognize hallucinations. This supports exact evidence links, an independent auditor role, abstention, and unsupported-assertion measurement.  
    Source: [EMNLP 2023, pp. 6449–6464](https://doi.org/10.18653/v1/2023.emnlp-main.397)

11. **Yao et al. (2023).** ReAct demonstrates a general language-model pattern that interleaves reasoning and external actions. The report cites it only to place “agentic” workflows in context; PolicyImpact deliberately constrains actions to typed proposals and does not expose autonomous tools.  
    Source: [ICLR 2023 paper](https://openreview.net/forum?id=WE_vluYUL-X)

## Citation and scope checks

- Every in-text citation in the report corresponds to a bibliography entry.
- No numerical savings, accuracy, market-size, productivity, or production-readiness claim is made from these sources.
- Cotiviti's public statements are attributed to Cotiviti; they are not independently verified performance findings.
- Regulatory sources are used as design context. The report does not offer legal advice or assert that this synthetic POC is a regulated product.
- The live-model provider is implemented but was not used in the evaluation. Reported results are from a reviewed offline demonstration fixture and the deterministic engine.
