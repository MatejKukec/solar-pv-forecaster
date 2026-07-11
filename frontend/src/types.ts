export interface Location {
  latitude: number
  longitude: number
  elevation_m?: number
  timezone?: string
}

export interface PVArrayInput {
  capacity_kw: number
  tilt_deg: number
  azimuth_deg: number
  system_loss_pct?: number
}

export interface ForecastRequest {
  location: Location
  arrays: PVArrayInput[]
  horizon_hours: number
}

export interface HourlyPowerPoint {
  timestamp: string
  ac_power_kw: number
  ghi_w_m2: number | null
  cloud_cover_pct: number | null
  uncertainty_kw: number | null
}

export interface ForecastResponse {
  location: Location
  generated_at: string
  hourly: HourlyPowerPoint[]
  total_capacity_kw: number
  mae_pct: number
  is_calibrated: boolean
}

export interface ApiErrorBody {
  error: { code: string; message: string }
}

export interface PastDateRequest {
  location: Location
  arrays: PVArrayInput[]
  date: string
}

export interface PastDateResponse {
  date: string
  location: Location
  hourly: HourlyPowerPoint[]
  modeled_kwh: number
  calibrated_kwh: number
  actual_kwh: number | null
  bias_factor: number
  is_calibrated: boolean
  mae_kwh: number
  mae_pct: number
}

export interface ProductionLogRequest {
  location: Location
  date: string
  actual_kwh: number
}

export interface ProductionLogResponse {
  site_id: string
  date: string
  actual_kwh: number
  n_days_logged: number
  is_calibrated: boolean
}

export interface ProductionHistoryEntry {
  date: string
  actual_kwh: number
}

export interface ProductionHistoryResponse {
  site_id: string
  entries: ProductionHistoryEntry[]
  n_days_logged: number
  is_calibrated: boolean
}

export type TiltMode = 'current' | 'daily' | 'annual'

export interface TiltRequest {
  location: Location
  mode: TiltMode
  target_date?: string
}

export interface TiltResponse {
  tilt_deg: number
  azimuth_deg: number
  poa_kwh_per_m2: number
  source: string
}

export interface LossRequest {
  location: Location
  array: PVArrayInput
  horizon_hours: number
}

export interface LossResponse {
  named_losses_pct: Record<string, number>
  temperature_loss_pct: number
  total_loss_pct: number
}

export interface EarningsRequest {
  energy_kwh: number
  price_per_kwh: number
  grid_co2_kg_per_kwh?: number
}

export interface EarningsResponse {
  energy_kwh: number
  earnings: number
  co2_avoided_kg: number
}
