from enum import Enum
from pydantic import BaseModel, Field


class Region(str, Enum):
    AU = "AU"  # 10% GST
    NZ = "NZ"  # 15% GST


class Condition(str, Enum):
    good = "good"
    fair = "fair"
    poor = "poor"


class RoomInput(BaseModel):
    length_m: float = Field(gt=0, le=50)
    width_m: float = Field(gt=0, le=50)
    height_m: float = Field(gt=0, le=10)
    coats: int = Field(default=2, ge=1, le=4)
    include_ceiling: bool = False
    region: Region = Region.AU


class Assessment(BaseModel):
    """What the AI sees in the photos. No prices, no maths."""
    wall_condition: Condition
    doors: int = Field(ge=0, le=10)
    windows: int = Field(ge=0, le=20)
    prep_items: list[str] = []
    dark_existing_colour: bool = False
    notes: str = ""
    confidence: float = Field(ge=0, le=1)


class LineItem(BaseModel):
    description: str
    quantity: float
    unit: str
    unit_price: float
    total: float


class Quote(BaseModel):
    assessment: Assessment
    wall_area_m2: float
    ceiling_area_m2: float
    paint_litres: float
    line_items: list[LineItem]
    subtotal: float
    gst: float
    total: float
    needs_review: bool
