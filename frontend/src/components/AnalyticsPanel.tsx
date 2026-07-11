import { useEffect, useRef, useState } from 'react'
import { ApiError, fetchEarnings, fetchLossBreakdown, fetchOptimalTilt } from '../api/client'
import type { EarningsResponse, Location, LossResponse, PVArrayInput, TiltMode, TiltResponse } from '../types'

interface AnalyticsPanelProps {
    location: Location
    array: PVArrayInput
    defaultEnergyKwh: number | null
    defaultPricePerKwh: number
    gridCo2KgPerKwh: number
    currencySymbol: string
}

const LOSS_LABELS: Record<string, string> = {
    soiling: 'Soiling',
    shading: 'Shading',
    wiring: 'Wiring',
    mismatch: 'Mismatch',
    connections: 'Connections',
    inverter: 'Inverter',
    availability: 'Availability',
}

export function AnalyticsPanel({
    location,
    array,
    defaultEnergyKwh,
    defaultPricePerKwh,
    gridCo2KgPerKwh,
    currencySymbol,
}: AnalyticsPanelProps) {
    const [tiltMode, setTiltMode] = useState<TiltMode>('annual')
    const [tilt, setTilt] = useState<TiltResponse | null>(null)
    const [losses, setLosses] = useState<LossResponse | null>(null)
    const [energyKwh, setEnergyKwh] = useState(defaultEnergyKwh ?? 500)
    const [pricePerKwh, setPricePerKwh] = useState(defaultPricePerKwh)
    const [earnings, setEarnings] = useState<EarningsResponse | null>(null)
    const [error, setError] = useState<string | null>(null)

    const lastTiltKey = useRef<string | null>(null)
    const lastLossKey = useRef<string | null>(null)

    // Tilt and losses are read-only reports of the current site — load them as
    // soon as the tab opens, no click required. The key guard skips a refetch
    // when the params haven't actually changed (React StrictMode intentionally
    // double-invokes effects in dev; without this, every params-unchanged
    // re-render would re-hit the API).
    useEffect(() => {
        const key = JSON.stringify({ location, tiltMode })
        if (lastTiltKey.current === key) return
        lastTiltKey.current = key
        fetchOptimalTilt({ location, mode: tiltMode })
            .then(setTilt)
            .catch((err) => setError(err instanceof ApiError ? err.message : 'Could not compute optimal tilt.'))
    }, [location, tiltMode])

    useEffect(() => {
        const key = JSON.stringify({ location, array })
        if (lastLossKey.current === key) return
        lastLossKey.current = key
        fetchLossBreakdown({ location, array, horizon_hours: 24 })
            .then(setLosses)
            .catch((err) => setError(err instanceof ApiError ? err.message : 'Could not compute loss breakdown.'))
    }, [location, array])

    // Earnings is a small calculator, not a report — recompute live as the
    // user edits either input, no submit step needed.
    useEffect(() => {
        const handle = setTimeout(() => {
            fetchEarnings({ energy_kwh: energyKwh, price_per_kwh: pricePerKwh, grid_co2_kg_per_kwh: gridCo2KgPerKwh })
                .then(setEarnings)
                .catch((err) => setError(err instanceof ApiError ? err.message : 'Could not compute earnings.'))
        }, 300)
        return () => clearTimeout(handle)
    }, [energyKwh, pricePerKwh, gridCo2KgPerKwh])

    return (
        <div className="analytics-grid">
            {error && <div className="error-banner">{error}</div>}

            <div className="card">
                <h2>Optimal tilt</h2>
                <div className="field">
                    <label htmlFor="tilt-mode">Mode</label>
                    <select id="tilt-mode" value={tiltMode} onChange={(e) => setTiltMode(e.target.value as TiltMode)}>
                        <option value="current">Current</option>
                        <option value="daily">Daily</option>
                        <option value="annual">Annual</option>
                    </select>
                </div>
                {tilt ? (
                    <div className="stat-row">
                        <div className="stat">
                            <span className="value">{tilt.tilt_deg}°</span>
                            <span className="label">Tilt</span>
                        </div>
                        <div className="stat">
                            <span className="value">{tilt.azimuth_deg}°</span>
                            <span className="label">Azimuth</span>
                        </div>
                        <div className="stat" title={`Source: ${tilt.source}`}>
                            <span className="value">{tilt.poa_kwh_per_m2} kWh/m²</span>
                            <span className="label">Insolation</span>
                        </div>
                    </div>
                ) : (
                    <div className="empty-state">Loading…</div>
                )}
            </div>

            <div className="card">
                <h2>Loss breakdown</h2>
                {losses ? (
                    <>
                        <div className="loss-stack">
                            {Object.entries(losses.named_losses_pct).map(([key, pct], i) => (
                                <span
                                    key={key}
                                    className="loss-stack-segment"
                                    style={{ flexGrow: pct, opacity: 1 - i * 0.09 }}
                                    title={`${LOSS_LABELS[key] ?? key}: ${pct}%`}
                                />
                            ))}
                            <span
                                className="loss-stack-segment"
                                style={{ flexGrow: losses.temperature_loss_pct, opacity: 0.35 }}
                                title={`Temperature: ${losses.temperature_loss_pct}%`}
                            />
                        </div>
                        <ul className="loss-legend">
                            {Object.entries(losses.named_losses_pct).map(([key, pct]) => (
                                <li key={key}>
                                    {LOSS_LABELS[key] ?? key} <span>{pct}%</span>
                                </li>
                            ))}
                            <li>
                                Temperature <span>{losses.temperature_loss_pct}%</span>
                            </li>
                        </ul>
                        <p className="loss-total-line">Total: {losses.total_loss_pct}%</p>
                    </>
                ) : (
                    <div className="empty-state">Loading…</div>
                )}
            </div>

            <div className="card">
                <h2>Earnings & CO₂ avoided</h2>
                <div className="field-row">
                    <div className="field">
                        <label htmlFor="energy-kwh">Energy (kWh)</label>
                        <input
                            id="energy-kwh"
                            type="number"
                            min="0"
                            value={energyKwh}
                            onChange={(e) => setEnergyKwh(Number(e.target.value))}
                        />
                    </div>
                    <div className="field">
                        <label htmlFor="price-kwh">Price / kWh ({currencySymbol})</label>
                        <input
                            id="price-kwh"
                            type="number"
                            step="0.01"
                            min="0"
                            value={pricePerKwh}
                            onChange={(e) => setPricePerKwh(Number(e.target.value))}
                        />
                    </div>
                </div>
                {earnings && (
                    <div className="stat-row">
                        <div className="stat">
                            <span className="value">
                                {currencySymbol}
                                {earnings.earnings.toFixed(2)}
                            </span>
                            <span className="label">Earnings</span>
                        </div>
                        <div className="stat">
                            <span className="value">{earnings.co2_avoided_kg.toFixed(1)} kg</span>
                            <span className="label">CO₂ avoided</span>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
