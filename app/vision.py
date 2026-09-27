"""Sends room photos to Claude and gets back a structured Assessment."""
import base64
import os
from anthropic import Anthropic
from .schemas import Assessment

_client: Anthropic | None = None


def get_client() -> Anthropic:
    """Created on first use, so the app (and tests) start without a key."""
    global _client
    if _client is None:
        _client = Anthropic()  # reads ANTHROPIC_API_KEY
    return _client


PROMPT = """You are helping an Australian/New Zealand house painter quote an interior room.
Look at the photos and assess ONLY what you can see:
- overall wall condition (good / fair / poor)
- number of doors and windows in the room
- prep work needed (e.g. crack patching, sanding, mould treatment, stain sealing)
- whether the existing colour is dark enough to need an extra coat
Do NOT estimate prices or areas. If photos are unclear, lower your confidence
and say what's missing in notes. Record your answer with the tool."""

TOOL = {
    "name": "record_assessment",
    "description": "Record the visual assessment of the room.",
    "input_schema": Assessment.model_json_schema(),
}


def assess_room(images: list[tuple[bytes, str]]) -> Assessment:
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": mime,
                                     "data": base64.b64encode(data).decode()}}
        for data, mime in images
    ]
    content.append({"type": "text", "text": PROMPT})

    resp = get_client().messages.create(
        model=os.getenv("MODEL", "claude-sonnet-5"),
        max_tokens=1024,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "record_assessment"},
        messages=[{"role": "user", "content": content}],
    )
    tool_use = next(b for b in resp.content if b.type == "tool_use")
    return Assessment.model_validate(tool_use.input)  # rejects malformed AI output
