from app.pricing import build_quote
from app.schemas import Assessment, RoomInput


def make(**kw):
    base = dict(wall_condition="good", doors=1, windows=1, confidence=0.9)
    base.update(kw)
    return Assessment(**base)


def test_wall_area_subtracts_openings():
    q = build_quote(RoomInput(length_m=4, width_m=3, height_m=2.5), make())
    assert q.wall_area_m2 == 2 * 7 * 2.5 - 1.9 - 1.5


def test_poor_walls_cost_more():
    room = RoomInput(length_m=4, width_m=3, height_m=2.5)
    assert build_quote(room, make(wall_condition="poor")).total > build_quote(room, make()).total


def test_nz_gst_is_15_percent():
    q = build_quote(RoomInput(length_m=4, width_m=3, height_m=2.5, region="NZ"), make())
    assert q.gst == round(q.subtotal * 0.15, 2)


def test_low_confidence_flags_review():
    q = build_quote(RoomInput(length_m=4, width_m=3, height_m=2.5), make(confidence=0.3))
    assert q.needs_review
