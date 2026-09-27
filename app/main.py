from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from .pricing import build_quote
from .schemas import Quote, RoomInput
from .vision import assess_room

app = FastAPI(title="Paint Quote AI")

ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024
MAX_PHOTOS = 5


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/quote", response_model=Quote)
async def quote(
    room: str = Form(..., description='JSON, e.g. {"length_m":4,"width_m":3.5,"height_m":2.7}'),
    photos: list[UploadFile] = File(...),
):
    try:
        room_input = RoomInput.model_validate_json(room)
    except ValidationError as e:
        raise HTTPException(422, e.errors())

    if not 1 <= len(photos) <= MAX_PHOTOS:
        raise HTTPException(400, f"Send 1–{MAX_PHOTOS} photos")

    images = []
    for p in photos:
        if p.content_type not in ALLOWED:
            raise HTTPException(400, f"{p.filename}: use JPEG, PNG or WebP")
        data = await p.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(400, f"{p.filename}: over 5 MB")
        images.append((data, p.content_type))

    try:
        assessment = assess_room(images)
    except ValidationError:
        raise HTTPException(502, "AI returned an invalid assessment, try again")

    return build_quote(room_input, assessment)
