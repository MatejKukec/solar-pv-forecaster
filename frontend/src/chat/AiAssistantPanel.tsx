import { useEffect, useState } from 'react'
import { ApiError, fetchChat, fetchProductionHistory } from '../api/client'
import type { Location } from '../types'

interface ChatMessage {
    role: 'user' | 'assistant'
    text: string
}

interface AiAssistantPanelProps {
    location: Location
    forecastContext: string
}

export function AiAssistantPanel({ location, forecastContext }: AiAssistantPanelProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [historyContext, setHistoryContext] = useState('')

    // Fetched once so the assistant can answer about any recently logged day
    // ("day before yesterday", a specific date, etc.), not just literally
    // "yesterday" — forecastContext alone only covers the forward-looking forecast.
    useEffect(() => {
        fetchProductionHistory(location)
            .then((history) => {
                if (history.entries.length === 0) {
                    setHistoryContext('No actual production has been logged for this site yet.')
                    return
                }
                const list = history.entries.map((e) => `${e.date}: ${e.actual_kwh.toFixed(1)}kWh`).join(', ')
                setHistoryContext(`Actual logged production, most recent first: ${list}.`)
            })
            .catch(() => setHistoryContext(''))
    }, [location])

    async function sendMessage(question: string) {
        if (!question.trim() || isLoading) return
        setMessages((curr) => [...curr, { role: 'user', text: question }])
        setInput('')
        setIsLoading(true)
        try {
            const context = [forecastContext, historyContext].filter(Boolean).join(' ')
            const result = await fetchChat(question, context)
            setMessages((curr) => [...curr, { role: 'assistant', text: result.reply }])
        } catch (err) {
            const text = err instanceof ApiError ? err.message : 'Something went wrong answering that.'
            setMessages((curr) => [...curr, { role: 'assistant', text }])
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="card ai-assistant-card">
            <h2>AI assistant</h2>

            {messages.length === 0 ? (
                <p className="chat-hint">
                    Ask about today's output, past production, or general solar PV questions.
                </p>
            ) : (
                <div className="chat-log">
                    {messages.map((message, i) => (
                        <div key={i} className={`chat-bubble chat-bubble-${message.role}`}>
                            {message.text}
                        </div>
                    ))}
                    {isLoading && <div className="chat-bubble chat-bubble-assistant chat-bubble-pending">…</div>}
                </div>
            )}

            <div className="chat-input-row">
                <input
                    type="text"
                    value={input}
                    placeholder="Ask a question…"
                    aria-label="Ask a question about your forecast"
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && sendMessage(input)}
                />
                <button className="btn-accent" onClick={() => sendMessage(input)} disabled={isLoading}>
                    Send
                </button>
            </div>
        </div>
    )
}
