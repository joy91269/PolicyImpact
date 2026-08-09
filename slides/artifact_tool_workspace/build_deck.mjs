import fs from "node:fs/promises";
import path from "node:path";
import {
  Presentation,
  PresentationFile,
  layers,
  shape,
  text,
} from "@oai/artifact-tool";

const OUT = path.resolve("..");
const RENDERED = path.join(OUT, "rendered");
const PPTX = path.join(OUT, "Jiuyi_Zheng_PolicyImpact_Presentation.pptx");

const COLORS = {
  ink: "#152033",
  muted: "#5B687A",
  line: "#CBD5E1",
  panel: "#EEF3F8",
  blue: "#176B87",
  blueSoft: "#DCEEF4",
  green: "#167D67",
  greenSoft: "#DFF3ED",
  amber: "#A65F00",
  amberSoft: "#FFF0D6",
  red: "#A13A3A",
  redSoft: "#FBE4E4",
  white: "#FFFFFF",
};

function paragraph(value, size = 22, options = {}) {
  return {
    runs: [
      {
        run: value,
        textStyle: {
          fontSize: `${size}px`,
          typeface: "Helvetica Neue",
          color: options.color ?? COLORS.ink,
          bold: options.bold ?? false,
        },
      },
    ],
    spaceAfter: options.spaceAfter ?? 0,
    paragraphStyle: {
      lineSpacingPercent: options.lineSpacingPercent ?? 108000,
      alignment: options.alignment ?? "left",
    },
  };
}

function sectionBlock(heading, body, options = {}) {
  return {
    heading: paragraph(heading, options.headingSize ?? 24, {
      bold: true,
      color: options.headingColor ?? COLORS.ink,
      spaceAfter: 520,
      lineSpacingPercent: 100000,
    }),
    body: paragraph(body, options.bodySize ?? 19, {
      color: options.bodyColor ?? COLORS.muted,
      lineSpacingPercent: 112000,
    }),
  };
}

function addNotes(slide, notes) {
  slide.speakerNotes.textFrame.setText(notes);
  slide.speakerNotes.setVisible(true);
}

function addFooter(slide, number) {
  slide.compose(
    layers({ name: `codex-grid-footer-${number}`, width: "fill", height: "fill" }, [
      text([String(number)], {
        name: `slide-number-${number}`,
        position: { left: 1182, top: 658 },
        width: 56,
        height: 26,
        style: {
          fontSize: "13px",
          typeface: "Helvetica Neue",
          color: COLORS.muted,
          alignment: "right",
          verticalAlignment: "bottom",
          insets: { top: 0, right: 0, bottom: 0, left: 0 },
        },
      }),
    ]),
    { frame: { left: 0, top: 0, width: 1280, height: 720 }, baseUnit: 1 },
  );
}

function buildTitleSlide(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = COLORS.white;
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-01-policyimpact", width: "fill", height: "fill" }, [
      shape({
        name: "accent-rail",
        geometry: "rect",
        fill: COLORS.blue,
        line: { style: "solid", width: 0, fill: COLORS.blue },
        position: { left: 0, top: 0 },
        width: 14,
        height: 720,
      }),
      text([paragraph("SYNTHETIC PROOF OF CONCEPT · COTIVITI GENAI SCIENCE", 19, { bold: true, color: COLORS.blue })], {
        name: "supertitle",
        position: { left: 52, top: 48 },
        width: 790,
        height: 42,
        style: { fontSize: "19px", typeface: "Helvetica Neue", color: COLORS.blue, insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      text([paragraph("PolicyImpact", 78, { bold: true, lineSpacingPercent: 92000 })], {
        name: "main-title",
        position: { left: 52, top: 181 },
        width: 1050,
        height: 112,
        style: { fontSize: "78px", typeface: "Helvetica Neue", color: COLORS.ink, verticalAlignment: "bottom", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      text([paragraph("Evidence-grounded policy change-to-claim review", 38, { color: COLORS.ink, lineSpacingPercent: 100000 })], {
        name: "subtitle",
        position: { left: 52, top: 310 },
        width: 1000,
        height: 98,
        style: { fontSize: "38px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      shape({
        name: "scope-panel",
        geometry: "roundRect",
        fill: COLORS.panel,
        line: { style: "solid", width: 0, fill: COLORS.panel },
        position: { left: 52, top: 478 },
        width: 940,
        height: 105,
      }),
      text([paragraph("Jiuyi Zheng  ·  Synthetic policies and claims  ·  No PHI  ·  No production decisions", 24, { color: COLORS.muted })], {
        name: "author-scope",
        position: { left: 82, top: 510 },
        width: 875,
        height: 58,
        style: { fontSize: "24px", typeface: "Helvetica Neue", color: COLORS.muted, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
    ]),
    { frame: { left: 0, top: 0, width: 1280, height: 720 }, baseUnit: 1 },
  );
  addFooter(slide, 1);
  addNotes(
    slide,
    "I am Jiuyi Zheng, a PhD student at the University of Missouri. PolicyImpact is a synthetic proof of concept for a narrow problem: turning a policy change into explicit, reviewable claim-impact logic. It does not use PHI, production claims, real payment decisions, or proprietary content. The demo focuses on workflow safety and traceability, not on a savings claim."
  );
  return slide;
}

function buildOpportunitySlide(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = COLORS.white;
  const opportunity = sectionBlock(
    "Opportunity",
    "Evidence-linked change triage\nTyped rule proposals\nExpert review queues",
    { headingColor: COLORS.green, bodySize: 22 }
  );
  const threat = sectionBlock(
    "Threat",
    "Unsupported rule fields\nSilent automation\nScope drift into adjudication",
    { headingColor: COLORS.red, bodySize: 22 }
  );
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-11-policyimpact", width: "fill", height: "fill" }, [
      text([paragraph("The opportunity is governed interpretation—not autonomous adjudication", 39, { bold: true, lineSpacingPercent: 93000 })], {
        name: "title",
        position: { left: 42, top: 36 },
        width: 1196,
        height: 105,
        style: { fontSize: "39px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      text([
        paragraph("WHY NOW", 16, { bold: true, color: COLORS.blue, spaceAfter: 480 }),
        paragraph("Public healthcare guidance increasingly emphasizes transparent decision support, data provenance, and governed AI. The tractable product surface is the handoff from policy evidence to human-reviewed rules—not replacing domain experts.", 23, { color: COLORS.muted, lineSpacingPercent: 115000 }),
      ], {
        name: "context",
        position: { left: 42, top: 146 },
        width: 1196,
        height: 165,
        style: { fontSize: "23px", typeface: "Helvetica Neue", color: COLORS.muted, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      shape({
        name: "opportunity-card",
        geometry: "roundRect",
        fill: COLORS.greenSoft,
        line: { style: "solid", width: 1, fill: "#B6DED3" },
        position: { left: 42, top: 346 },
        width: 580,
        height: 238,
      }),
      text([opportunity.heading, opportunity.body], {
        name: "opportunity-text",
        position: { left: 76, top: 378 },
        width: 510,
        height: 172,
        style: { fontSize: "22px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      shape({
        name: "threat-card",
        geometry: "roundRect",
        fill: COLORS.redSoft,
        line: { style: "solid", width: 1, fill: "#EBC2C2" },
        position: { left: 658, top: 346 },
        width: 580,
        height: 238,
      }),
      text([threat.heading, threat.body], {
        name: "threat-text",
        position: { left: 692, top: 378 },
        width: 510,
        height: 172,
        style: { fontSize: "22px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      text([paragraph("Guardrail: generative output stays non-executable until Auditor review and explicit human approval.", 20, { bold: true, color: COLORS.blue })], {
        name: "guardrail",
        position: { left: 42, top: 617 },
        width: 1120,
        height: 38,
        style: { fontSize: "20px", typeface: "Helvetica Neue", color: COLORS.blue, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
    ]),
    { frame: { left: 0, top: 0, width: 1280, height: 720 }, baseUnit: 1 },
  );
  addFooter(slide, 2);
  addNotes(
    slide,
    "The opportunity is not autonomous claim adjudication. It is governed interpretation: connect a policy change to explicit evidence, propose typed logic, challenge it, and route it to an expert. Cotiviti's public responsible-AI principles emphasize human oversight, traceability, and accountability. CMS and ONC also show a broader move toward interoperable, transparent healthcare workflows. Those public trends motivate the workflow, but this prototype does not claim compliance or production readiness.\n\n[Sources]\nhttps://www.cotiviti.com/about/responsible-ai-use\nhttps://www.cms.gov/newsroom/fact-sheets/cms-interoperability-and-prior-authorization-final-rule-cms-0057-f\nhttps://healthit.gov/regulations/hti-rules/hti-1-final-rule/"
  );
  return slide;
}

function buildArchitectureSlide(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = COLORS.white;
  const cards = [
    sectionBlock("Interpret", "Versioned policy pair\nControlled parser\nAnalyst proposal", { headingColor: COLORS.blue, bodySize: 21 }),
    sectionBlock("Govern", "Independent Auditor\nExactly one revision\nExplicit human gate", { headingColor: COLORS.amber, bodySize: 21 }),
    sectionBlock("Execute", "Approved typed rules\nDeterministic engine\nExact evidence trace", { headingColor: COLORS.green, bodySize: 21 }),
  ];
  const xs = [42, 453, 865];
  const fills = [COLORS.blueSoft, COLORS.amberSoft, COLORS.greenSoft];
  const lines = ["#B9DCE8", "#F0D19C", "#B6DED3"];
  const labels = ["01  SOURCE", "02  GATE", "03  REVIEW QUEUE"];
  const items = [
    text([paragraph("Architecture keeps generative roles outside execution", 39, { bold: true, lineSpacingPercent: 93000 })], {
      name: "title",
      position: { left: 42, top: 36 }, width: 1196, height: 95,
      style: { fontSize: "39px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
    }),
    shape({ name: "baseline", geometry: "straightConnector1", fill: "none", line: { style: "solid", width: 1, fill: COLORS.line }, position: { left: 36, top: 566 }, width: 1270, height: 0.03 }),
  ];
  for (let i = 0; i < 3; i += 1) {
    items.push(
      shape({ name: `card-${i + 1}`, geometry: "roundRect", fill: fills[i], line: { style: "solid", width: 1, fill: lines[i] }, position: { left: xs[i], top: 151 }, width: 374, height: 376 }),
      text([cards[i].heading, cards[i].body], {
        name: `card-text-${i + 1}`,
        position: { left: xs[i] + 33, top: 194 }, width: 308, height: 260,
        style: { fontSize: "21px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      shape({ name: `dot-${i + 1}`, geometry: "ellipse", fill: COLORS.ink, position: { left: xs[i] - 6, top: 560 }, width: 12, height: 12 }),
      text([paragraph(labels[i], 19, { bold: true, color: COLORS.muted })], {
        name: `label-${i + 1}`,
        position: { left: xs[i], top: 594 }, width: 300, height: 34,
        style: { fontSize: "19px", typeface: "Helvetica Neue", color: COLORS.muted, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      })
    );
  }
  slide.compose(layers({ name: "codex-grid-layout-library#slide-18-policyimpact", width: "fill", height: "fill" }, items), { frame: { left: 0, top: 0, width: 1280, height: 720 }, baseUnit: 1 });
  addFooter(slide, 3);
  addNotes(
    slide,
    "This architecture draws a hard line between interpretation and execution. The Analyst and Auditor can only emit validated typed records. The workflow permits exactly one revision, and even a final Auditor acceptance does not authorize execution. A human must separately approve each rule pair. Only then can the deterministic engine evaluate the same synthetic claims and expose the exact policy evidence used. This design follows the spirit of NIST's govern-map-measure-manage framing and uses provenance as a first-class traceability concept.\n\n[Sources]\nhttps://doi.org/10.6028/NIST.AI.100-1\nhttps://hl7.org/fhir/R4/provenance.html"
  );
  return slide;
}

function buildWorkflowSlide(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = COLORS.white;
  const events = [
    { label: "ROUND 1", title: "Analyst proposes", body: "4 changes\nTyped candidate pairs\nExact sections + caveats" },
    { label: "CHALLENGE", title: "Auditor tests", body: "Accept / revise / abstain\nModifier logic challenged\nNo hidden rationale" },
    { label: "ROUND 2", title: "Revision closes", body: "3 accept · 1 abstain\nHuman approve / reject\nNo second AI loop" },
  ];
  const xs = [42, 453, 859];
  const items = [
    text([paragraph("Two roles, one revision, one explicit decision boundary", 39, { bold: true, lineSpacingPercent: 93000 })], {
      name: "title", position: { left: 42, top: 36 }, width: 1196, height: 95,
      style: { fontSize: "39px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
    }),
    text([paragraph("Ambiguity remains visible and non-executable; abstention is an allowed outcome.", 24, { color: COLORS.muted })], {
      name: "subtitle", position: { left: 42, top: 150 }, width: 1080, height: 45,
      style: { fontSize: "24px", typeface: "Helvetica Neue", color: COLORS.muted, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
    }),
    shape({ name: "timeline", geometry: "straightConnector1", fill: "none", line: { style: "solid", width: 2, fill: COLORS.line }, position: { left: 36, top: 344 }, width: 1260, height: 0.03 }),
  ];
  for (let i = 0; i < events.length; i += 1) {
    const event = events[i];
    items.push(
      text([paragraph(event.label, 16, { bold: true, color: COLORS.blue })], {
        name: `event-label-${i + 1}`, position: { left: xs[i], top: 284 }, width: 210, height: 32,
        style: { fontSize: "16px", typeface: "Helvetica Neue", color: COLORS.blue, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      shape({ name: `event-dot-${i + 1}`, geometry: "ellipse", fill: i === 2 ? COLORS.green : COLORS.blue, position: { left: xs[i] - 6, top: 338 }, width: 13, height: 13 }),
      text([paragraph(event.title, 25, { bold: true, spaceAfter: 500 }), paragraph(event.body, 20, { color: COLORS.muted, lineSpacingPercent: 114000 })], {
        name: `event-body-${i + 1}`, position: { left: xs[i], top: 388 }, width: 330, height: 190,
        style: { fontSize: "20px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      })
    );
  }
  slide.compose(layers({ name: "codex-grid-layout-library#slide-17-policyimpact", width: "fill", height: "fill" }, items), { frame: { left: 0, top: 0, width: 1280, height: 720 }, baseUnit: 1 });
  addFooter(slide, 4);
  addNotes(
    slide,
    "The workflow is deliberately bounded. In round one, the Analyst identifies four policy changes and proposes typed rule pairs with exact supporting sections and caveats. The Auditor independently checks those fields. One modifier rule is challenged because the policy supports a narrower qualification. The Analyst gets exactly one revision. The final fixture contains three accepted rules and one abstention. That is the end of the model loop: the human decision is separate, explicit, and recorded."
  );
  return slide;
}

function buildMetricsSlide(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = COLORS.white;
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-22-policyimpact", width: "fill", height: "fill" }, [
      text([paragraph("Controlled fixture replay validates the workflow plumbing", 39, { bold: true, lineSpacingPercent: 93000 })], {
        name: "title", position: { left: 42, top: 36 }, width: 1196, height: 95,
        style: { fontSize: "39px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      shape({ name: "chart-frame", geometry: "roundRect", fill: COLORS.white, line: { style: "solid", width: 1, fill: COLORS.line }, position: { left: 42, top: 136 }, width: 582, height: 488 }),
      text([paragraph("OFFLINE FIXTURE REPLAY", 16, { bold: true, color: COLORS.blue, spaceAfter: 500 }), paragraph("All reported values are deterministic checks against synthetic gold fixtures. They are not live-model accuracy, generalization, production savings, or clinical/payment performance.", 22, { color: COLORS.muted, lineSpacingPercent: 114000 })], {
        name: "scope-text", position: { left: 676, top: 173 }, width: 530, height: 185,
        style: { fontSize: "22px", typeface: "Helvetica Neue", color: COLORS.muted, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      text([paragraph("16 / 16", 36, { bold: true, color: COLORS.green }), paragraph("claim-impact records match gold", 18, { color: COLORS.muted })], {
        name: "stat-one", position: { left: 676, top: 410 }, width: 230, height: 120,
        style: { fontSize: "28px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      text([paragraph("20 / 20", 36, { bold: true, color: COLORS.blue }), paragraph("outputs retain exact traceability", 18, { color: COLORS.muted })], {
        name: "stat-two", position: { left: 965, top: 410 }, width: 235, height: 120,
        style: { fontSize: "28px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      text([paragraph("Final review: 3 accepted · 1 abstained · 0 unsupported assertions", 19, { bold: true, color: COLORS.ink })], {
        name: "decision-summary", position: { left: 676, top: 562 }, width: 530, height: 44,
        style: { fontSize: "19px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
    ]),
    { frame: { left: 0, top: 0, width: 1280, height: 720 }, baseUnit: 1 },
  );
  slide.charts.add("bar", {
    position: { left: 82, top: 174, width: 500, height: 402 },
    categories: ["Clearly affected", "Clearly unaffected", "Boundary", "Human review"],
    series: [{ name: "Synthetic claims", values: [6, 6, 2, 2], fill: COLORS.blue }],
    hasLegend: false,
    dataLabels: { showValue: true, position: "outEnd" },
    chartFill: COLORS.white,
    chartLine: { style: "solid", width: 0, fill: COLORS.white },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", width: 0, fill: COLORS.white },
    xAxis: {
      visible: true,
      deleted: false,
      majorUnit: 2,
      max: 7,
      majorGridlines: { style: "solid", width: 1, fill: "#E8EDF2" },
      line: { style: "solid", width: 0, fill: COLORS.white },
      textStyle: { typeface: "Helvetica Neue", fontSize: "12px", color: COLORS.muted },
    },
    yAxis: {
      visible: true,
      deleted: false,
      line: { style: "solid", width: 0, fill: COLORS.white },
      textStyle: { typeface: "Helvetica Neue", fontSize: "14px", color: COLORS.ink },
    },
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 70 },
  });
  addFooter(slide, 5);
  addNotes(
    slide,
    "The evaluation is a controlled fixture replay. The sixteen synthetic claims intentionally cover six clearly affected cases, six clearly unaffected cases, two boundary cases, and two human-review cases. The deterministic engine produced sixteen of sixteen expected impact records, and all twenty evaluated outputs retained the expected evidence trace. The final agent review had three accepted rules, one abstention, and zero unsupported final assertions. These checks validate the workflow plumbing; they do not estimate live-model performance or business value."
  );
  return slide;
}

function buildRecommendationSlide(presentation) {
  const slide = presentation.slides.add();
  slide.background.fill = COLORS.white;
  const checks = [
    "Freeze 10–20 approved policy pairs and gold criteria before model runs",
    "Use independent domain experts to author and adjudicate ground truth",
    "Run in a controlled environment; measure accuracy, abstention, traceability, and overrides",
    "Stop or roll back when evidence, safety, or approval gates fail",
  ];
  const items = [
    text([paragraph("Recommendation: run a result-blind, multi-policy pilot", 39, { bold: true, lineSpacingPercent: 93000 })], {
      name: "title", position: { left: 42, top: 36 }, width: 1196, height: 95,
      style: { fontSize: "39px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
    }),
    text([paragraph("The POC is ready to test as a governed review aid—not to deploy as an autonomous decision-maker.", 29, { color: COLORS.ink, lineSpacingPercent: 108000 })], {
      name: "recommendation", position: { left: 42, top: 172 }, width: 590, height: 125,
      style: { fontSize: "29px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
    }),
    shape({ name: "boundary-card", geometry: "roundRect", fill: COLORS.redSoft, line: { style: "solid", width: 1, fill: "#EBC2C2" }, position: { left: 42, top: 355 }, width: 585, height: 195 }),
    text([paragraph("BOUNDARIES", 16, { bold: true, color: COLORS.red, spaceAfter: 500 }), paragraph("No PHI · no clinical advice · no payment decision · no production deployment · no savings claim", 22, { bold: true, color: COLORS.ink, lineSpacingPercent: 113000 })], {
      name: "boundaries", position: { left: 76, top: 388 }, width: 515, height: 125,
      style: { fontSize: "22px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
    }),
  ];
  checks.forEach((value, i) => {
    const top = 160 + i * 105;
    items.push(
      shape({ name: `check-${i + 1}`, geometry: "ellipse", fill: COLORS.greenSoft, line: { style: "solid", width: 1, fill: COLORS.green }, position: { left: 704, top: top + 4 }, width: 27, height: 27 }),
      text([paragraph("✓", 17, { bold: true, color: COLORS.green, alignment: "center" })], {
        name: `checkmark-${i + 1}`, position: { left: 707, top: top + 5 }, width: 22, height: 22,
        style: { fontSize: "17px", typeface: "Helvetica Neue", color: COLORS.green, alignment: "center", verticalAlignment: "middle", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      }),
      text([paragraph(value, 21, { color: COLORS.ink, lineSpacingPercent: 110000 })], {
        name: `check-text-${i + 1}`, position: { left: 752, top }, width: 450, height: 72,
        style: { fontSize: "21px", typeface: "Helvetica Neue", color: COLORS.ink, autoFit: "shrinkText", insets: { top: 0, right: 0, bottom: 0, left: 0 } },
      })
    );
  });
  slide.compose(layers({ name: "codex-grid-layout-library#slide-10-policyimpact", width: "fill", height: "fill" }, items), { frame: { left: 0, top: 0, width: 1280, height: 720 }, baseUnit: 1 });
  addFooter(slide, 6);
  addNotes(
    slide,
    "My recommendation is a small, result-blind pilot rather than deployment. Freeze approved policy pairs and scoring criteria before any model run. Have independent experts create and adjudicate the gold set. Run in a controlled environment and measure not only extraction accuracy, but also abstention, unsupported assertions, evidence traceability, and human overrides. Define stop and rollback gates up front. The current proof of concept remains synthetic and does not support clinical, payment, savings, or production claims.\n\n[Sources]\nhttps://doi.org/10.6028/NIST.AI.100-1\nhttps://doi.org/10.6028/NIST.AI.600-1\nhttps://www.cotiviti.com/about/responsible-ai-use"
  );
  return slide;
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  await fs.mkdir(RENDERED, { recursive: true });
  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  buildTitleSlide(presentation);
  buildOpportunitySlide(presentation);
  buildArchitectureSlide(presentation);
  buildWorkflowSlide(presentation);
  buildMetricsSlide(presentation);
  buildRecommendationSlide(presentation);

  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(path.join(RENDERED, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(RENDERED, `${stem}.layout.json`), await layout.text());
  }
  await writeBlob(path.join(RENDERED, "montage.webp"), await presentation.export({ format: "webp", montage: true, scale: 1 }));
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(PPTX);
  console.log(PPTX);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
