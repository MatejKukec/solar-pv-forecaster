export type ServiceStatus = 'checking' | 'ok' | 'degraded' | 'down'

interface StatusDotProps {
  label: string
  status: ServiceStatus
}

const STATUS_TEXT: Record<ServiceStatus, string> = {
  checking: 'Checking…',
  ok: 'OK',
  degraded: 'Degraded',
  down: 'Down',
}

function StatusDot({ label, status }: StatusDotProps) {
  return (
    <span className="status-dot-group" title={`${label}: ${STATUS_TEXT[status]}`}>
      <span className={`status-dot status-dot-${status}`} />
      {label}
    </span>
  )
}

interface StatusBarProps {
  backendStatus: ServiceStatus
  weatherStatus: ServiceStatus
  aiProvider: 'mock' | 'gemini' | null
}

export function StatusBar({ backendStatus, weatherStatus, aiProvider }: StatusBarProps) {
  return (
    <div className="status-bar">
      <StatusDot label="Backend" status={backendStatus} />
      <StatusDot label="Weather" status={weatherStatus} />
      <span className="status-dot-group" title="Which AI backend is answering summary/chat/anomaly requests">
        <span className={`status-dot ${aiProvider === 'gemini' ? 'status-dot-ok' : 'status-dot-neutral'}`} />
        AI: {aiProvider === 'gemini' ? 'Gemini' : aiProvider === 'mock' ? 'Mock' : '…'}
      </span>
    </div>
  )
}
