# Solar PV Forecaster — Backend

FastAPI + pvlib service. Weather ingestion, physics engine, forecast/past-date/analytics
API, calibration against logged production, and an AI layer behind a swappable
`AIProvider` interface (Mock or Gemini).

## Setup (Windows / PowerShell, per ENV.md)

```powershell
cd backend
uv sync --extra dev
copy .env.example .env
```

Leave `GEMINI_API_KEY` blank to use `MockProvider`; set it to use the real
`GeminiProvider` — no other code changes needed (see `api/deps.py::get_ai_provider`).

## Run

```powershell
uv run uvicorn backend.main:app --reload --port 8000
```

Visit http://127.0.0.1:8000/docs for the interactive API contract. On first
startup the app creates `solar_pv.db` (SQLite) and auto-seeds ~10 days of
synthetic production history for the frontend's default demo site, so the
dashboard isn't empty on first load (see `seed.py`).

## Test / lint / type-check

```powershell
uv run pytest --cov=backend --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
```

All four are clean — 76/76 tests, 95% coverage, zero lint/type errors.

## What's real vs. mocked

| Piece | Status |
|---|---|
| Open-Meteo forecast/archive, PVGIS clients | Real, tested against mocked HTTP responses |
| NASA POWER client | Written, untested, not wired into any route (see Known simplifications) |
| pvlib physics pipeline (clear-sky → POA → DC/AC power) | Real |
| `/api/forecast`, `/api/past` | Real end-to-end (weather → physics → response) |
| Calibration (bias correction, 7-day gating), rolling MAE, uncertainty band | Real |
| Tilt optimizer (PVGIS annual, clear-sky sim for current/daily) | Real |
| Loss breakdown, earnings/CO2 | Real |
| `AIProvider` | `MockProvider` (canned) or `GeminiProvider` (real Gemini API), selected by `GEMINI_API_KEY` |
| SQLite persistence (production log, demo seed) | Real |

## Known simplifications (stated plainly, not hidden)

- **Bias/MAE recomputation cost**: `/api/past` and `/api/forecast` re-fetch
  historical weather for every logged day at a site, on every call. Fine at
  demo scope (a handful of logged days); a real deployment would cache
  modeled-kWh per logged day instead of recomputing it each time.
- **"Forecast error" is really model error**: rolling MAE is computed against
  physics-modeled output using *actual* historical weather, not true
  lead-time forecast error at the horizon the forecast was originally made.
  A real deployment would track error per forecast horizon.
- **Loss breakdown categories are typical shares, not measured**: only the
  temperature-driven loss is computed dynamically from weather; the rest
  (soiling, shading, wiring, ...) are NREL PVWatts-default proportions of
  the array's lumped `system_loss_pct`.
- **Sites are identified by rounded coordinates**, not user accounts — there's
  no auth in the demo scope.
- **CAMS satellite irradiance layer**: designed for (see dev plan §1.2), not
  wired in — non-US coverage only, out of scope for this demo.
- **NASA POWER client** (`data_ingestion/nasa_power.py`): implemented against the
  real API but no route calls it and it has no test coverage — PVGIS covers the
  demo's regions, so this is unused fallback groundwork, not a finished path.
- **AI anomaly flagging**: `POST /api/ai/anomaly` works and is tested end-to-end
  for both providers, but nothing in the frontend calls it yet, so it never
  appears in the running demo.

## API contract

- `GET /health`
- `POST /api/forecast` — hourly AC power forecast, with an uncertainty band once calibrated
- `POST /api/past` — historical reconstruction, bias-corrected, with actual overlay
- `POST /api/calibration/production`, `GET /api/calibration/status` — log/check actual production
- `POST /api/analytics/tilt`, `/losses`, `/earnings` — tilt guidance, loss breakdown, earnings/CO2
- `POST /api/ai/summary`, `/chat`, `/anomaly` — AI layer (Mock or Gemini)

See `/docs` for full request/response schemas.
