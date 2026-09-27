# Paint Quote AI

![tests](https://github.com/Ncam00/-paint-quote-ai/actions/workflows/tests.yml/badge.svg)

Upload room photos + dimensions → get a draft painting quote.
The AI assesses the photos (condition, doors/windows, prep work);
deterministic Python does all area, paint and price maths.

## Run it locally
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your Anthropic key + a SERVICE_API_KEY
pytest                 # no API key needed
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs, click **Authorize**, enter your `SERVICE_API_KEY`, then try `/quote`.

## Call the API
```bash
curl -X POST https://YOUR-URL/quote \
  -H "X-API-Key: $SERVICE_API_KEY" \
  -F 'room={"length_m":4,"width_m":3.5,"height_m":2.7,"include_ceiling":true,"region":"AU"}' \
  -F photo_1=@room1.jpg -F photo_2=@room2.jpg   # photo_2/photo_3 optional
```

## Security
- Every `/quote` call needs the `X-API-Key` header (`/health` is open)
- Rate limited per key (`RATE_LIMIT_PER_HOUR`, default 20)
- CORS off unless `ALLOWED_ORIGINS` is set; call it server-side where possible

## Deploy (Render)
1. render.com → **New → Blueprint** → pick this repo (uses `render.yaml`)
2. Enter `ANTHROPIC_API_KEY` when prompted; leave `ALLOWED_ORIGINS` blank
3. Render generates `SERVICE_API_KEY` — copy it into your Base44 app's secrets
4. Check `https://YOUR-URL/health` returns `{"ok": true}`

Every push to `main` redeploys automatically.
