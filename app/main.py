from dotenv import load_dotenv
load_dotenv()

import os

import anthropic
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .pricing import build_quote
from .schemas import Quote, RoomInput
from .security import require_api_key
from . import vision

app = FastAPI(title="Paint Quote AI")

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["X-API-Key", "Content-Type"],
    )

def _mark_file_fields(node):
    """Make /docs show real file pickers (Swagger UI needs format: binary)."""
    if isinstance(node, dict):
        variants = node.get("anyOf")
        if variants and any(v.get("contentMediaType") for v in variants):
            node.pop("anyOf")
            node.update({"type": "string", "format": "binary"})
        if node.get("contentMediaType") == "application/octet-stream":
            node["format"] = "binary"
        for v in node.values():
            _mark_file_fields(v)
    elif isinstance(node, list):
        for v in node:
            _mark_file_fields(v)


_default_openapi = app.openapi


def _openapi_with_file_pickers():
    if not app.openapi_schema:
        _mark_file_fields(_default_openapi())
    return app.openapi_schema


app.openapi = _openapi_with_file_pickers

ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/quote", response_model=Quote, dependencies=[Depends(require_api_key)])
async def quote(
    room: str = Form(..., description='JSON, e.g. {"length_m":4,"width_m":3.5,"height_m":2.7}'),
    photo_1: UploadFile = File(..., description="Room photo (required)"),
    photo_2: UploadFile | None = File(None, description="Optional extra angle"),
    photo_3: UploadFile | None = File(None, description="Optional extra angle"),
):
    try:
        room_input = RoomInput.model_validate_json(room)
    except ValidationError as e:
        raise HTTPException(422, e.errors(include_url=False))

    photos = [p for p in (photo_1, photo_2, photo_3) if p is not None and p.filename]
    images = []
    for p in photos:
        if p.content_type not in ALLOWED:
            raise HTTPException(400, f"{p.filename}: use JPEG, PNG or WebP")
        data = await p.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(400, f"{p.filename}: over 5 MB")
        images.append((data, p.content_type))

    try:
        assessment = vision.assess_room(images)
    except ValidationError:
        raise HTTPException(502, "AI returned an invalid assessment, try again")
    except anthropic.APIError:
        raise HTTPException(502, "AI service unavailable, try again shortly")

    return build_quote(room_input, assessment)
