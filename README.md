# Paint Quote AI

Upload room photos + dimensions → get a draft painting quote.
The AI assesses the photos (condition, doors/windows, prep work);
deterministic Python does all area, paint and price maths.

## Run it
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your Anthropic API key
pytest                 # pricing tests, no API key needed
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs to try `/quote` in the browser.

## Try with curl
```bash
curl -X POST localhost:8000/quote \
  -F 'room={"length_m":4,"width_m":3.5,"height_m":2.7,"include_ceiling":true,"region":"AU"}' \
  -F photos=@room1.jpg -F photos=@room2.jpg
```

## Next steps
- Replace the rates in `app/pricing.py` with real painters' numbers
- Deploy (Render/Railway/Fly) and call `/quote` from the Base44 app
- Save quotes to Postgres; add PDF export
