# NOW Intelligence

Public stock dashboard with a Next.js frontend and FastAPI backend. The frontend is designed for Vercel, and the backend is designed for Render or Railway.

## Public Architecture

- Browser loads the Next.js app from Vercel.
- Vercel frontend calls the deployed FastAPI backend at `https://<backend-host>/api`.
- FastAPI serves `/api/snapshot/{ticker}` and health checks.
- Backend uses in-memory cache for hot responses and SQLite for persistent response cache.
- yfinance/Yahoo Finance remains the upstream market data provider, with retry and fallback sample data when throttled.

## Run Locally

Backend:

```bash
cd backend
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

Local frontend env:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
NEXT_PUBLIC_DEFAULT_TICKER=NOW
NEXT_TELEMETRY_DISABLED=1
```

Local backend env:

```bash
APP_NAME=NOW Intelligence API
APP_ENV=development
API_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SQLITE_PATH=./data/now_intelligence.sqlite
CACHE_TTL_SECONDS=300
MARKET_CACHE_TTL_SECONDS=1800
MARKET_FALLBACK_CACHE_TTL_SECONDS=600
```

## Backend Deployment: Render

1. Push this repository to GitHub.
2. In Render, create a new Web Service from the repo.
3. Set the root directory to `backend`.
4. Use Python runtime.
5. Build command:

```bash
pip install -r requirements.txt
```

6. Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

7. Add backend environment variables:

```bash
APP_NAME=NOW Intelligence API
APP_ENV=production
API_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=https://your-vercel-app.vercel.app
SQLITE_PATH=/tmp/now_intelligence.sqlite
CACHE_TTL_SECONDS=300
MARKET_CACHE_TTL_SECONDS=1800
MARKET_FALLBACK_CACHE_TTL_SECONDS=600
```

8. Deploy and confirm:

```text
https://your-render-service.onrender.com/api/v1/health
https://your-render-service.onrender.com/api/snapshot/NOW
```

The included `render.yaml` can also be used as a Render Blueprint. You must still set `BACKEND_CORS_ORIGINS` to the deployed Vercel origin.

## Backend Deployment: Railway

1. Create a Railway project from the repo.
2. Select the `backend` directory as the service root.
3. Railway/Nixpacks will install from `requirements.txt`.
4. The included `backend/railway.json` starts the app with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

5. Add the same backend environment variables listed above, with `BACKEND_CORS_ORIGINS` set to the Vercel URL.

For Railway persistent cache, use a mounted volume and set:

```bash
SQLITE_PATH=/data/now_intelligence.sqlite
```

## Frontend Deployment: Vercel

1. Import the repository into Vercel.
2. Set the project root directory to `frontend`.
3. Framework preset should be Next.js.
4. Build command:

```bash
npm run build
```

5. Install command:

```bash
npm install
```

6. Add frontend environment variables:

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-backend-host.com/api
NEXT_PUBLIC_DEFAULT_TICKER=NOW
NEXT_TELEMETRY_DISABLED=1
```

7. Deploy the frontend.
8. Copy the final Vercel URL back into the backend `BACKEND_CORS_ORIGINS` value.
9. Redeploy the backend after updating CORS.

## Required Environment Variables

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`: Deployed backend API base URL ending in `/api`.
- `NEXT_PUBLIC_DEFAULT_TICKER`: Initial ticker shown in the dashboard.
- `NEXT_TELEMETRY_DISABLED`: Set to `1`.

Backend:

- `APP_NAME`: API display name.
- `APP_ENV`: Use `production` in public deployments.
- `API_PREFIX`: Health API prefix, usually `/api/v1`.
- `BACKEND_CORS_ORIGINS`: Comma-separated deployed frontend origins. Do not use localhost in production.
- `SQLITE_PATH`: SQLite cache path.
- `CACHE_TTL_SECONDS`: Hot in-memory default TTL.
- `MARKET_CACHE_TTL_SECONDS`: Successful market response TTL.
- `MARKET_FALLBACK_CACHE_TTL_SECONDS`: Degraded fallback response TTL.

## Production Notes

- The frontend has no localhost fallback in code. `NEXT_PUBLIC_API_BASE_URL` must be configured during Vercel build.
- The backend rejects production startup if CORS origins are missing, wildcarded, or still pointing at localhost.
- CORS origins must be origins only, such as `https://your-app.vercel.app`, not paths and not trailing API URLs.
- Render free services may sleep after inactivity. The first request after sleep can be slow.
- Free Render filesystem storage is ephemeral. Use Railway volumes or a paid Render disk if cache persistence across redeploys matters.

## Recommended Providers

- Frontend: Vercel free tier.
- Backend: Render for the simplest beginner setup, or Railway if you want easier persistent volumes.
- Domain: Start with provider subdomains, then add a custom domain later.

## Current Limitations

- No authentication yet.
- No Docker or Kubernetes yet.
- yfinance/Yahoo throttling can still occur.
- SQLite cache is appropriate for a single backend instance, not horizontally scaled deployments.
