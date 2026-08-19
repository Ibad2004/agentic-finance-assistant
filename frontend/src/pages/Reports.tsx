import { useState } from 'react'
import { apiClient } from '../api/client'
import { useReports } from '../hooks/useApi'
import { formatCurrency, formatDate, cn } from '../utils/format'
import type { Report, ReportDetail, ReportType } from '../types/api'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Modal from '../components/ui/Modal'
import Badge from '../components/ui/Badge'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { SkeletonTable } from '../components/ui/Skeleton'
import { useToast } from '../contexts/ToastContext'
import { FileText, Plus, Download, Eye } from 'lucide-react'

const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  monthly_summary: 'Monthly Summary',
  expense_summary: 'Expense Summary',
  tax_summary: 'Tax Summary',
}

const REPORT_TYPE_BADGE: Record<ReportType, 'blue' | 'purple' | 'amber'> = {
  monthly_summary: 'blue',
  expense_summary: 'purple',
  tax_summary: 'amber',
}

const REPORT_TYPE_OPTIONS = [
  { value: 'monthly_summary', label: 'Monthly Summary' },
  { value: 'expense_summary', label: 'Expense Summary' },
  { value: 'tax_summary', label: 'Tax Summary' },
]

export default function ReportsPage() {
  const { data: reports, loading, error, refetch } = useReports()
  const { toast } = useToast()
  const [showModal, setShowModal] = useState(false)
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null)
  const [reportDetail, setReportDetail] = useState<ReportDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const [reportType, setReportType] = useState<ReportType>('monthly_summary')
  const [periodStart, setPeriodStart] = useState('2026-04-01')
  const [periodEnd, setPeriodEnd] = useState('2026-04-30')
  const [generating, setGenerating] = useState(false)
  const [generatedDetail, setGeneratedDetail] = useState<ReportDetail | null>(null)
  const [generateError, setGenerateError] = useState<string | null>(null)

  const handleGenerate = async () => {
    setGenerating(true)
    setGenerateError(null)
    setGeneratedDetail(null)
    try {
      const result = await apiClient.generateReport(reportType, periodStart, periodEnd)
      setGeneratedDetail(result)
      refetch()
      toast('success', `${REPORT_TYPE_LABELS[reportType]} report generated`)
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : 'Failed to generate report')
    } finally {
      setGenerating(false)
    }
  }

  const handleViewDetail = async (reportId: string) => {
    setSelectedReportId(reportId)
    setLoadingDetail(true)
    try {
      const detail = await apiClient.getReport(reportId)
      setReportDetail(detail as ReportDetail)
    } catch {
      setReportDetail(null)
    } finally {
      setLoadingDetail(false)
    }
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setGeneratedDetail(null)
    setGenerateError(null)
  }

  if (selectedReportId && reportDetail) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setSelectedReportId(null)
              setReportDetail(null)
            }}
          >
            Back to Reports
          </Button>
        </div>

        <Card>
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-purple/15">
              <FileText size={20} className="text-accent-purple" />
            </div>
            <div>
              <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                {REPORT_TYPE_LABELS[reportDetail.report_type]}
              </h2>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                {formatDate(reportDetail.period_start)} — {formatDate(reportDetail.period_end)}
              </p>
            </div>
          </div>

          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface-secondary)' }}>
              <p className="mb-1 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Total Income</p>
              <p className="text-xl font-bold text-success">{formatCurrency(reportDetail.total_income)}</p>
            </div>
            <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface-secondary)' }}>
              <p className="mb-1 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Total Expenses</p>
              <p className="text-xl font-bold text-danger">{formatCurrency(reportDetail.total_expenses)}</p>
            </div>
            <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface-secondary)' }}>
              <p className="mb-1 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Net Amount</p>
              <p className={cn('text-xl font-bold', reportDetail.net_amount >= 0 ? 'text-success' : 'text-danger')}>
                {formatCurrency(reportDetail.net_amount)}
              </p>
            </div>
            <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface-secondary)' }}>
              <p className="mb-1 text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Transactions</p>
              <p className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{reportDetail.transaction_count}</p>
            </div>
          </div>

          {Object.keys(reportDetail.category_breakdown).length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Category Breakdown</h3>
              <div className="space-y-2">
                {Object.entries(reportDetail.category_breakdown)
                  .sort(([, a], [, b]) => b - a)
                  .map(([category, amount]) => (
                    <div
                      key={category}
                      className="flex items-center justify-between rounded-lg border px-4 py-3"
                      style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface-secondary)' }}
                    >
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{category}</span>
                      <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{formatCurrency(amount)}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Financial Reports</h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>Generate and view financial reports</p>
        </div>
        <Button variant="primary" size="md" onClick={() => setShowModal(true)}>
          <Plus size={18} />
          Generate Report
        </Button>
      </div>

      <Card>
        {loading ? (
          <SkeletonTable rows={5} />
        ) : error ? (
          <ErrorState message={error} onRetry={refetch} />
        ) : !reports || reports.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No reports generated yet"
            description="Generate your first financial report to get started."
            action={
              <Button variant="primary" size="sm" onClick={() => setShowModal(true)}>
                <Plus size={16} />
                Generate Report
              </Button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border-default)' }}>
                  <th className="px-6 py-4 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Type</th>
                  <th className="px-6 py-4 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Period</th>
                  <th className="px-6 py-4 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Format</th>
                  <th className="px-6 py-4 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Generated</th>
                  <th className="px-6 py-4 text-right text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: 'var(--border-default)' }}>
                {reports.map((report) => (
                  <tr
                    key={report.id}
                    className="transition-colors hover:bg-[var(--bg-surface-hover)]"
                  >
                    <td className="px-6 py-4">
                      <Badge variant={REPORT_TYPE_BADGE[report.report_type]}>
                        {REPORT_TYPE_LABELS[report.report_type]}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-sm" style={{ color: 'var(--text-secondary)' }}>
                      {formatDate(report.period_start)} — {formatDate(report.period_end)}
                    </td>
                    <td className="px-6 py-4 text-sm uppercase" style={{ color: 'var(--text-secondary)' }}>{report.file_format}</td>
                    <td className="px-6 py-4 text-sm" style={{ color: 'var(--text-tertiary)' }}>{formatDate(report.generated_at)}</td>
                    <td className="px-6 py-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewDetail(report.id)}
                      >
                        <Eye size={14} />
                        View Details
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={showModal} onClose={handleCloseModal} title="Generate Report">
        <div className="space-y-4">
          <Select
            label="Report Type"
            options={REPORT_TYPE_OPTIONS}
            value={reportType}
            onChange={(e) => setReportType(e.target.value as ReportType)}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Period Start"
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
            />
            <Input
              label="Period End"
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
            />
          </div>

          {generateError && (
            <div className="rounded-xl border border-danger/20 bg-danger/10 px-4 py-3">
              <p className="text-sm text-danger">{generateError}</p>
            </div>
          )}

          {generatedDetail && (
            <div className="space-y-3 rounded-xl border border-success/20 bg-success/5 p-4">
              <p className="text-xs font-medium uppercase tracking-wider text-success">Report Generated</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Income</p>
                  <p className="text-sm font-semibold text-success">{formatCurrency(generatedDetail.total_income)}</p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Expenses</p>
                  <p className="text-sm font-semibold text-danger">{formatCurrency(generatedDetail.total_expenses)}</p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Net</p>
                  <p className={cn('text-sm font-semibold', generatedDetail.net_amount >= 0 ? 'text-success' : 'text-danger')}>
                    {formatCurrency(generatedDetail.net_amount)}
                  </p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Transactions</p>
                  <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{generatedDetail.transaction_count}</p>
                </div>
              </div>
              {Object.keys(generatedDetail.category_breakdown).length > 0 && (
                <div>
                  <p className="mb-1.5 text-xs" style={{ color: 'var(--text-tertiary)' }}>Categories</p>
                  <div className="space-y-1">
                    {Object.entries(generatedDetail.category_breakdown)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 5)
                      .map(([cat, amount]) => (
                        <div key={cat} className="flex items-center justify-between text-xs">
                          <span style={{ color: 'var(--text-secondary)' }}>{cat}</span>
                          <span style={{ color: 'var(--text-primary)' }}>{formatCurrency(amount)}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={handleCloseModal}>
              Close
            </Button>
            <Button
              variant="primary"
              onClick={handleGenerate}
              loading={generating}
            >
              <Plus size={16} />
              Generate
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
