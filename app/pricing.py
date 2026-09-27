"""All the maths lives here, so quotes are predictable and testable."""
import math
from .schemas import Assessment, Condition, LineItem, Quote, Region, RoomInput

# Tune these with real painters' numbers.
DOOR_M2 = 1.9
WINDOW_M2 = 1.5
COVERAGE_M2_PER_L = 12.0
PAINT_PRICE_PER_L = 18.0
LABOUR_PER_M2 = 14.0
PREP_MULTIPLIER = {Condition.good: 1.0, Condition.fair: 1.15, Condition.poor: 1.35}
PREP_ITEM_FLAT = 45.0
GST = {Region.AU: 0.10, Region.NZ: 0.15}
REVIEW_THRESHOLD = 0.6


def build_quote(room: RoomInput, a: Assessment) -> Quote:
    perimeter = 2 * (room.length_m + room.width_m)
    wall_area = max(perimeter * room.height_m - a.doors * DOOR_M2 - a.windows * WINDOW_M2, 0)
    ceiling_area = room.length_m * room.width_m if room.include_ceiling else 0.0

    coats = room.coats + (1 if a.dark_existing_colour else 0)
    paint_area = (wall_area + ceiling_area) * coats
    litres = math.ceil(paint_area / COVERAGE_M2_PER_L)

    labour_rate = LABOUR_PER_M2 * PREP_MULTIPLIER[a.wall_condition]
    items = [
        _item(f"Wall painting ({coats} coats)", wall_area, "m²", labour_rate),
        _item("Paint", litres, "L", PAINT_PRICE_PER_L),
    ]
    if ceiling_area:
        items.insert(1, _item("Ceiling painting", ceiling_area, "m²", labour_rate))
    for prep in a.prep_items:
        items.append(_item(f"Prep: {prep}", 1, "item", PREP_ITEM_FLAT))

    subtotal = round(sum(i.total for i in items), 2)
    gst = round(subtotal * GST[room.region], 2)
    return Quote(
        assessment=a,
        wall_area_m2=round(wall_area, 2),
        ceiling_area_m2=round(ceiling_area, 2),
        paint_litres=litres,
        line_items=items,
        subtotal=subtotal,
        gst=gst,
        total=round(subtotal + gst, 2),
        needs_review=a.confidence < REVIEW_THRESHOLD,
    )


def _item(desc: str, qty: float, unit: str, price: float) -> LineItem:
    qty = round(qty, 2)
    return LineItem(description=desc, quantity=qty, unit=unit,
                    unit_price=round(price, 2), total=round(qty * price, 2))
