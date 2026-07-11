import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { ApiError, fetchForecast, fetchHealth } from './api/client'
import { AnalyticsPanel } from './components/AnalyticsPanel'
import { PastCalibrationPanel } from './components/PastCalibrationPanel'
import { SettingsPage } from './components/SettingsPage'
import { AiAssistantPanel } from './chat/AiAssistantPanel'
import { StatusBar, type ServiceStatus } from './components/StatusBar'
import { loadSettings, saveSettings, type AppSettings } from './settings'
import type { ForecastRequest, ForecastResponse, HourlyPowerPoint } from './types'

const ForecastChart = lazy(() => import('./components/ForecastChart').then((m) => ({ default: m.ForecastChart })))

type Tab = 'forecast' | 'past' | 'analytics' | 'ai'
type View = 'app' | 'settings'

function toSiteRequest(settings: AppSettings): ForecastRequest {
    return { location: settings.location, arrays: [settings.array], horizon_hours: settings.horizon_hours }
}

function sumKwh(points: HourlyPowerPoint[]): number {
    return Math.round(points.reduce((sum, h) => sum + h.ac_power_kw, 0) * 100) / 100
}

function peakKw(points: HourlyPowerPoint[]): number {
    return points.length ? Math.max(...points.map((h) => h.ac_power_kw)) : 0
}

// Built once per forecast so the AI assistant has enough to answer "today"/
// "tomorrow" questions specifically, not just a flat multi-day total — it can
// only answer from what's in here (see backend chat system prompt), so a
// thin context means "I don't have that" for anything not spelled out below.
function buildForecastContext(forecast: ForecastResponse | null): string {
    if (!forecast) return 'No forecast run yet — general solar PV question.'

    const now = new Date()
    const tomorrow = new Date(now)
    tomorrow.setDate(tomorrow.getDate() + 1)

    const todayPoints = forecast.hourly.filter((h) => new Date(h.timestamp).toDateString() === now.toDateString())
    const tomorrowPoints = forecast.hourly.filter(
        (h) => new Date(h.timestamp).toDateString() === tomorrow.toDateString(),
    )

    const parts = [
        `Today's date: ${now.toISOString().slice(0, 10)}.`,
        `Site at ${forecast.location.latitude}, ${forecast.location.longitude}, ${forecast.total_capacity_kw}kW installed.`,
    ]

    parts.push(
        todayPoints.length > 0
            ? `Remaining forecast for today (from now until midnight): ${sumKwh(todayPoints).toFixed(1)}kWh, peak ${peakKw(todayPoints).toFixed(2)}kW.`
            : "No forecast hours remain for today in this window.",
    )
    if (tomorrowPoints.length > 0) {
        parts.push(`Forecast for tomorrow: ${sumKwh(tomorrowPoints).toFixed(1)}kWh, peak ${peakKw(tomorrowPoints).toFixed(2)}kW.`)
    }
    parts.push(
        `Total forecast over the next ${forecast.hourly.length}h: ${sumKwh(forecast.hourly).toFixed(1)}kWh, peak ${peakKw(forecast.hourly).toFixed(2)}kW.`,
    )
    if (forecast.is_calibrated) {
        parts.push(`This site is calibrated against logged production, with ${(forecast.mae_pct * 100).toFixed(0)}% typical error.`)
    }
    return parts.join(' ')
}

export default function App() {
    const [view, setView] = useState<View>('app')
    const [tab, setTab] = useState<Tab>('forecast')
    const [visitedTabs, setVisitedTabs] = useState<Set<Tab>>(new Set(['forecast']))
    const [settings, setSettings] = useState<AppSettings>(loadSettings)
    const [forecast, setForecast] = useState<ForecastResponse | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [backendStatus, setBackendStatus] = useState<ServiceStatus>('checking')
    const [weatherStatus, setWeatherStatus] = useState<ServiceStatus>('checking')
    const [aiProvider, setAiProvider] = useState<'mock' | 'gemini' | null>(null)

    const site = useMemo(() => toSiteRequest(settings), [settings])

    function selectTab(next: Tab) {
        setTab(next)
        setVisitedTabs((curr) => (curr.has(next) ? curr : new Set(curr).add(next)))
    }

    const runForecast = useCallback(async (request: ForecastRequest) => {
        setIsLoading(true)
        setError(null)
        try {
            const result = await fetchForecast(request)
            setForecast(result)
            setWeatherStatus('ok')
        } catch (err) {
            setError(err instanceof ApiError ? err.message : 'Something went wrong fetching the forecast.')
            // A 502 from this endpoint specifically means the weather provider failed
            // upstream (see backend/api/routes/forecast.py) — anything else (4xx) is
            // a request-shape problem, not a weather outage.
            setWeatherStatus(err instanceof ApiError && err.status === 502 ? 'degraded' : 'checking')
        } finally {
            setIsLoading(false)
        }
    }, [])

    // Show a real forecast immediately on load, using the saved (or default)
    // site — no empty form to fill in before anything appears.
    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- deliberate fetch-on-mount; loading state can't be derived
        runForecast(site)
        fetchHealth()
            .then((health) => {
                setBackendStatus('ok')
                setAiProvider(health.ai_provider)
            })
            .catch(() => setBackendStatus('down'))
        // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally runs once, on mount only
    }, [])

    function handleSaveSettings(next: AppSettings) {
        setSettings(next)
        saveSettings(next)
        setView('app')
        runForecast(toSiteRequest(next))
    }

    const totalKwh = forecast ? sumKwh(forecast.hourly) : null
    const peakKwValue = forecast ? peakKw(forecast.hourly) : null
    const forecastContext = buildForecastContext(forecast)

    return (
        <div className="app-shell">
            <div className="top-bar">
                <span className="top-bar-title">☀ Solar PV Forecaster</span>
                <StatusBar backendStatus={backendStatus} weatherStatus={weatherStatus} aiProvider={aiProvider} />
            </div>

            {view === 'settings' ? (
                <SettingsPage value={settings} onSave={handleSaveSettings} onClose={() => setView('app')} />
            ) : (
                <>
                    <div className="tab-bar">
                        <div className="tab-bar-tabs">
                            <button className={tab === 'forecast' ? 'tab active' : 'tab'} onClick={() => selectTab('forecast')}>
                                Forecast
                            </button>
                            <button className={tab === 'past' ? 'tab active' : 'tab'} onClick={() => selectTab('past')}>
                                Past & calibration
                            </button>
                            <button className={tab === 'analytics' ? 'tab active' : 'tab'} onClick={() => selectTab('analytics')}>
                                Analytics
                            </button>
                            <button className={tab === 'ai' ? 'tab active' : 'tab'} onClick={() => selectTab('ai')}>
                                AI assistant
                            </button>
                        </div>
                        <button className="icon-btn" aria-label="Settings" title="Settings" onClick={() => setView('settings')}>
                            ⚙
                        </button>
                    </div>

                    <div className={tab === 'forecast' ? undefined : 'hidden'}>
                        <div className="card">
                            <div className="panel-header">
                                <h2>Forecast</h2>
                                {isLoading && <span className="updating-note">Updating…</span>}
                            </div>

                            {error && <div className="error-banner">{error}</div>}

                            {forecast && (
                                <>
                                    <div className="stat-row">
                                        <div className="stat">
                                            <span className="value">{totalKwh?.toFixed(1)} kWh</span>
                                            <span className="label">Total over horizon</span>
                                        </div>
                                        <div className="stat">
                                            <span className="value">{peakKwValue?.toFixed(2)} kW</span>
                                            <span className="label">Peak output</span>
                                        </div>
                                        <div className="stat">
                                            <span className="value">{forecast.total_capacity_kw} kW</span>
                                            <span className="label">Installed capacity</span>
                                        </div>
                                        {forecast.is_calibrated && (
                                            <span className="badge badge-success badge-inline">
                                                Calibrated (±{(forecast.mae_pct * 100).toFixed(0)}%)
                                            </span>
                                        )}
                                    </div>
                                    <Suspense fallback={<div className="empty-state">Loading chart…</div>}>
                                        <ForecastChart hourly={forecast.hourly} />
                                    </Suspense>
                                </>
                            )}
                        </div>
                    </div>

                    <div className={tab === 'past' ? undefined : 'hidden'}>
                        {visitedTabs.has('past') && <PastCalibrationPanel location={site.location} arrays={site.arrays} />}
                    </div>
                    <div className={tab === 'analytics' ? undefined : 'hidden'}>
                        {visitedTabs.has('analytics') && (
                            <AnalyticsPanel
                                location={site.location}
                                array={site.arrays[0]}
                                defaultEnergyKwh={totalKwh}
                                defaultPricePerKwh={settings.price_per_kwh}
                                gridCo2KgPerKwh={settings.grid_co2_kg_per_kwh}
                                currencySymbol={settings.currency_symbol}
                            />
                        )}
                    </div>
                    <div className={tab === 'ai' ? undefined : 'hidden'}>
                        {visitedTabs.has('ai') && <AiAssistantPanel location={site.location} forecastContext={forecastContext} />}
                    </div>
                </>
            )}
        </div>
    )
}
