import { DEFAULT_ARRAY, DEFAULT_LOCATION } from './constants'
import type { Location, PVArrayInput } from './types'

export interface AppSettings {
  location: Location
  array: PVArrayInput
  horizon_hours: number
  price_per_kwh: number
  grid_co2_kg_per_kwh: number
  currency_symbol: string
}

const STORAGE_KEY = 'solar-pv-forecaster:settings'

export const DEFAULT_SETTINGS: AppSettings = {
  location: DEFAULT_LOCATION,
  array: DEFAULT_ARRAY,
  horizon_hours: 48,
  price_per_kwh: 0.15,
  grid_co2_kg_per_kwh: 0.4,
  currency_symbol: '$',
}

export function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_SETTINGS
    return { ...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<AppSettings>) }
  } catch {
    return DEFAULT_SETTINGS
  }
}

export function saveSettings(settings: AppSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch {
    // Non-critical — settings just won't persist across reloads.
  }
}
