import { useState } from 'react'
import { apiClient } from '../api/client'
import { useTaxCalculations } from '../hooks/useApi'
import { formatCurrency, formatPercent, cn } from '../utils/format'
import type { TaxCalculation, TaxBandBreakdown } from '../types/api'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import EmptyState from '../components/ui/EmptyState'
import { useToast } from '../contexts/ToastContext'
import { Calculator, TrendingUp, History, Info } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

function StatCard({
  label,
  value,
  sub,
  color,
}: {
  label: string
  value: string
  sub?: string
  color?: string
}) {
  return (
    <Card>
      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</p>
      <p className={cn('mt-1 text-xl font-bold', color)} style={color ? undefined : { color: 'var(--text-primary)' }}>{value}</p>
      {sub && <p className="mt-0.5 text-xs" style={{ color: 'var(--text-tertiary)' }}>{sub}</p>}
    </Card>
  )
}

const BAND_COLORS: Record<string, string> = {
  'Basic Rate': '#4F7CFF',
  'Higher Rate': '#8B5CF6',
  'Additional Rate': '#EF4444',
}

function CustomBarTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ value: number; payload: TaxBandBreakdown }>
}) {
  if (!active || !payload || payload.length === 0) return null
  const band = payload[0].payload
  return (
    <div
      className="rounded-lg border px-3 py-2 shadow-xl"
      style={{
        borderColor: 'var(--border-default)',
        backgroundColor: 'var(--bg-modal)',
      }}
    >
      <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{band.band_name}</p>
      <p className="mt-0.5 text-xs" style={{ color: 'var(--text-secondary)' }}>
        Rate: {band.rate}% &middot; Tax: {formatCurrency(band.tax_due)}
      </p>
    </div>
  )
}

function ResultSection({ result }: { result: TaxCalculation }) {
  const chartData = result.band_breakdown.filter((b) => b.taxable_amount > 0)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Gross Income" value={formatCurrency(result.total_income)} />
        <StatCard
          label="Personal Allowance"
          value={formatCurrency(result.total_allowances)}
          color="text-success"
        />
        <StatCard label="Taxable Income" value={formatCurrency(result.taxable_income)} />
        <StatCard
          label="Total Tax"
          value={formatCurrency(result.income_tax_due)}
          color="text-danger"
        />
        <StatCard
          label="Effective Rate"
          value={formatPercent(result.effective_tax_rate)}
        />
        <StatCard
          label="Marginal Rate"
          value={formatPercent(result.marginal_tax_rate)}
        />
      </div>

      {chartData.length > 0 && (
        <Card>
          <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Tax Band Breakdown</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
              <XAxis
                dataKey="band_name"
                tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                axisLine={{ stroke: 'var(--border-default)' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                axisLine={{ stroke: 'var(--border-default)' }}
                tickLine={false}
                tickFormatter={(v: number) => `£${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip content={<CustomBarTooltip />} cursor={{ fill: 'var(--bg-surface-hover)' }} />
              <Bar dataKey="tax_due" radius={[6, 6, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.band_name} fill={BAND_COLORS[entry.band_name] ?? '#4F7CFF'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      <Card>
        <h3 className="mb-4 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Band Details</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b" style={{ borderColor: 'var(--border-default)' }}>
                <th className="pb-3 pr-4 font-medium" style={{ color: 'var(--text-secondary)' }}>Band</th>
                <th className="pb-3 pr-4 font-medium" style={{ color: 'var(--text-secondary)' }}>Rate</th>
                <th className="pb-3 pr-4 font-medium" style={{ color: 'var(--text-secondary)' }}>Taxable Amount</th>
                <th className="pb-3 font-medium" style={{ color: 'var(--text-secondary)' }}>Tax Due</th>
              </tr>
            </thead>
            <tbody>
              {result.band_breakdown.map((band) => (
                <tr
                  key={band.band_name}
                  className="border-b last:border-0"
                  style={{ borderColor: 'var(--border-default)' }}
                >
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{
                          backgroundColor: BAND_COLORS[band.band_name] ?? '#4F7CFF',
                        }}
                      />
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{band.band_name}</span>
                    </div>
                  </td>
                  <td className="py-3 pr-4" style={{ color: 'var(--text-primary)' }}>{band.rate}%</td>
                  <td className="py-3 pr-4" style={{ color: 'var(--text-primary)' }}>
                    {formatCurrency(band.taxable_amount)}
                  </td>
                  <td className="py-3 font-medium" style={{ color: 'var(--text-primary)' }}>
                    {formatCurrency(band.tax_due)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="flex items-start gap-3 rounded-xl border border-accent-cyan/20 bg-accent-cyan/5 p-4">
        <Info size={18} className="mt-0.5 shrink-0 text-accent-cyan" />
        <div className="text-sm">
          <p className="font-medium text-accent-cyan">Disclaimer</p>
          <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
            Estimation only — this is not official HMRC tax advice. Based on GOV.UK rates for
            2026/27. Results may differ from your actual tax liability.
          </p>
        </div>
      </div>

      {result.assumptions && (
        <Card>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
            Assumptions
          </h4>
          <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{result.assumptions}</p>
        </Card>
      )}

      {result.limitations && (
        <Card>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
            Limitations
          </h4>
          <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{result.limitations}</p>
        </Card>
      )}
    </div>
  )
}

export function TaxPage() {
  const { data: history, loading: historyLoading, refetch: refetchHistory } = useTaxCalculations()
  const { toast } = useToast()

  const [annualIncome, setAnnualIncome] = useState('')
  const [customAllowance, setCustomAllowance] = useState('')
  const [calculating, setCalculating] = useState(false)
  const [calcError, setCalcError] = useState('')
  const [result, setResult] = useState<TaxCalculation | null>(null)

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCalcError('')

    const income = parseFloat(annualIncome)
    if (isNaN(income) || income < 0) {
      setCalcError('Please enter a valid annual income')
      return
    }

    setCalculating(true)
    try {
      const allowance = customAllowance ? parseFloat(customAllowance) : undefined
      if (customAllowance && (isNaN(allowance!) || allowance! < 0)) {
        setCalcError('Custom allowance must be a valid number')
        setCalculating(false)
        return
      }
      const calc = await apiClient.estimateTax(income, allowance)
      setResult(calc)
      toast('success', 'Tax calculation complete')
      refetchHistory()
    } catch (err) {
      setCalcError(err instanceof Error ? err.message : 'Failed to calculate tax')
      toast('error', err instanceof Error ? err.message : 'Failed to calculate tax')
    } finally {
      setCalculating(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Tax Estimator</h2>
            <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
              England Income Tax &bull; 2026/27
            </p>
          </div>
        </div>
      </div>

      <Card>
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Calculator size={20} className="text-primary" />
          </div>
          <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Tax Calculator</h3>
        </div>

        {calcError && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger">
            <span>{calcError}</span>
          </div>
        )}

        <form onSubmit={handleCalculate} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Input
              label="Annual Income (£)"
              type="number"
              step="0.01"
              min="0"
              value={annualIncome}
              onChange={(e) => setAnnualIncome(e.target.value)}
              placeholder="e.g. 45000"
            />
            <Input
              label={<>Custom Personal Allowance <span style={{ color: 'var(--text-tertiary)' }}>(optional)</span></>}
              type="number"
              step="0.01"
              min="0"
              value={customAllowance}
              onChange={(e) => setCustomAllowance(e.target.value)}
              placeholder="Default: £12,570"
            />
          </div>

          <Button type="submit" variant="primary" loading={calculating}>
            <Calculator size={18} />
            Calculate Tax
          </Button>
        </form>
      </Card>

      {result && <ResultSection result={result} />}

      <Card>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-purple/10">
            <History size={20} className="text-accent-purple" />
          </div>
          <div>
            <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Previous Calculations</h3>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {history ? `${history.length} calculation${history.length !== 1 ? 's' : ''}` : 'Loading...'}
            </p>
          </div>
        </div>

        <div className="mt-4">
          {historyLoading ? (
            <div className="py-8 text-center">
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Loading history...</p>
            </div>
          ) : !history || history.length === 0 ? (
            <EmptyState
              icon={TrendingUp}
              title="No previous calculations yet"
              description="Run a tax calculation to see it appear here."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b" style={{ borderColor: 'var(--border-default)' }}>
                    <th className="pb-3 pr-4 font-medium" style={{ color: 'var(--text-secondary)' }}>Date</th>
                    <th className="pb-3 pr-4 font-medium" style={{ color: 'var(--text-secondary)' }}>Income</th>
                    <th className="pb-3 pr-4 font-medium" style={{ color: 'var(--text-secondary)' }}>Tax Due</th>
                    <th className="pb-3 pr-4 font-medium" style={{ color: 'var(--text-secondary)' }}>Effective Rate</th>
                    <th className="pb-3 font-medium" style={{ color: 'var(--text-secondary)' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((calc, idx) => (
                    <tr
                      key={calc.id ?? idx}
                      className="border-b last:border-0"
                      style={{ borderColor: 'var(--border-default)' }}
                    >
                      <td className="py-3 pr-4" style={{ color: 'var(--text-primary)' }}>
                        {calc.calculated_at
                          ? new Date(calc.calculated_at).toLocaleDateString('en-GB', {
                              day: 'numeric',
                              month: 'short',
                              year: 'numeric',
                            })
                          : '—'}
                      </td>
                      <td className="py-3 pr-4" style={{ color: 'var(--text-primary)' }}>
                        {formatCurrency(calc.total_income)}
                      </td>
                      <td className="py-3 pr-4 font-medium" style={{ color: 'var(--text-primary)' }}>
                        {formatCurrency(calc.income_tax_due)}
                      </td>
                      <td className="py-3 pr-4" style={{ color: 'var(--text-primary)' }}>
                        {formatPercent(calc.effective_tax_rate)}
                      </td>
                      <td className="py-3">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setResult(calc)}
                        >
                          View Details
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
