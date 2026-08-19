import { useState, useRef, useEffect } from 'react'
import { BotMessageSquare, User, Sparkles, Loader2, Send, TrendingUp, TrendingDown, Wallet, Calculator } from 'lucide-react'
import { apiClient } from '../api/client'
import { useAccounts, useBudgets } from '../hooks/useApi'
import { formatCurrency, cn } from '../utils/format'
import Card from '../components/ui/Card'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const SUGGESTED_PROMPTS = [
  'Where did I spend the most this month?',
  'Am I on track with my budgets?',
  'How much tax might I owe?',
  'Summarize my finances',
]

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: accounts } = useAccounts()
  const { data: budgets } = useBudgets()

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const totalBalance = accounts?.reduce((sum, a) => sum + (a.current_balance ?? 0), 0) ?? 0

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await apiClient.chatWithAssistant(text.trim())
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch {
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      {/* Main Chat Column */}
      <div className="flex min-h-0 flex-1 flex-col">
        {/* Header */}
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-purple/15">
            <BotMessageSquare size={20} className="text-accent-purple" />
          </div>
          <div>
            <h1 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>AI Financial Assistant</h1>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Your personal finance copilot</p>
          </div>
        </div>

        {/* Chat Container */}
        <div className="flex min-h-0 flex-1 flex-col rounded-2xl border" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface)', boxShadow: 'var(--shadow-card)' }}>
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center">
                <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-purple/10">
                  <Sparkles size={32} className="text-accent-purple" />
                </div>
                <h2 className="mb-2 text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>How can I help you?</h2>
                <p className="mb-8 text-sm" style={{ color: 'var(--text-secondary)' }}>Ask me anything about your finances</p>

                <div className="grid w-full max-w-2xl gap-3 sm:grid-cols-2">
                  {SUGGESTED_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => sendMessage(prompt)}
                      className="group rounded-xl border p-4 text-left text-sm transition-all duration-200 hover:border-accent-purple/30 hover:bg-[var(--bg-surface-hover)]"
                      style={{ borderColor: 'var(--border-default)', color: 'var(--text-secondary)' }}
                    >
                      <div className="flex items-start gap-3">
                        <Sparkles size={14} className="mt-0.5 shrink-0 text-accent-purple/60 transition-colors group-hover:text-accent-purple" />
                        <span className="group-hover:text-[var(--text-primary)]">{prompt}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      'flex',
                      message.role === 'user' ? 'justify-end' : 'justify-start',
                    )}
                  >
                    <div
                      className={cn(
                        'flex max-w-[80%] items-start gap-3 rounded-2xl px-4 py-3',
                        message.role === 'user'
                          ? 'bg-primary text-white'
                          : 'border text-[var(--text-primary)]',
                      )}
                      style={message.role === 'assistant' ? { backgroundColor: 'var(--bg-surface-secondary)', borderColor: 'var(--border-default)' } : undefined}
                    >
                      {message.role === 'assistant' && (
                        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-purple/20">
                          <BotMessageSquare size={14} className="text-accent-purple" />
                        </div>
                      )}
                      <div className="min-w-0">
                        <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
                        <p className="mt-1.5 text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                          {message.timestamp.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                      {message.role === 'user' && (
                        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10">
                          <User size={14} className="text-white" />
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="flex items-start gap-3 rounded-2xl border px-4 py-3" style={{ backgroundColor: 'var(--bg-surface-secondary)', borderColor: 'var(--border-default)' }}>
                      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-purple/20">
                        <BotMessageSquare size={14} className="text-accent-purple" />
                      </div>
                      <div className="flex items-center gap-2">
                        <Loader2 size={16} className="animate-spin text-accent-purple" />
                        <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>Thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Input Bar */}
          <div className="border-t px-4 py-4 sm:px-6" style={{ borderColor: 'var(--border-default)' }}>
            <form onSubmit={handleSubmit} className="flex items-center gap-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me about your finances..."
                disabled={loading}
                className="flex-1 rounded-xl border px-4 py-3 text-sm outline-none transition-colors disabled:opacity-50"
                style={{
                  borderColor: 'var(--border-default)',
                  backgroundColor: 'var(--bg-input)',
                  color: 'var(--text-primary)',
                }}
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="flex h-11 w-11 items-center justify-center rounded-xl text-white shadow-lg transition-all disabled:cursor-not-allowed disabled:opacity-50"
                style={{ background: 'linear-gradient(to right, var(--color-primary, #6366f1), var(--color-accent-purple, #a855f7))' }}
              >
                {loading ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Context Panel */}
      <div className="hidden w-72 shrink-0 flex-col gap-4 lg:flex">
        <Card>
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Financial Summary</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3 rounded-lg p-3" style={{ backgroundColor: 'var(--bg-surface-secondary)' }}>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                <Wallet size={18} className="text-primary" />
              </div>
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Total Balance</p>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{formatCurrency(totalBalance)}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-lg p-3" style={{ backgroundColor: 'var(--bg-surface-secondary)' }}>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-success/10">
                <TrendingUp size={18} className="text-success" />
              </div>
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Accounts</p>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{accounts?.length ?? 0}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-lg p-3" style={{ backgroundColor: 'var(--bg-surface-secondary)' }}>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-warning/10">
                <Calculator size={18} className="text-warning" />
              </div>
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Budgets</p>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{budgets?.length ?? 0}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-lg p-3" style={{ backgroundColor: 'var(--bg-surface-secondary)' }}>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-purple/10">
                <TrendingDown size={18} className="text-accent-purple" />
              </div>
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Active Budgets</p>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {budgets?.filter(b => b.status !== 'over_budget').length ?? 0}
                </p>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="mb-3 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Quick Actions</h3>
          <div className="space-y-2">
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => sendMessage(prompt)}
                className="w-full rounded-lg p-2.5 text-left text-xs transition-colors hover:bg-[var(--bg-surface-hover)]"
                style={{ color: 'var(--text-secondary)' }}
              >
                {prompt}
              </button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
