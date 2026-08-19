import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useAccounts, useBudgets, useTransactions, useTaxCalculations } from '../hooks/useApi'
import { formatCurrency, formatDate, getGreeting, getStatusColor, getStatusLabel, cn } from '../utils/format'
import Card, { CardHeader, CardTitle } from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import ProgressBar from '../components/ui/ProgressBar'
import EmptyState from '../components/ui/EmptyState'
import { SkeletonCard } from '../components/ui/Skeleton'
import { useToast } from '../contexts/ToastContext'
import { apiClient } from '../api/client'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Wallet, TrendingUp, TrendingDown, Calculator, Plus, FileText, BotMessageSquare, ArrowRight } from 'lucide-react'
import type { Account, Budget, Transaction, TaxCalculation } from '../types/api'

const PIE_COLORS = ['#4F7CFF', '#8B5CF6', '#22D3EE', '#22C55E', '#F59E0B', '#EF4444', '#EC4899', '#14B8A6']

const PLACEHOLDER_SPENDING = [
  { month: 'Jan', income: 4200, expenses: 3100 },
  { month: 'Feb', income: 4200, expenses: 2850 },
  { month: 'Mar', income: 4500, expenses: 3400 },
  { month: 'Apr', income: 4200, expenses: 2950 },
  { month: 'May', income: 4800, expenses: 3600 },
  { month: 'Jun', income: 4200, expenses: 3200 },
]

function SpendingTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name: string; color: string }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl px-4 py-3 shadow-xl" style={{ border: '1px solid var(--border-default)', background: 'var(--bg-surface)' }}>
      <p className="mb-1 text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="text-sm font-semibold" style={{ color: entry.color }}>
          {entry.name === 'income' ? 'Income' : 'Expenses'}: {formatCurrency(entry.value)}
        </p>
      ))}
    </div>
  )
}

function CategoryTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number }> }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl px-4 py-3 shadow-xl" style={{ border: '1px solid var(--border-default)', background: 'var(--bg-surface)' }}>
      <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{payload[0].name}</p>
      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{formatCurrency(payload[0].value)}</p>
    </div>
  )
}

export function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data: accounts, loading: accountsLoading } = useAccounts()
  const { data: budgets, loading: budgetsLoading } = useBudgets()
  const { data: taxData, loading: taxLoading } = useTaxCalculations()

  const firstAccountId = accounts?.[0]?.id ?? null

  const { data: txnData, loading: txnLoading } = useTransactions(firstAccountId, { limit: 200 })

  const transactions = txnData?.transactions ?? []
  const loading = accountsLoading || txnLoading

  const now = new Date()
  const currentMonth = now.getMonth()
  const currentYear = now.getFullYear()

  const displayName = useMemo(() => {
    const raw = user?.name || user?.email || 'there'
    if (raw.includes('@')) {
      const prefix = raw.split('@')[0]
      return prefix.charAt(0).toUpperCase() + prefix.slice(1)
    }
    return raw.charAt(0).toUpperCase() + raw.slice(1)
  }, [user])

  const totalBalance = useMemo(
    () => (accounts ?? []).reduce((sum, a) => sum + (a.current_balance ?? 0), 0),
    [accounts],
  )

  const monthlyTxns = useMemo(
    () =>
      transactions.filter((t) => {
        const d = new Date(t.transaction_date)
        return d.getMonth() === currentMonth && d.getFullYear() === currentYear
      }),
    [transactions, currentMonth, currentYear],
  )

  const monthlyIncome = useMemo(
    () =>
      monthlyTxns
        .filter((t) => t.transaction_type === 'income')
        .reduce((sum, t) => sum + Math.abs(t.amount), 0),
    [monthlyTxns],
  )

  const monthlyExpenses = useMemo(
    () =>
      monthlyTxns
        .filter((t) => t.transaction_type === 'expense')
        .reduce((sum, t) => sum + Math.abs(t.amount), 0),
    [monthlyTxns],
  )

  const latestTaxEstimate = taxData?.[0]?.income_tax_due ?? null

  const spendingData = useMemo(() => {
    if (transactions.length === 0) return PLACEHOLDER_SPENDING

    const monthMap: Record<string, { income: number; expenses: number }> = {}
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for (const name of monthNames) {
      monthMap[name] = { income: 0, expenses: 0 }
    }
    for (const t of transactions) {
      const d = new Date(t.transaction_date)
      const key = monthNames[d.getMonth()]
      if (!key) continue
      if (t.transaction_type === 'income') {
        monthMap[key].income += Math.abs(t.amount)
      } else {
        monthMap[key].expenses += Math.abs(t.amount)
      }
    }
    return monthNames.map((m) => ({ month: m, ...monthMap[m] }))
  }, [transactions])

  const categoryData = useMemo(() => {
    const expenses = monthlyTxns.filter((t) => t.transaction_type === 'expense')
    if (expenses.length === 0) return []

    const map: Record<string, number> = {}
    for (const t of expenses) {
      const cat = t.category ?? 'Uncategorised'
      map[cat] = (map[cat] ?? 0) + Math.abs(t.amount)
    }
    return Object.entries(map)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [monthlyTxns])

  const hasPieData = categoryData.length > 0

  const recentTransactions = useMemo(
    () =>
      [...transactions]
        .sort((a, b) => new Date(b.transaction_date).getTime() - new Date(a.transaction_date).getTime())
        .slice(0, 5),
    [transactions],
  )

  const hasTransactions = transactions.length > 0

  const budgetItems = (budgets ?? []).slice(0, 4)

  const quickActions = [
    { icon: ArrowRight, title: 'Import Transactions', desc: 'Upload a CSV file to get started.', to: '/transactions' },
    { icon: Plus, title: 'Create Budget', desc: 'Set spending limits per category.', to: '/budgets' },
    { icon: Calculator, title: 'Tax Estimator', desc: 'UK income tax for 2026/27.', to: '/tax' },
    { icon: FileText, title: 'Generate Report', desc: 'Export your financial summary.', to: '/reports' },
  ]

  const categoryTotal = useMemo(() => categoryData.reduce((s, c) => s + c.value, 0), [categoryData])

  return (
    <div className="mx-auto max-w-[1440px] space-y-5 pb-12">

      {/* ── Greeting ──────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
          {getGreeting()}, {displayName} 👋
        </h1>
        <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
          Here's what's happening with your finances today.
        </p>
      </div>

      {/* ── Summary Cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            {/* Total Balance */}
            <Card>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                  Total Balance
                </span>
                <div className="flex h-9 w-9 items-center justify-center rounded-full" style={{ backgroundColor: 'color-mix(in srgb, #4F7CFF 12%, transparent)' }}>
                  <Wallet size={18} className="text-primary" />
                </div>
              </div>
              <p className="mt-2 text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                {formatCurrency(totalBalance)}
              </p>
              <p className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                Across {accounts?.length ?? 0} account{(accounts?.length ?? 0) !== 1 ? 's' : ''}
              </p>
            </Card>

            {/* Monthly Income */}
            <Card>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                  Monthly Income
                </span>
                <div className="flex h-9 w-9 items-center justify-center rounded-full" style={{ backgroundColor: 'color-mix(in srgb, #22C55E 12%, transparent)' }}>
                  <TrendingUp size={18} className="text-success" />
                </div>
              </div>
              <p className="mt-2 text-2xl font-bold text-success">
                {formatCurrency(monthlyIncome)}
              </p>
              <p className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                Current month
              </p>
            </Card>

            {/* Monthly Expenses */}
            <Card>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                  Monthly Expenses
                </span>
                <div className="flex h-9 w-9 items-center justify-center rounded-full" style={{ backgroundColor: 'color-mix(in srgb, #EF4444 12%, transparent)' }}>
                  <TrendingDown size={18} className="text-danger" />
                </div>
              </div>
              <p className="mt-2 text-2xl font-bold text-danger">
                {formatCurrency(monthlyExpenses)}
              </p>
              <p className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                Current month
              </p>
            </Card>

            {/* Tax Estimate */}
            <Card>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                  Tax Estimate
                </span>
                <div className="flex h-9 w-9 items-center justify-center rounded-full" style={{ backgroundColor: 'color-mix(in srgb, #8B5CF6 12%, transparent)' }}>
                  <Calculator size={18} className="text-accent-purple" />
                </div>
              </div>
              {taxLoading ? (
                <div className="skeleton mt-2 h-7 w-32 rounded" />
              ) : latestTaxEstimate !== null ? (
                <p className="mt-2 text-2xl font-bold text-accent-purple">
                  {formatCurrency(latestTaxEstimate)}
                </p>
              ) : (
                <p className="mt-2 text-lg font-semibold" style={{ color: 'var(--text-tertiary)' }}>—</p>
              )}
              <p className="mt-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
                {latestTaxEstimate !== null ? '2026/27 estimate' : 'Run a tax estimate'}
              </p>
            </Card>
          </>
        )}
      </div>

      {/* ── Analytics Row ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">

        {/* Spending Overview */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Spending Overview</CardTitle>
          </CardHeader>

          {loading ? (
            <div className="skeleton h-60 w-full rounded-lg" />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={spendingData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradIncome" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22C55E" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22C55E" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradExpenses" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#EF4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, #1E2A45)" vertical={false} />
                <XAxis
                  dataKey="month"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: 'var(--text-tertiary)', fontSize: 12 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: 'var(--text-tertiary)', fontSize: 12 }}
                  tickFormatter={(v: number) => `£${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<SpendingTooltip />} />
                <Area
                  type="monotone"
                  dataKey="income"
                  stroke="#22C55E"
                  strokeWidth={2}
                  fill="url(#gradIncome)"
                />
                <Area
                  type="monotone"
                  dataKey="expenses"
                  stroke="#EF4444"
                  strokeWidth={2}
                  fill="url(#gradExpenses)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Category Breakdown */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Category Breakdown</CardTitle>
          </CardHeader>

          {loading ? (
            <div className="skeleton h-60 w-full rounded-lg" />
          ) : !hasPieData ? (
            <EmptyState
              icon={TrendingDown}
              title="No spending data yet"
              description="Import transactions to see your spending breakdown."
            />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {categoryData.map((entry, i) => (
                      <Cell key={entry.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CategoryTooltip />} />
                </PieChart>
              </ResponsiveContainer>

              <div className="mt-3 space-y-2">
                {categoryData.map((entry, i) => {
                  const pct = categoryTotal > 0 ? (entry.value / categoryTotal) * 100 : 0
                  return (
                    <div key={entry.name} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                        />
                        <span style={{ color: 'var(--text-secondary)' }}>{entry.name}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                          {formatCurrency(entry.value)}
                        </span>
                        <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          {pct.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </Card>
      </div>

      {/* ── Budget + Transactions Row ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">

        {/* Budget Health */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle>Budget Health</CardTitle>
            </div>
            {budgetItems.length > 0 && (
              <button
                onClick={() => navigate('/budgets')}
                className="text-xs font-medium text-primary transition hover:opacity-80"
              >
                View All
              </button>
            )}
          </CardHeader>

          {budgetsLoading ? (
            <div className="space-y-4">
              <div className="skeleton h-14 w-full rounded" />
              <div className="skeleton h-14 w-full rounded" />
              <div className="skeleton h-14 w-full rounded" />
            </div>
          ) : budgetItems.length === 0 ? (
            <EmptyState
              icon={Wallet}
              title="Create your first budget"
              description="Set spending limits to track your finances."
              action={
                <button
                  onClick={() => navigate('/budgets')}
                  className="inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-medium text-primary transition"
                  style={{ backgroundColor: 'color-mix(in srgb, var(--text-primary) 10%, transparent)' }}
                >
                  <Plus size={14} />
                  Create Budget
                </button>
              }
            />
          ) : (
            <div className="space-y-4">
              {budgetItems.map((b) => {
                const pct = Math.min(b.percentage_used, 100)
                const barColor: 'green' | 'amber' | 'red' =
                  b.status === 'over_budget' ? 'red' : b.status === 'near_limit' ? 'amber' : 'green'

                return (
                  <div key={b.id}>
                    <div className="mb-1.5 flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                          {b.category_name}
                        </span>
                        <Badge
                          variant={
                            b.status === 'over_budget'
                              ? 'red'
                              : b.status === 'near_limit'
                                ? 'amber'
                                : 'green'
                          }
                        >
                          {getStatusLabel(b.status)}
                        </Badge>
                      </div>
                      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        {formatCurrency(b.actual_spending)} / {formatCurrency(b.budget_amount)}
                      </span>
                    </div>
                    <ProgressBar value={pct} color={barColor} />
                  </div>
                )
              })}
            </div>
          )}
        </Card>

        {/* Recent Transactions */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle>Recent Transactions</CardTitle>
            </div>
            {hasTransactions && (
              <button
                onClick={() => navigate('/transactions')}
                className="text-xs font-medium text-primary transition hover:opacity-80"
              >
                View All
              </button>
            )}
          </CardHeader>

          {txnLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="skeleton h-10 w-full rounded" />
              ))}
            </div>
          ) : !hasTransactions ? (
            <EmptyState
              icon={FileText}
              title="No transactions yet"
              description="Import a CSV file to get started."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs" style={{ color: 'var(--text-tertiary)', borderBottom: '1px solid var(--border-default)' }}>
                    <th className="pb-3 pr-4 font-medium">Date</th>
                    <th className="pb-3 pr-4 font-medium">Description</th>
                    <th className="pb-3 text-right font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTransactions.map((t) => {
                    const isIncome = t.transaction_type === 'income'
                    return (
                      <tr
                        key={t.id}
                        className="transition"
                        style={{ borderBottom: '1px solid color-mix(in srgb, var(--border-default) 50%, transparent)' }}
                      >
                        <td className="py-3 pr-4" style={{ color: 'var(--text-secondary)' }}>
                          {formatDate(t.transaction_date)}
                        </td>
                        <td className="py-3 pr-4 font-medium" style={{ color: 'var(--text-primary)' }}>
                          {t.description}
                        </td>
                        <td className={cn('py-3 text-right font-semibold', isIncome ? 'text-success' : 'text-danger')}>
                          {isIncome ? '+' : '−'}{formatCurrency(Math.abs(t.amount))}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      {/* ── Quick Actions ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {quickActions.map((action) => (
          <Card key={action.to} hover className="cursor-pointer" onClick={() => navigate(action.to)}>
            <div className="flex items-center gap-3">
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                style={{ backgroundColor: 'color-mix(in srgb, var(--text-primary) 8%, transparent)' }}
              >
                <action.icon size={18} style={{ color: 'var(--text-primary)' }} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold transition" style={{ color: 'var(--text-primary)' }}>
                  {action.title}
                </p>
                <p className="mt-0.5 text-xs truncate" style={{ color: 'var(--text-tertiary)' }}>
                  {action.desc}
                </p>
              </div>
              <ArrowRight size={14} className="ml-auto shrink-0" style={{ color: 'var(--text-tertiary)' }} />
            </div>
          </Card>
        ))}
      </div>

      {/* ── AI Assistant Card ─────────────────────────────────────────────── */}
      <div
        className="flex items-center justify-between rounded-xl border p-5"
        style={{
          borderColor: 'color-mix(in srgb, #8B5CF6 30%, transparent)',
          background: 'var(--bg-surface)',
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div className="flex items-center gap-4">
          <div
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl"
            style={{ backgroundColor: 'color-mix(in srgb, #8B5CF6 15%, transparent)' }}
          >
            <BotMessageSquare size={24} className="text-accent-purple" />
          </div>
          <div>
            <h2 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
              AI Financial Assistant
            </h2>
            <p className="mt-0.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
              Ask me anything about your finances — spending patterns, budget tips, tax guidance, and more.
            </p>
          </div>
        </div>

        <button
          onClick={() => navigate('/assistant')}
          className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#6366F1] px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-[#8B5CF6]/20 transition hover:shadow-[#8B5CF6]/40"
        >
          <BotMessageSquare size={16} />
          Chat with AI
        </button>
      </div>
    </div>
  )
}
