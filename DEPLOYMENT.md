# Deployment

Frontend and backend deploy as two separate services (free tiers on both sides).
This doc is instructions to run yourself — it can't be executed from here, since
it needs your own Render/Vercel accounts and a live GitHub repo connected to them.

## 1. Push to GitHub

```powershell
git init
git add .
git commit -m "Solar PV Forecaster"
git remote add origin <your-repo-url>
git push -u origin main
```

`.gitignore` already excludes `.venv`, `node_modules`, `*.db`, and `.env`.

## 2. Backend → Render

1. On [render.com](https://render.com), **New → Blueprint**, connect the repo.
   Render reads `render.yaml` at the repo root automatically.
2. Set the `GEMINI_API_KEY` env var (Render dashboard → Environment) if you
   want real AI responses — leave it blank to keep `MockProvider`.
3. Leave `CORS_ORIGINS` blank for now; you'll set it after step 3 below.
4. Deploy. Note the resulting URL, e.g. `https://solar-pv-forecaster-backend.onrender.com`.
   Free tier spins down after 15 min idle — first request after that takes ~30-60s.

## 3. Frontend → Vercel

1. On [vercel.com](https://vercel.com), **New Project**, import the repo,
   set **Root Directory** to `frontend`.
2. Add a build-time env var: `VITE_API_BASE_URL` = the Render backend URL
   from step 2 (no trailing slash).
3. Deploy. Note the resulting URL, e.g. `https://solar-pv-forecaster.vercel.app`.

## 4. Close the loop: CORS

Back on Render, set `CORS_ORIGINS` to the Vercel URL from step 3, then redeploy
the backend (Render → Manual Deploy). Without this the frontend's requests
will be blocked by the browser's CORS policy.

## Alternatives

- **Frontend on Netlify** instead of Vercel: same idea — root directory
  `frontend`, build command `npm run build`, publish directory `dist`, same
  `VITE_API_BASE_URL` env var.
- **Backend on Railway or Fly.io** instead of Render: both can build directly
  from `backend/Dockerfile`. Same env vars as `render.yaml` lists
  (`DATABASE_URL`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `CORS_ORIGINS`, `DEBUG`).
  Mount a persistent volume for `DATABASE_URL`'s directory or the SQLite file
  resets on every redeploy.

## Local development (no deployment needed)

```powershell
# terminal 1
cd backend
uv sync --extra dev
copy .env.example .env
uv run uvicorn backend.main:app --reload --port 8000

# terminal 2
cd frontend
npm install
npm run dev
```

Visit http://localhost:5173 — the Vite dev server proxies `/api` to
`localhost:8000` (see `frontend/vite.config.ts`), so `VITE_API_BASE_URL`
isn't needed locally.
