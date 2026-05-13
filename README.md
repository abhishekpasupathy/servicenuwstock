# DadStock

DadStock is a small full-stack stock dashboard I built for my dad so he can check a few stocks without bouncing between finance sites. It keeps the interface simple: search a ticker, see the latest quote, review the chart, and skim basic company details.

The app uses free public market data through `yfinance`, so it is useful for tracking and learning, not for trading decisions.

## Features

- Ticker search with validation
- Latest quote, day range, volume, market cap, and daily move
- Historical close chart with `1M`, `3M`, `6M`, `1Y`, and `MAX` views
- Company profile with sector, industry, country, website, and summary
- Backend response caching to reduce repeated upstream calls
- Degraded fallback responses when the upstream provider is rate limited
- Dark, responsive dashboard UI

## Tech Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS, Recharts
- Backend: FastAPI, Pydantic, yfinance, pandas
- Cache: in-memory TTL cache plus SQLite response cache
- Deployment: Vercel for the frontend, Render for the backend

## Architecture

```text
Browser
  -> Vercel Next.js app
  -> NEXT_PUBLIC_API_BASE_URL
  -> Render FastAPI service
  -> yfinance / Yahoo Finance
```

The deployed frontend should call the backend with a base URL ending in `/api`.

```text
https://servicenuwstock-api.onrender.com/api/quote/AAPL
https://servicenuwstock-api.onrender.com/api/snapshot/AAPL
```

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── requirements.txt
│   └── runtime.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   └── package.json
├── render.yaml
└── README.md
```

## API Routes

Base URL:

```text
https://servicenuwstock-api.onrender.com/api
```

Routes:

- `GET /health`
- `GET /quote/{ticker}`
- `GET /profile/{ticker}`
- `GET /history/{ticker}?period=1y&interval=1d`
- `GET /snapshot/{ticker}?period=1y&interval=1d`

The frontend dashboard uses `/snapshot/{ticker}` because it needs quote, profile, and history data in one request. Smaller components can use `/quote`, `/profile`, or `/history` directly.

## Local Setup

Backend:

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

For local backend development, set `frontend/.env.local` to:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
NEXT_PUBLIC_DEFAULT_TICKER=NOW
NEXT_TELEMETRY_DISABLED=1
```

Backend environment example:

```bash
APP_NAME=DadStock API
APP_ENV=development
API_PREFIX=/api
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SQLITE_PATH=./data/dadstock.sqlite
CACHE_TTL_SECONDS=300
MARKET_CACHE_TTL_SECONDS=1800
MARKET_FALLBACK_CACHE_TTL_SECONDS=600
```

## Deployment

### Backend on Render

The root `render.yaml` is ready for a Render web service. The important settings are:

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`

Production environment variables:

```bash
APP_NAME=DadStock API
APP_ENV=production
API_PREFIX=/api
BACKEND_CORS_ORIGINS=https://your-vercel-app.vercel.app
SQLITE_PATH=/tmp/dadstock.sqlite
CACHE_TTL_SECONDS=300
MARKET_CACHE_TTL_SECONDS=1800
MARKET_FALLBACK_CACHE_TTL_SECONDS=600
```

After deployment, confirm:

```text
https://servicenuwstock-api.onrender.com/api/health
https://servicenuwstock-api.onrender.com/api/snapshot/AAPL
```

### Frontend on Vercel

Set the Vercel project root to `frontend` and use the normal Next.js preset.

Required frontend environment variables:

```bash
NEXT_PUBLIC_API_BASE_URL=https://servicenuwstock-api.onrender.com/api
NEXT_PUBLIC_DEFAULT_TICKER=NOW
NEXT_TELEMETRY_DISABLED=1
```

Redeploy the frontend after changing `NEXT_PUBLIC_API_BASE_URL`; Next.js reads public environment variables at build time.

## Screenshots

Add screenshots here after the next production deploy.

- Dashboard overview
- Ticker search result
- Mobile layout

## Future Improvements

- Watchlist saved in local storage
- Basic portfolio notes for tracked tickers
- More chart indicators such as moving averages
- Better provider abstraction if a paid market data API is added later
- Unit tests for backend response shaping and frontend API helpers

## Disclaimer

This project is for personal tracking and education. Market data can be delayed, incomplete, or unavailable because it comes from free public sources. Nothing in this app is financial advice.
