# Solar PV Forecaster — Frontend

React (Vite) app, four tabs: **Forecast**, **Past & calibration**, **Analytics**, **AI assistant** —
all wired to the real backend API.

## Setup (Windows / PowerShell, per ENV.md)

```powershell
cd frontend
npm install
```

## Run

```powershell
npm run dev
```

Visit http://localhost:5173 — the dev server proxies `/api` and `/health` to the
backend on port 8000 (see `vite.config.ts`), so run the backend first.

## Build / type-check / lint

```powershell
npm run build   # tsc -b && vite build
npm run lint     # eslint .
```

Clean as of Day 5 — no type errors, no lint errors, `npm audit`: 0 vulnerabilities.
Main bundle ~50 kB gzip; the forecast chart (recharts) is lazy-loaded on first
forecast, per react-best-practices bundle-size guidance.

## Structure

```
src/
├── api/client.ts          # typed fetch client against the locked backend contract
├── components/            # ForecastChart, PastCalibrationPanel, AnalyticsPanel, SettingsPage, StatusBar
├── chat/                  # AiAssistantPanel — talks to /api/ai/summary and /api/ai/chat
├── constants.ts           # shared default location/array used across panels
├── types.ts                # mirrors backend Pydantic schemas
└── App.tsx                 # tab shell
```

## Accessibility pass (Day 5)

WCAG contrast check on every Aura palette text/background pairing actually used
in the app (see calculation in project history / ISSUES.md #10 context):

| Pairing | Ratio | AA normal text (4.5:1) |
|---|---|---|
| text-primary on bg | 17.85:1 | Pass |
| text-secondary on bg / card | 8.26:1 / 7.48:1 | Pass |
| accent on bg (links/buttons) | 9.75:1 | Pass |
| bg on accent (button text) | 9.75:1 | Pass |
| bg on success (badge text) | 10.89:1 | Pass |
| danger text on bg (error banner) | 5.91:1 | Pass |

One real failure was caught and fixed: the Aura skill's own example CSS for
`.badge-warning` (white text on `--color-warning`) is only 2.59:1, well under
AA. Switched to dark (`--color-bg`) text on that badge — 7.49:1.

Also added: visible `:focus-visible` outlines on tabs, the secondary button,
selects, and the chat input (previously only present on the primary button
and form inputs); an `aria-label` on the chat input, which has no visible
`<label>`.

Not done: a full screen-reader pass or automated axe-core scan — out of scope
for a demo-day accessibility pass, noted here rather than left unstated.
