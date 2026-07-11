import { useState } from 'react'
import type { AppSettings } from '../settings'

interface SettingsPageProps {
  value: AppSettings
  onSave: (settings: AppSettings) => void
  onClose: () => void
}

export function SettingsPage({ value, onSave, onClose }: SettingsPageProps) {
  const [draft, setDraft] = useState<AppSettings>(value)

  function updateLocation(field: keyof AppSettings['location'], val: number) {
    setDraft((curr) => ({ ...curr, location: { ...curr.location, [field]: val } }))
  }

  function updateArray(field: keyof AppSettings['array'], val: number) {
    setDraft((curr) => ({ ...curr, array: { ...curr.array, [field]: val } }))
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    onSave(draft)
  }

  return (
    <form className="card settings-page" onSubmit={handleSubmit}>
      <div className="panel-header">
        <h2>Settings</h2>
        <button type="button" className="btn-link" onClick={onClose}>
          ← Back
        </button>
      </div>

      <h3>Site & array</h3>
      <div className="field-row">
        <div className="field">
          <label htmlFor="latitude">Latitude</label>
          <input
            id="latitude"
            type="number"
            step="0.0001"
            value={draft.location.latitude}
            onChange={(e) => updateLocation('latitude', Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="longitude">Longitude</label>
          <input
            id="longitude"
            type="number"
            step="0.0001"
            value={draft.location.longitude}
            onChange={(e) => updateLocation('longitude', Number(e.target.value))}
          />
        </div>
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="capacity">Capacity (kW)</label>
          <input
            id="capacity"
            type="number"
            step="0.1"
            min="0.1"
            value={draft.array.capacity_kw}
            onChange={(e) => updateArray('capacity_kw', Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="tilt">Tilt (°)</label>
          <input
            id="tilt"
            type="number"
            min="0"
            max="90"
            value={draft.array.tilt_deg}
            onChange={(e) => updateArray('tilt_deg', Number(e.target.value))}
          />
        </div>
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="azimuth">Azimuth (° — 180 = south)</label>
          <input
            id="azimuth"
            type="number"
            min="0"
            max="360"
            value={draft.array.azimuth_deg}
            onChange={(e) => updateArray('azimuth_deg', Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="loss">System loss (%)</label>
          <input
            id="loss"
            type="number"
            min="0"
            max="50"
            step="0.5"
            value={draft.array.system_loss_pct ?? 14}
            onChange={(e) => updateArray('system_loss_pct', Number(e.target.value))}
          />
        </div>
      </div>

      <h3>Forecast</h3>
      <div className="field">
        <label htmlFor="horizon">Horizon (hours)</label>
        <input
          id="horizon"
          type="number"
          min="1"
          max="360"
          value={draft.horizon_hours}
          onChange={(e) => setDraft((curr) => ({ ...curr, horizon_hours: Number(e.target.value) }))}
        />
      </div>

      <h3>Earnings & CO₂</h3>
      <div className="field-row">
        <div className="field">
          <label htmlFor="price">Default price / kWh</label>
          <input
            id="price"
            type="number"
            step="0.01"
            min="0"
            value={draft.price_per_kwh}
            onChange={(e) => setDraft((curr) => ({ ...curr, price_per_kwh: Number(e.target.value) }))}
          />
        </div>
        <div className="field">
          <label htmlFor="co2">Grid CO₂ (kg/kWh)</label>
          <input
            id="co2"
            type="number"
            step="0.01"
            min="0"
            value={draft.grid_co2_kg_per_kwh}
            onChange={(e) => setDraft((curr) => ({ ...curr, grid_co2_kg_per_kwh: Number(e.target.value) }))}
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="currency">Currency symbol</label>
        <input
          id="currency"
          type="text"
          maxLength={3}
          value={draft.currency_symbol}
          onChange={(e) => setDraft((curr) => ({ ...curr, currency_symbol: e.target.value }))}
        />
      </div>

      <button className="btn-accent" type="submit">
        Save & apply
      </button>
    </form>
  )
}
