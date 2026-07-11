# Solar PV Forecaster

[![CI](https://github.com/MatejKukec/solar-pv-forecaster/actions/workflows/ci.yml/badge.svg)](https://github.com/MatejKukec/solar-pv-forecaster/actions/workflows/ci.yml)

*Replace `OWNER/REPO` above once pushed to GitHub — the badge goes green automatically
once `.github/workflows/ci.yml` runs (see [`DEPLOYMENT.md`](DEPLOYMENT.md) step 1).*

PV power forecasting, historical reconstruction, calibration against real production,
and an AI layer — built as a portfolio demo in a 6-day sprint. React frontend, FastAPI
+ pvlib backend.

**Live demo:** not deployed from here — see [`DEPLOYMENT.md`](DEPLOYMENT.md) to deploy
your own (free tier, ~10 minutes: Render for the backend, Vercel for the frontend).

## What it does

- **Forecast** — hourly PV power forecast (up to 15 days out) from live Open-Meteo
  weather, run through a real `pvlib` physics pipeline (clear-sky → plane-of-array
  transposition → cell temperature → DC/AC conversion), for up to 5 arrays at a site.
- **Past & calibration** — reconstruct modeled output for any past date from historical
  weather, log actual production against it, and get a bias-corrected estimate once a
  site has 7+ logged days. The forecast tab then shows an uncertainty band derived from
  that site's rolling mean-absolute-error.
- **Analytics** — optimal fixed-tilt guidance (PVGIS typical-year, or a clear-sky
  simulation for a specific day), a loss diagnostic breakdown, and earnings/CO₂-avoided
  estimates.
- **AI assistant** — plain-language forecast summaries and a chat Q&A grounded in the
  site's forecast context. Backed by Gemini (free tier) when `GEMINI_API_KEY` is set, a
  deterministic mock otherwise. A third capability, anomaly flagging when actual output
  deviates >20% from modeled, is implemented and tested on the backend (`/api/ai/anomaly`)
  but not yet called from the UI — see "Explicitly not built" below.

The dashboard auto-seeds ~10 days of synthetic production history for the default demo
site on first load, so there's something to look at immediately — see `backend/seed.py`.

## How it's calculated

Everything below is deterministic physics (via `pvlib`) plus simple statistics —
there's no trained ML model anywhere in the numeric pipeline. The AI layer (Gemini)
only narrates results in plain language; it never touches a number.

**Forecast — 5-stage physics pipeline** (`physics_engine/pv_model.py`):

1. **Weather** — Open-Meteo hourly GHI/DNI/DHI, air temperature, and wind speed for
   the site's coordinates.
2. **POA transposition** — `pvlib.solarposition` computes sun position; then
   `pvlib.irradiance.get_total_irradiance` transposes horizontal irradiance onto the
   array's actual tilt/azimuth plane.
3. **Cell temperature** — Faiman model (`pvlib.temperature.faiman`), from POA
   irradiance, air temp, and wind speed.
4. **DC power** — `pvlib.pvsystem.pvwatts_dc`, with a fixed -0.4%/°C temperature
   coefficient (generic crystalline-silicon default; per-panel presets aren't wired in).
5. **AC power** — `pvlib.inverter.pvwatts`, then the array's lumped system-loss % is
   applied as a final multiplier.

**Calibration** (`calibration/bias.py`, `calibration/mae.py`): once a site has ≥7
logged production days, `actual/modeled` is computed per day and averaged into one
multiplicative bias factor (below 7 days, factor = 1.0, no correction). Rolling mean
absolute error between modeled and actual kWh, as a %, becomes the forecast's
`uncertainty_kw` band (`power × mae_pct` per hour) — this is historical model error,
not true lead-time forecast error.

**Tilt optimization** (`analytics/tilt.py`): "annual" mode uses PVGIS's own
typical-year optimal-angle endpoint; "current"/"daily" mode (or a PVGIS fallback)
brute-forces a clear-sky simulation (Ineichen model) across tilts in 5° steps and
picks whichever maximizes total POA irradiance.

**Loss breakdown** (`analytics/losses.py`): the lumped system-loss % is split into
named categories (soiling, shading, wiring, mismatch, connections, inverter,
availability) using NREL PVWatts' typical proportional shares — industry defaults,
not measured per-site. Temperature loss is the one category computed dynamically,
from modeled cell temperature.

**Earnings / CO₂** (`analytics/earnings.py`): `kWh × price_per_kwh` and
`kWh × grid_co2_kg_per_kwh` (default 0.4 kg/kWh if no local figure is supplied).

## Architecture

```
backend/src/backend/
├── config.py            # settings from env / .env
├── data_ingestion/       # Open-Meteo, PVGIS, NASA POWER — pure I/O, no logic
├── physics_engine/       # pvlib wrappers: clear-sky, POA transposition, DC/AC power
├── calibration/           # bias correction, rolling MAE, 7-day gating
├── analytics/              # tilt optimizer, loss breakdown, earnings/CO2
├── ai_layer/                # AIProvider interface + MockProvider + GeminiProvider
├── models/                   # domain entities (Location, PVArray) + SQLModel tables
├── db.py, seed.py             # SQLite persistence + demo-data seeding
├── api/                        # FastAPI routes — the contract the React app builds against
└── tests/                       # 76 tests, 95% coverage

frontend/src/
├── api/client.ts         # typed fetch client against the locked backend contract
├── components/            # ForecastChart, PastCalibrationPanel, AnalyticsPanel, SettingsPage, StatusBar
├── chat/                    # AiAssistantPanel
└── App.tsx                   # tab shell (Forecast / Past & calibration / Analytics / AI)
```

**Why modular:** each piece has one job and a defined interface, so any one of them —
especially the AI provider — can be swapped without touching the others.
`data_ingestion` and `physics_engine` are provider-agnostic; swapping Open-Meteo for
another weather source touches one file. `calibration` only depends on `physics_engine`
output plus logged actuals, so it was built and tested against mock data before real
history existed. `api/` is the seam between backend and frontend — its shape was locked
on day 1, which is what let both sides build in parallel.

### The `AIProvider` swap pattern

```python
class AIProvider(Protocol):
    async def summarize(self, forecast_context: str) -> str: ...
    async def chat(self, message: str, forecast_context: str) -> str: ...
    async def flag_anomaly(self, actual_kw: float, expected_kw: float, context: str) -> str | None: ...
```

`MockProvider` (canned responses, no network calls) was built on day 1 so the rest of
the app — calibration, analytics, the React chat UI — could be developed and tested
without waiting on a real AI backend. `GeminiProvider` landed on day 3, implementing the
same interface against the real Gemini API. Which one is active is decided in exactly
one place:

```python
# backend/api/deps.py
def get_ai_provider() -> AIProvider:
    if settings.gemini_api_key:
        return GeminiProvider()
    return MockProvider()
```

Swapping in Claude, or any other model, means writing one new class that implements
`AIProvider` and adding one line to that function — nothing else in the app changes.

## What's real vs. mocked

| Piece | Status |
|---|---|
| Weather ingestion (Open-Meteo, PVGIS) | Real, tested against mocked HTTP responses |
| NASA POWER client | Written, untested, not wired into any route — see "Explicitly not built" |
| Physics pipeline (pvlib) | Real |
| Forecast, past-date reconstruction | Real end-to-end |
| Calibration (bias correction), rolling MAE, uncertainty band | Real |
| Tilt optimizer, loss breakdown, earnings/CO2 | Real |
| AI layer | Real (Gemini) once `GEMINI_API_KEY` is set, otherwise a deterministic mock |
| Persistence (SQLite: production log, demo seed) | Real |

Full known-simplifications list (stated openly rather than hidden) is in
[`backend/README.md`](backend/README.md#known-simplifications).

## Explicitly not built

- Notifications/push, PWA installability — need a product decision that doesn't matter
  for a demo.
- Full calibration validation (held-out testing, overfitting checks) — the 7-day gating
  is a stated simplification, not a claim of statistical rigor.
- CAMS satellite irradiance layer — real and free, but scoped to non-US regions by the
  provider; designed for, not wired in.
- NASA POWER fallback client — written against the real API (`data_ingestion/nasa_power.py`),
  but no route calls it yet and it has no test coverage; PVGIS covers the demo's regions,
  so this is groundwork for non-PVGIS locations, not a finished fallback path.
- AI anomaly flagging — `POST /api/ai/anomaly` is implemented and tested for both
  `MockProvider` and `GeminiProvider`, but the frontend never calls it, so it doesn't
  surface anywhere in the running app. The natural hook is `PastCalibrationPanel`'s
  log-production flow; wiring it in is a small, self-contained follow-up.
- User accounts/auth — sites are identified by rounded coordinates, not logins.

## Running it

See [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md)
for setup, or [`DEPLOYMENT.md`](DEPLOYMENT.md) to put it online.

```powershell
# backend
cd backend && uv sync --extra dev && copy .env.example .env
uv run uvicorn backend.main:app --reload --port 8000

# frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Quality signal

- Backend: 76 tests, 95% coverage, `ruff check`/`ruff format --check`/`mypy --strict` all clean.
- Frontend: `tsc -b`/`eslint` clean, 0 `npm audit` vulnerabilities.
- CI: `.github/workflows/ci.yml` runs all of the above on every push/PR.
- `ISSUES.md` tracks every bug found during development and how it was fixed —
  including ones a smoke test caught that unit tests alone wouldn't have (a date-type
  mismatch in the production-log endpoint, and a test-isolation bug from auto-seeded
  demo data colliding with test fixtures).

## Tech stack

Python 3.12, FastAPI, pvlib, SQLModel/SQLite, `uv` · React, Vite, TypeScript, recharts ·
Open-Meteo, PVGIS, NASA POWER, Gemini (free tiers) · Render + Vercel
