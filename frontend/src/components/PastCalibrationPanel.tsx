import { useEffect, useState } from 'react'
import { fetchPastDate, fetchProductionHistory, logProduction, ApiError } from '../api/client'
import type { Location, PastDateResponse, ProductionHistoryEntry, PVArrayInput } from '../types'

interface PastCalibrationPanelProps {
    location: Location
    arrays: PVArrayInput[]
}

function yesterdayIso(): string {
    const d = new Date()
    d.setDate(d.getDate() - 1)
    return d.toISOString().slice(0, 10)
}

function Sparkline({ entries }: { entries: ProductionHistoryEntry[] }) {
    if (entries.length < 2) return null
    const chronological = [...entries].reverse()
    const values = chronological.map((e) => e.actual_kwh)
    const max = Math.max(...values, 1)
    const width = 100
    const height = 32
    const step = width / (values.length - 1)
    const points = values.map((v, i) => `${i * step},${height - (v / max) * height}`).join(' ')

    return (
        <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true">
            <polyline points={points} fill="none" stroke="#4ac3ff" strokeWidth="2" vectorEffect="non-scaling-stroke" />
        </svg>
    )
}

export function PastCalibrationPanel({ location, arrays }: PastCalibrationPanelProps) {
    const [date, setDate] = useState(yesterdayIso())
    const [result, setResult] = useState<PastDateResponse | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(false)

    const [isLogging, setIsLogging] = useState(false)
    const [actualKwh, setActualKwh] = useState(15)
    const [logMessage, setLogMessage] = useState<string | null>(null)

    const [history, setHistory] = useState<ProductionHistoryEntry[]>([])
    const [historyCount, setHistoryCount] = useState(0)

    function refreshHistory() {
        fetchProductionHistory(location)
            .then((response) => {
                setHistory(response.entries)
                setHistoryCount(response.n_days_logged)
            })
            .catch(() => {
                /* history is a secondary view; a failed refresh isn't worth surfacing as an error banner */
            })
    }

    useEffect(() => {
        let cancelled = false
        // eslint-disable-next-line react-hooks/set-state-in-effect -- deliberate fetch-on-prop-change; loading state can't be derived
        setIsLoading(true)
        setError(null)
        fetchPastDate({ location, arrays, date })
            .then((response) => !cancelled && setResult(response))
            .catch((err) => !cancelled && setError(err instanceof ApiError ? err.message : 'Could not load that date.'))
            .finally(() => !cancelled && setIsLoading(false))
        return () => {
            cancelled = true
        }
    }, [location, arrays, date])

    useEffect(() => {
        refreshHistory()
        // eslint-disable-next-line react-hooks/exhaustive-deps -- refreshHistory is stable in behavior; only `location` should retrigger
    }, [location])

    async function handleLogProduction() {
        setError(null)
        try {
            const response = await logProduction({ location, date, actual_kwh: actualKwh })
            setLogMessage(`Logged — ${response.n_days_logged}/7 days recorded for this site.`)
            setIsLogging(false)
            const refreshed = await fetchPastDate({ location, arrays, date })
            setResult(refreshed)
            refreshHistory()
        } catch (err) {
            setError(err instanceof ApiError ? err.message : 'Could not log production.')
        }
    }

    return (
        <div className="card">
            <div className="panel-header">
                <h2>Past date</h2>
                <input
                    type="date"
                    aria-label="Date"
                    value={date}
                    max={yesterdayIso()}
                    onChange={(e) => {
                        setDate(e.target.value)
                        setLogMessage(null)
                    }}
                />
            </div>

            {error && <div className="error-banner">{error}</div>}

            {isLoading && !result && <div className="empty-state">Loading…</div>}

            {result && (
                <div className="stat-row">
                    <div className="stat">
                        <span className="value">{result.modeled_kwh.toFixed(1)} kWh</span>
                        <span className="label">Modeled</span>
                    </div>
                    <div className="stat">
                        <span className="value">{result.calibrated_kwh.toFixed(1)} kWh</span>
                        <span className="label">Bias-corrected</span>
                    </div>
                    <div className="stat">
                        <span className="value">{result.actual_kwh !== null ? `${result.actual_kwh.toFixed(1)} kWh` : '—'}</span>
                        <span className="label">Actual logged</span>
                    </div>
                    <span className={`badge badge-inline ${result.is_calibrated ? 'badge-success' : 'badge-warning'}`}>
                        {result.is_calibrated ? `Calibrated (±${(result.mae_pct * 100).toFixed(0)}%)` : 'Not yet calibrated'}
                    </span>
                </div>
            )}

            {logMessage && <div className="info-banner">{logMessage}</div>}

            {!isLogging ? (
                <button className="btn-link" onClick={() => setIsLogging(true)}>
                    + Log actual production for {date}
                </button>
            ) : (
                <div className="log-production-row">
                    <div className="field">
                        <label htmlFor="actual-kwh">Actual output (kWh)</label>
                        <input
                            id="actual-kwh"
                            type="number"
                            step="0.1"
                            min="0"
                            value={actualKwh}
                            onChange={(e) => setActualKwh(Number(e.target.value))}
                        />
                    </div>
                    <button className="btn-accent" onClick={handleLogProduction}>
                        Save
                    </button>
                    <button className="btn-link" onClick={() => setIsLogging(false)}>
                        Cancel
                    </button>
                </div>
            )}

            <hr className="section-divider" />

            <h3>Production history</h3>
            <p className="calibration-progress">{historyCount}/7 days logged for calibration</p>

            {history.length >= 2 && <Sparkline entries={history} />}

            {history.length === 0 ? (
                <div className="empty-state">No production logged yet for this site.</div>
            ) : (
                <ul className="history-list">
                    {history.map((entry) => (
                        <li key={entry.date}>
                            <span>{entry.date}</span>
                            <span>{entry.actual_kwh.toFixed(1)} kWh</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}
