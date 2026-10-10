"""Paginated investment report from an authorized stored property snapshot (F-15)."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.services.properties import get_property_detail


def investment_pdf(db: Session, listing_id: str, run_id: str | None = None) -> bytes:
    detail = get_property_detail(db, listing_id, run_id)
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "Evidence",
            parent=styles["BodyText"],
            fontSize=8,
            leading=11,
            wordWrap="CJK",
            spaceAfter=5,
        )
    )
    story = []

    def paragraph(text, style="BodyText"):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])

    def section(title, text):
        story.extend([Spacer(1, 12), paragraph(title, "Heading2"), paragraph(text)])

    story.extend(
        [
            paragraph("REALTY INTEL", "Title"),
            paragraph("Investment research report", "Heading1"),
            paragraph(detail.listing.name, "Heading2"),
            paragraph(f"Run: {detail.run_id} | Property: {listing_id}", "Evidence"),
            paragraph(f"Observed: {detail.listing.last_seen_at.isoformat()}", "Evidence"),
        ]
    )
    section(
        "Property facts",
        "Quoted portal entries may represent ranges or projects rather "
        "than individual units. Confirm the same unit and current terms with the source.",
    )
    for model, heading in ((detail.listing, "Facts"), (detail.metrics, "Investment estimates")):
        if heading != "Facts":
            section(
                heading,
                "Gross estimates before costs. Past price growth is historical; "
                "an investor override is an assumption. This is not a guaranteed return.",
            )
        if model is None:
            story.append(paragraph("Unavailable for this candidate."))
            continue
        rows = []
        for name in (
            "price_inr",
            "size_sqft",
            "price_per_sqft",
            "bedrooms",
            "status",
            "property_type",
            "locality",
            "est_monthly_rent_inr",
            "rental_yield_pct",
            "price_growth_pct",
            "total_return_pct",
            "price_vs_area_pct",
        ):
            fact = getattr(model, name, None)
            if fact is None:
                continue
            text = "Unknown" if fact.value is None else str(fact.value)
            if name.endswith("inr") and fact.value is not None:
                text = f"INR {fact.value:,.0f}"
            text += f" | confidence {fact.confidence:.0%} | {fact.method}"
            if fact.note:
                text += f". {fact.note}"
            rows.append(
                [paragraph(name.replace("_", " "), "Evidence"), paragraph(text, "Evidence")]
            )
        if rows:
            table = Table(rows, colWidths=[140, 355], hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                    ]
                )
            )
            story.append(table)
    check = detail.verification
    section(
        "Relevance and recommendation",
        f"{check.verdict}, match {check.match_score}/100"
        if check
        else "Not AI-checked in this run.",
    )
    if detail.recommendation:
        story.append(paragraph(detail.recommendation.reason))
    if check:
        for flag in check.flags:
            story.append(paragraph(f"{flag.kind}: {flag.reason}", "Evidence"))
    section("Risk evidence screening", detail.risk.note if detail.risk else "Unknown")
    refs = list(detail.sources)
    if detail.risk:
        for item in detail.risk.indicators:
            story.append(paragraph(f"{item.kind}: {item.status}. {item.next_step}"))
            for evidence in item.evidence:
                story.append(paragraph(evidence, "Evidence"))
            refs.extend(item.sources)
    if detail.area:
        section("Locality evidence", detail.area.summary or "Summary unavailable.")
        for issue in detail.area.warnings:
            story.append(paragraph(f"Unavailable: {issue.section}. {issue.message}", "Evidence"))
        refs.extend(news.source for news in detail.area.news)
    section(
        "Sources",
        "Links below identify the underlying search evidence. They do not "
        "independently verify accuracy. Review retrieval dates and current availability.",
    )
    seen = set()
    for ref in refs:
        key = (ref.url, ref.search_id)
        if key in seen:
            continue
        seen.add(key)
        story.append(
            paragraph(
                f"{ref.title or ref.engine}: {ref.url or ref.search_id or 'No URL'}", "Evidence"
            )
        )

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(
            50, 25, "Realty Intel | Stored evidence and estimates | Not investment advice"
        )
        canvas.drawRightString(A4[0] - 50, 25, f"Page {doc.page}")

    SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=50,
        rightMargin=50,
        topMargin=45,
        bottomMargin=45,
        title="Realty Intel investment report",
        author="Realty Intel",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
