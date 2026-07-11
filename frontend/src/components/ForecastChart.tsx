import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { HourlyPowerPoint } from '../types'

interface ForecastChartProps {
    hourly: HourlyPowerPoint[]
}

interface ChartPoint {
    time: string
    kw: number
    uncertaintyKw: number | null
    bandLow: number
    bandRange: number
}

interface TooltipPayloadEntry {
    payload: ChartPoint
}

interface ChartTooltipProps {
    active?: boolean
    label?: string
    payload?: TooltipPayloadEntry[]
}

function ChartTooltip({ active, label, payload }: ChartTooltipProps) {
    if (!active || !payload || payload.length === 0) return null
    const point = payload[0].payload

    return (
        <div className="chart-tooltip">
            <div className="chart-tooltip-label">{label}</div>
            <div className="chart-tooltip-value">
                {point.kw.toFixed(2)} kW
                {point.uncertaintyKw !== null && ` (±${point.uncertaintyKw.toFixed(2)} kW)`}
            </div>
        </div>
    )
}

const WEEKDAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function formatTick(timestamp: string): string {
    const d = new Date(timestamp)
    const weekday = WEEKDAY_NAMES[d.getDay()]
    const hour = d.getHours().toString().padStart(2, '0')
    return `${weekday} ${hour}:00`
}

export function ForecastChart({ hourly }: ForecastChartProps) {
    const data: ChartPoint[] = hourly.map((point) => {
        const uncertainty = point.uncertainty_kw ?? 0
        const bandLow = Math.max(0, point.ac_power_kw - uncertainty)
        return {
            time: formatTick(point.timestamp),
            kw: point.ac_power_kw,
            uncertaintyKw: point.uncertainty_kw,
            bandLow,
            bandRange: point.ac_power_kw + uncertainty - bandLow,
        }
    })
    const hasUncertainty = hourly.some((point) => point.uncertainty_kw !== null)
    // Cap the x-axis to ~8 labels regardless of horizon length — at 48+ points,
    // printing every tick makes them collide and become unreadable.
    const tickInterval = Math.max(0, Math.ceil(data.length / 8) - 1)

    return (
        <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={data}>
                <defs>
                    <linearGradient id="powerFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#4ac3ff" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#4ac3ff" stopOpacity={0} />
                    </linearGradient>
                </defs>
                <CartesianGrid stroke="#2a2d34" vertical={false} />
                <XAxis dataKey="time" stroke="#a6a9b1" fontSize={12} tickLine={false} interval={tickInterval} />
                <YAxis stroke="#a6a9b1" fontSize={12} tickLine={false} axisLine={false} unit="kW" />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#2a2d34' }} />
                {hasUncertainty && (
                    <>
                        <Area dataKey="bandLow" stackId="band" stroke="none" fill="transparent" isAnimationActive={false} />
                        <Area
                            dataKey="bandRange"
                            stackId="band"
                            stroke="none"
                            fill="#4ac3ff"
                            fillOpacity={0.12}
                            isAnimationActive={false}
                        />
                    </>
                )}
                <Area type="monotone" dataKey="kw" stroke="#4ac3ff" strokeWidth={2} fill="url(#powerFill)" />
            </AreaChart>
        </ResponsiveContainer>
    )
}
