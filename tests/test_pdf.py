from datetime import date

from pypdf import PdfReader
from io import BytesIO

from app.pdf import PdfRequest, build_pdf
from app.schemas import LineItem


def text_of(pdf: bytes) -> str:
    return "".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)


def req(**kw):
    base = dict(
        line_items=[LineItem(description="Wall painting", quantity=10, unit="m²", unit_price=20, total=999)],
        business_name="Smith Painting", client_name="Jane", job_address="1 Test St")
    base.update(kw)
    return PdfRequest(**base)


def test_totals_recalculated_from_line_items():
    text = text_of(build_pdf(req(), today=date(2026, 9, 28)))
    assert "$200.00" in text          # 10 x 20, not the stale 999
    assert "$220.00" in text          # + 10% AU GST
    assert "$999" not in text


def test_nz_gst():
    assert "$230.00" in text_of(build_pdf(req(region="NZ")))


def test_valid_until_date():
    assert "28 Oct 2026" in text_of(build_pdf(req(), today=date(2026, 9, 28)))
