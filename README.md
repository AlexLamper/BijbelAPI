# BijbelAPI

Dé #1 Nederlandse Bijbel API voor ontwikkelaars.

- Productie domein: `https://bijbelapi.com`
- Docs: `https://bijbelapi.com/docs`
- ReDoc: `https://bijbelapi.com/redoc`

## Wat deze API biedt

- Nederlandse Bijbel endpoints (`/api/verse`, `/api/chapter`, `/api/daytext`, ...)
- Parse endpoints voor complexe verwijzingen
- Nederlandse commentary endpoint
- Stripe billing flow voor betaalde API-toegang

## Ondersteunde vertalingen

- `nbg1951`
- `nld1939`
- `sv` (alias: `statenvertaling`)
- `bb` (optioneel, als databestand aanwezig is)

## Snelle start (lokaal)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/transform_bible_data.py
python -m uvicorn main:app --reload --port 8081
```

Open:
- `http://127.0.0.1:8081/`
- `http://127.0.0.1:8081/docs`

## Render deployment

Deze repo bevat `render.yaml` met:
- build command: `pip install -r requirements.txt`
- start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- healthcheck: `/health`

## Hostinger + domein checklist

1. Voeg `bijbelapi.com` toe als custom domain in Render.
2. Zet de DNS records in Hostinger exact zoals Render toont.
3. Stel redirect in:
   - `www.bijbelapi.com` -> `bijbelapi.com` (301)
4. Controleer SSL op Render (status: issued).

## Stripe setup

Verplichte variabelen:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID_PRO_MONTHLY`
- `STRIPE_PRICE_ID_PRO_YEARLY`
- `APP_BASE_URL` (bijv. `https://bijbelapi.com`)
- `BILLING_ENFORCED` (`true` in productie)

Belangrijke billing endpoints:

- `POST /billing/checkout-session`
- `POST /billing/portal-session`
- `GET /billing/status`
- `POST /stripe/webhook`

## Data pipeline (NBG1951/NLD1939)

Bronbestanden staan in:
- `non-transformed-data/nbg/nldnbg_vpl.txt`
- `non-transformed-data/nld/nldnbg_vpl.txt`

Converter:
- `scripts/transform_bible_data.py`

Output:
- `data/nbg1951.json`
- `data/nld1939.json`

## GitHub metadata (aanbevolen)

- Description:
  - `Dé #1 Nederlandse Bijbel API voor ontwikkelaars. FastAPI, Stripe-billing, Nederlandse vertalingen en commentary endpoints.`
- Topics:
  - `bible-api`, `dutch-bible`, `fastapi`, `python`, `rest-api`, `openapi`, `stripe`, `scripture`, `api-key-auth`

## Licentie

MIT
