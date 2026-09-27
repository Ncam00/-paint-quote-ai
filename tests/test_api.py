import json

import pytest
from fastapi.testclient import TestClient

from app import main, vision
from app.schemas import Assessment
from app.security import reset_rate_limits

ROOM = json.dumps({"length_m": 4, "width_m": 3.5, "height_m": 2.7})
PHOTO = {"photo_1": ("room.jpg", b"fake-image-bytes", "image/jpeg")}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SERVICE_API_KEY", "test-key")
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "2")
    monkeypatch.setattr(vision, "assess_room", lambda images: Assessment(
        wall_condition="fair", doors=1, windows=2, confidence=0.8))
    reset_rate_limits()
    return TestClient(main.app)


def post(client, key="test-key"):
    headers = {"X-API-Key": key} if key else {}
    return client.post("/quote", data={"room": ROOM}, files=PHOTO, headers=headers)


def test_health_needs_no_key(client):
    assert client.get("/health").status_code == 200


def test_missing_key_rejected(client):
    assert post(client, key=None).status_code == 401


def test_wrong_key_rejected(client):
    assert post(client, key="nope").status_code == 401


def test_valid_key_returns_quote(client):
    r = post(client)
    assert r.status_code == 200
    assert r.json()["total"] > 0


def test_rate_limit(client):
    assert post(client).status_code == 200
    assert post(client).status_code == 200
    r = post(client)
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_bad_file_type_rejected(client):
    files = {"photo_1": ("notes.txt", b"hi", "text/plain")}
    r = client.post("/quote", data={"room": ROOM}, files=files, headers={"X-API-Key": "test-key"})
    assert r.status_code == 400


def test_multiple_photos_and_blank_optional(client):
    files = {"photo_1": ("a.jpg", b"x", "image/jpeg"), "photo_2": ("b.png", b"y", "image/png")}
    r = client.post("/quote", data={"room": ROOM, "photo_3": ""}, files=files,
                    headers={"X-API-Key": "test-key"})
    assert r.status_code == 200
