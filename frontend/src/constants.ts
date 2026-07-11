import type { Location, PVArrayInput } from './types'

export const DEFAULT_LOCATION: Location = { latitude: 45.815, longitude: 15.9819, elevation_m: 158, timezone: 'Europe/Zagreb' }

export const DEFAULT_ARRAY: PVArrayInput = { capacity_kw: 5, tilt_deg: 30, azimuth_deg: 180, system_loss_pct: 14 }
