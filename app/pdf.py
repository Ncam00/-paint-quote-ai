"""Turns a (possibly painter-edited) quote into a PDF for the homeowner."""
from datetime import date, timedelta
from io import BytesIO

from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from .pricing import GST
from .schemas import LineItem, Region

ACCENT = colors.HexColor("#1F4E79")


class PdfRequest(BaseModel):
    line_items: list[LineItem] = Field(min_length=1, max_length=50)
    region: Region = Region.AU
    business_name: str = Field(min_length=1, max_length=100)
    business_phone: str = Field(default="", max_length=40)
    business_email: str = Field(default="", max_length=100)
    business_number: str = Field(default="", max_length=30, description="ABN (AU) or NZBN")
    client_name: str = Field(min_length=1, max_length=100)
    job_address: str = Field(min_length=1, max_length=200)
    quote_number: str = Field(default="", max_length=30)
    valid_days: int = Field(default=30, ge=1, le=365)
    notes: str = Field(default="", max_length=1000)


def money(v: float) -> str:
    return f"${v:,.2f}"


def build_pdf(req: PdfRequest, today: date | None = None) -> bytes:
    today = today or date.today()
    # Recalculate from line items, so painter edits always add up correctly.
    items = [(i.description, round(i.quantity, 2), i.unit, i.unit_price,
              round(round(i.quantity, 2) * i.unit_price, 2)) for i in req.line_items]
    subtotal = round(sum(i[4] for i in items), 2)
    rate = GST[req.region]
    gst = round(subtotal * rate, 2)
    total = round(subtotal + gst, 2)

    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=body, fontSize=9, textColor=colors.HexColor("#555555"))
    title = ParagraphStyle("title", parent=body, fontSize=22, leading=26, textColor=ACCENT,
                           fontName="Helvetica-Bold")
    biz = ParagraphStyle("biz", parent=body, fontSize=14, leading=18, fontName="Helvetica-Bold")
    e = lambda s: escape(s).replace("\n", "<br/>")

    contact = " · ".join(e(x) for x in (req.business_phone, req.business_email) if x)
    tax_label = "ABN" if req.region == Region.AU else "NZBN"
    details = [f"<b>Date:</b> {today:%d %b %Y}",
               f"<b>Valid until:</b> {today + timedelta(days=req.valid_days):%d %b %Y}"]
    if req.quote_number:
        details.insert(0, f"<b>Quote #:</b> {e(req.quote_number)}")

    left = [Paragraph(e(req.business_name), biz)]
    if contact:
        left.append(Paragraph(contact, small))
    if req.business_number:
        left.append(Paragraph(f"{tax_label} {e(req.business_number)}", small))
    header = Table([[left, [Paragraph("QUOTE", title)] + [Paragraph(d, body) for d in details]]],
                   colWidths=[105 * mm, 65 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    client = Paragraph(f"<b>Prepared for</b><br/>{e(req.client_name)}<br/>{e(req.job_address)}", body)

    rows = [["Description", "Qty", "Unit price", "Amount"]]
    rows += [[Paragraph(e(d), body), f"{q:g} {e(u)}", money(p), money(t)] for d, q, u, p, t in items]
    table = Table(rows, colWidths=[85 * mm, 28 * mm, 28 * mm, 29 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6FA")]),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    totals = Table([["Subtotal", money(subtotal)],
                    [f"GST ({rate:.0%})", money(gst)],
                    ["Total", money(total)]], colWidths=[40 * mm, 29 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 2), (-1, 2), 13),
        ("LINEABOVE", (0, 2), (-1, 2), 1, ACCENT),
        ("TOPPADDING", (0, 2), (-1, 2), 8),
    ]))

    story = [header, Spacer(1, 10 * mm), client, Spacer(1, 8 * mm), table, Spacer(1, 4 * mm), totals]
    if req.notes:
        story += [Spacer(1, 8 * mm), Paragraph("<b>Notes</b>", body), Paragraph(e(req.notes), body)]
    story += [Spacer(1, 10 * mm),
              Paragraph("To accept this quote, reply to this email or call us. Prices include GST.", small)]

    buf = BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=18 * mm, bottomMargin=18 * mm,
                      title=f"Quote for {req.client_name}", author=req.business_name).build(story)
    return buf.getvalue()
