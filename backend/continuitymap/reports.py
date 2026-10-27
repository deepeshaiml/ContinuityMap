from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#102638")
TEAL = colors.HexColor("#087F8C")
PALE = colors.HexColor("#EAF1F4")


def _pdf(
    title: str,
    subtitle: str,
    sections: list[tuple[str, list[str]]],
    tables: list[tuple[str, list[list[str]]]] = (),
) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CMTitle",
            parent=styles["Title"],
            textColor=NAVY,
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CMSection",
            parent=styles["Heading2"],
            textColor=TEAL,
            fontSize=12,
            leading=15,
            spaceBefore=11,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CMBody", parent=styles["BodyText"], fontSize=9, leading=13, spaceAfter=4
        )
    )
    story = [
        Paragraph(
            "CONTINUITYMAP · SYNTHETIC EXERCISE",
            styles["Kicker"] if "Kicker" in styles else styles["Normal"],
        ),
        Paragraph(title, styles["CMTitle"]),
        Paragraph(subtitle, styles["CMBody"]),
        Spacer(1, 5),
    ]
    for heading, lines in sections:
        story.append(Paragraph(heading, styles["CMSection"]))
        for line in lines:
            story.append(Paragraph(line, styles["CMBody"]))
    for heading, rows in tables:
        story.append(Paragraph(heading, styles["CMSection"]))
        styled_rows = [[Paragraph(str(cell), styles["CMBody"]) for cell in row] for row in rows]
        table = Table(styled_rows, repeatRows=1, hAlign="LEFT", colWidths=None)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CFD9DE")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.extend([table, Spacer(1, 5)])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#627785"))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(
            17 * mm,
            10 * mm,
            "Planning support only · Verify with service owners · Generated "
            + datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        )
        canvas.drawRightString(A4[0] - 17 * mm, 10 * mm, f"{doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


def impact_pdf(graph, result) -> bytes:
    node_map = {node.id: node.name for node in graph.nodes}
    rows = [["Node", "Status", "Declared basis"]]
    for item in result.explanations:
        rows.append([item.node_name, item.status.replace("_", " "), item.reason])
    return _pdf(
        "Disruption impact report",
        result.scenario_name,
        [
            (
                "Scenario method",
                [
                    result.caveat,
                    f"Explicit disruption seeds: {', '.join(node_map.get(key, key) for key in result.disrupted_nodes)}.",
                    f"Affected entries include the explicit scenario seed(s); total listed: {len(result.affected_nodes)}.",
                    f"Unverified paths requiring review: {len(result.uncertain_review_nodes)}.",
                ],
            ),
            (
                "How to read this report",
                [
                    "A downstream status reflects only a verified dependency rule in the saved graph. A proposed or unknown relationship is not treated as a failed service."
                ],
            ),
        ],
        [("Declared impact trace", rows)],
    )


def gaps_pdf(graph, validation) -> bytes:
    rows = [["Item", "State", "Evidence / question", "Owner"]]
    for edge in graph.edges:
        if edge.verification_status.value != "verified":
            rows.append(
                [
                    f"{edge.source} → {edge.dependent}",
                    edge.verification_status.value,
                    edge.evidence + " (" + edge.evidence_ref + ")",
                    edge.owner,
                ]
            )
    for relationship in graph.unknown_relationships:
        rows.append(
            [
                f"{relationship.source} → {relationship.dependent}",
                "unknown",
                relationship.question,
                relationship.owner,
            ]
        )
    for issue in validation.issues:
        if issue.severity in {"error", "warning"}:
            rows.append(
                [
                    issue.object_id or "graph",
                    issue.severity + ": " + issue.code,
                    issue.message,
                    "Graph steward",
                ]
            )
    return _pdf(
        "Dependency gap report",
        graph.title,
        [
            (
                "Review scope",
                [
                    f"Graph integrity: {'valid' if validation.valid else 'has errors'}; {validation.counts['warnings']} warning(s).",
                    "This report lists proposed and unknown relationships, plus integrity warnings. It does not infer that a missing edge is absent in the real world.",
                ],
            )
        ],
        [
            (
                "Relationships and validation findings",
                rows or [["—", "none", "No gaps recorded", "—"]],
            )
        ],
    )


def checklist_pdf(graph, result) -> bytes:
    rows = [["Review action", "Evidence status", "Reviewer / date"]]
    actions = []
    scenario = next((item for item in graph.scenarios if item.name == result.scenario_name), None)
    if scenario:
        actions.extend(scenario.review_actions)
    actions.extend(
        [
            f"Validate declared path: {' → '.join(item.path)} ({', '.join(item.edge_ids)})"
            for item in result.explanations
            if item.status == "affected" and item.edge_ids
        ]
    )
    actions.extend(
        [f"Resolve unverified possible path: {node}" for node in result.uncertain_review_nodes]
    )
    for action in dict.fromkeys(actions):
        rows.append([action, "Open — human review required", ""])
    return _pdf(
        "Human-reviewed continuity checklist",
        result.scenario_name,
        [
            (
                "Review instruction",
                [
                    "Complete and sign this checklist with accountable service owners. It is a planning aid and does not change service status or approve a recovery plan.",
                    result.caveat,
                ],
            )
        ],
        [("Actions for review", rows)],
    )
