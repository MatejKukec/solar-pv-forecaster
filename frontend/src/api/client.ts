import type {
    ApiErrorBody,
    EarningsRequest,
    EarningsResponse,
    ForecastRequest,
    ForecastResponse,
    Location,
    LossRequest,
    LossResponse,
    PastDateRequest,
    PastDateResponse,
    ProductionHistoryResponse,
    ProductionLogRequest,
    ProductionLogResponse,
    TiltRequest,
    TiltResponse,
} from '../types'

// In dev, relative paths go through the Vite proxy (vite.config.ts) to
// localhost:8000. In production, frontend and backend are deployed
// separately (see DEPLOYMENT.md), so set VITE_API_BASE_URL at build time to
// the backend's public URL.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

class ApiError extends Error {
    constructor(
        message: string,
        public status: number,
    ) {
        super(message)
    }
}

async function getJson<TResponse>(path: string, params?: Record<string, string | number>): Promise<TResponse> {
    const query = params ? `?${new URLSearchParams(params as Record<string, string>).toString()}` : ''
    const response = await fetch(`${API_BASE}${path}${query}`)

    if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as ApiErrorBody | null
        throw new ApiError(errorBody?.error?.message ?? `request to ${path} failed`, response.status)
    }

    return (await response.json()) as TResponse
}

async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
    const response = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })

    if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as ApiErrorBody | null
        throw new ApiError(errorBody?.error?.message ?? `request to ${path} failed`, response.status)
    }

    return (await response.json()) as TResponse
}

export function fetchForecast(request: ForecastRequest): Promise<ForecastResponse> {
    return postJson<ForecastResponse>('/api/forecast', request)
}

export function fetchChat(message: string, forecastContext: string): Promise<{ reply: string }> {
    return postJson('/api/ai/chat', { message, forecast_context: forecastContext })
}

export function fetchAnomaly(actualKw: number, expectedKw: number, context: string): Promise<{ message: string | null }> {
    return postJson('/api/ai/anomaly', { actual_kw: actualKw, expected_kw: expectedKw, context })
}

export function fetchPastDate(request: PastDateRequest): Promise<PastDateResponse> {
    return postJson<PastDateResponse>('/api/past', request)
}

export function logProduction(request: ProductionLogRequest): Promise<ProductionLogResponse> {
    return postJson<ProductionLogResponse>('/api/calibration/production', request)
}

export function fetchOptimalTilt(request: TiltRequest): Promise<TiltResponse> {
    return postJson<TiltResponse>('/api/analytics/tilt', request)
}

export function fetchLossBreakdown(request: LossRequest): Promise<LossResponse> {
    return postJson<LossResponse>('/api/analytics/losses', request)
}

export function fetchEarnings(request: EarningsRequest): Promise<EarningsResponse> {
    return postJson<EarningsResponse>('/api/analytics/earnings', request)
}

export interface HealthResponse {
    status: string
    ai_provider: 'mock' | 'gemini'
}

export function fetchHealth(): Promise<HealthResponse> {
    return getJson<HealthResponse>('/health')
}

export function fetchProductionHistory(location: Location): Promise<ProductionHistoryResponse> {
    return getJson<ProductionHistoryResponse>('/api/calibration/history', {
        latitude: location.latitude,
        longitude: location.longitude,
    })
}

export { ApiError }