from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT


PRIMARY = colors.HexColor("#185FA5")
LIGHT_BG = colors.HexColor("#f9fafb")
BORDER = colors.HexColor("#e5e7eb")
MUTED = colors.HexColor("#6b7280")
BLACK = colors.HexColor("#111111")


def generate_pdf(quote) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    bold = ParagraphStyle("bold", fontName="Helvetica-Bold", fontSize=10, textColor=BLACK)
    normal = ParagraphStyle("normal", fontName="Helvetica", fontSize=9, textColor=BLACK)
    muted = ParagraphStyle("muted", fontName="Helvetica", fontSize=8, textColor=MUTED)
    right = ParagraphStyle("right", fontName="Helvetica", fontSize=9, alignment=TA_RIGHT)
    right_bold = ParagraphStyle("right_bold", fontName="Helvetica-Bold", fontSize=10, alignment=TA_RIGHT)
    center = ParagraphStyle("center", fontName="Helvetica", fontSize=8, alignment=TA_CENTER, textColor=MUTED)

    subtotal = sum(item.final_price or 0 for item in quote.items)
    tax = round(subtotal * (quote.tax_pct / 100), 2)
    grand_total = round(subtotal + tax + (quote.adjustment or 0), 2)

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("<font color='#185FA5' size=16><b>Executive Ledger</b></font><br/>"
                  "<font color='#6b7280' size=8>Internal Quoting Tool</font>", styles["Normal"]),
        Paragraph(
            f"<font size=16><b>{quote.quote_number}</b></font><br/>"
            f"<font color='#6b7280' size=8>Version {quote.version}</font><br/>"
            f"<font color='#1e40af' size=8><b>{quote.status.upper()}</b></font>",
            ParagraphStyle("hdr_right", alignment=TA_RIGHT, fontSize=9)
        ),
    ]]
    header_table = Table(header_data, colWidths=[90*mm, 90*mm])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_table)
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 5*mm))

    # ── Client + Quote Details ───────────────────────────────────────────────
    def field(label, value):
        return [Paragraph(label, muted), Paragraph(str(value) if value else "—", normal)]

    validity = quote.validity_date.strftime("%b %d, %Y") if quote.validity_date else "—"
    created = quote.created_at.strftime("%b %d, %Y")

    info_data = [
        [Paragraph("<b>CLIENT INFORMATION</b>", muted), Paragraph("<b>QUOTE DETAILS</b>", muted)],
        [
            Table([
                field("Company", quote.client.company_name),
                field("Contact", quote.client.contact_name),
                field("Email", quote.client.email),
                field("Phone", quote.client.phone),
            ], colWidths=[22*mm, 60*mm]),
            Table([
                field("Quote Number", quote.quote_number),
                field("Issue Date", created),
                field("Valid Until", validity),
                field("Currency", quote.currency),
            ], colWidths=[22*mm, 60*mm]),
        ]
    ]
    info_table = Table(info_data, colWidths=[90*mm, 90*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6*mm))

    # ── Line Items ───────────────────────────────────────────────────────────
    story.append(Paragraph("<b>LINE ITEMS</b>", muted))
    story.append(Spacer(1, 2*mm))

    item_rows = [[
        Paragraph("<b>#</b>", muted),
        Paragraph("<b>Product</b>", muted),
        Paragraph("<b>Size/Cap.</b>", muted),
        Paragraph("<b>Color</b>", muted),
        Paragraph("<b>Lead Time</b>", muted),
        Paragraph("<b>Qty</b>", ParagraphStyle("muted_r", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)),
        Paragraph("<b>Unit Price</b>", ParagraphStyle("muted_r", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)),
        Paragraph("<b>Disc%</b>", ParagraphStyle("muted_r", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)),
        Paragraph("<b>Amount</b>", ParagraphStyle("muted_r", fontSize=8, textColor=MUTED, alignment=TA_RIGHT)),
    ]]

    for i, item in enumerate(quote.items, 1):
        desc = f"<b>{item.product_name}</b>"
        if item.description:
            desc += f"<br/><font color='#6b7280' size=7>{item.description}</font>"
        item_rows.append([
            Paragraph(f"{i:02d}", muted),
            Paragraph(desc, normal),
            Paragraph(item.size_capacity or "—", normal),
            Paragraph(item.color or "—", normal),
            Paragraph(item.lead_time or "—", normal),
            Paragraph(str(item.quantity), right),
            Paragraph(f"{quote.currency} {item.unit_price:.2f}", right),
            Paragraph(f"{item.discount_pct}%", right),
            Paragraph(f"{quote.currency} {(item.final_price or 0):.2f}", right_bold),
        ])

    items_table = Table(item_rows, colWidths=[8*mm, 42*mm, 18*mm, 18*mm, 18*mm, 12*mm, 22*mm, 12*mm, 22*mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 1, BORDER),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4*mm))

    # ── Totals ───────────────────────────────────────────────────────────────
    totals_rows = [
        [Paragraph("Subtotal", muted), Paragraph(f"{quote.currency} {subtotal:.2f}", right)],
        [Paragraph(f"Tax ({quote.tax_pct}%)", muted), Paragraph(f"{quote.currency} {tax:.2f}", right)],
    ]
    if quote.adjustment:
        totals_rows.append([
            Paragraph("Adjustment", muted),
            Paragraph(f"{quote.currency} {quote.adjustment:.2f}", right)
        ])
    totals_rows.append([
        Paragraph("<b>Grand Total Due</b>", bold),
        Paragraph(f"<b>{quote.currency} {grand_total:.2f}</b>", right_bold),
    ])

    totals_table = Table(totals_rows, colWidths=[130*mm, 42*mm])
    totals_table.setStyle(TableStyle([
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, BLACK),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)

    # ── Notes & Terms ────────────────────────────────────────────────────────
    if quote.notes:
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("<b>NOTES</b>", muted))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(quote.notes, normal))

    if quote.terms:
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("<b>TERMS &amp; CONDITIONS</b>", muted))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(quote.terms, normal))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"Executive Ledger &nbsp;|&nbsp; {quote.quote_number} v{quote.version} &nbsp;|&nbsp; Generated {created}",
        center
    ))

    doc.build(story)
    return buffer.getvalue()
