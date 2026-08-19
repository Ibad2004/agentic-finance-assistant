import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../api/client'
import { useAccounts } from '../hooks/useApi'
import { formatCurrency, formatDate, cn } from '../utils/format'
import type { Transaction, TransactionFilters, Category } from '../types/api'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { SkeletonTable } from '../components/ui/Skeleton'
import { useToast } from '../contexts/ToastContext'
import { Search, Upload, Sparkles, ChevronLeft, ChevronRight, FileSpreadsheet, X } from 'lucide-react'

const PAGE_SIZE = 15

export default function TransactionsPage() {
  const { toast } = useToast()
  const { data: accounts, loading: accountsLoading } = useAccounts()

  const [selectedAccountId, setSelectedAccountId] = useState<string>('')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)

  const [search, setSearch] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [typeFilter, setTypeFilter] = useState<'income' | 'expense' | ''>('')

  const [csvModalOpen, setCsvModalOpen] = useState(false)
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [csvLoading, setCsvLoading] = useState(false)
  const [csvResult, setCsvResult] = useState<{
    rows_read: number
    rows_imported: number
    rows_rejected: number
    duplicate_rows: number
  } | null>(null)

  const [catLoading, setCatLoading] = useState(false)

  useEffect(() => {
    if (accounts && accounts.length > 0 && !selectedAccountId) {
      setSelectedAccountId(accounts[0].id)
    }
  }, [accounts, selectedAccountId])

  const fetchTransactions = useCallback(async () => {
    if (!selectedAccountId) {
      setTransactions([])
      setTotalCount(0)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const filters: TransactionFilters = {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }
      if (startDate) filters.start_date = startDate
      if (endDate) filters.end_date = endDate
      if (typeFilter) filters.transaction_type = typeFilter as 'income' | 'expense'

      const result = await apiClient.listTransactions(selectedAccountId, filters)
      setTransactions(result.transactions)
      setTotalCount(result.total_count)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transactions')
      setTransactions([])
      setTotalCount(0)
    } finally {
      setLoading(false)
    }
  }, [selectedAccountId, page, startDate, endDate, typeFilter])

  useEffect(() => {
    fetchTransactions()
  }, [fetchTransactions])

  useEffect(() => {
    setPage(0)
  }, [selectedAccountId, startDate, endDate, typeFilter])

  const hasActiveFilters = search || startDate || endDate || typeFilter

  const clearFilters = () => {
    setSearch('')
    setStartDate('')
    setEndDate('')
    setTypeFilter('')
  }

  const filteredTransactions = search
    ? transactions.filter((t) =>
        t.description.toLowerCase().includes(search.toLowerCase()),
      )
    : transactions

  const totalPages = Math.ceil(totalCount / PAGE_SIZE)
  const pageStart = page * PAGE_SIZE + 1
  const pageEnd = Math.min((page + 1) * PAGE_SIZE, totalCount)

  const handleCsvImport = async () => {
    if (!csvFile || !selectedAccountId) return
    setCsvLoading(true)
    try {
      const result = await apiClient.importCsv(selectedAccountId, csvFile)
      setCsvResult(result)
      toast('success', `Imported ${result.rows_imported} transactions`)
      fetchTransactions()
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Import failed')
    } finally {
      setCsvLoading(false)
    }
  }

  const handleCategorize = async () => {
    if (!selectedAccountId) return
    setCatLoading(true)
    try {
      const result = await apiClient.categorizeTransactions(selectedAccountId)
      const saved = result.saved_transaction_ids.length
      const review = result.needs_review_transaction_ids.length
      const failed = result.failed_transactions.length
      toast('success', `Categorized: ${saved} saved, ${review} to review, ${failed} failed`)
      fetchTransactions()
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Categorization failed')
    } finally {
      setCatLoading(false)
    }
  }

  const resetCsvModal = () => {
    setCsvModalOpen(false)
    setCsvFile(null)
    setCsvResult(null)
  }

  const accountOptions = accounts
    ? accounts.map((acc) => ({
        value: acc.id,
        label: `${acc.account_name} (${acc.account_type.replace('_', ' ')})`,
      }))
    : []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1
          className="text-2xl font-bold"
          style={{ color: 'var(--text-primary)' }}
        >
          Transactions
        </h1>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={handleCategorize}
            disabled={!selectedAccountId || catLoading}
            loading={catLoading}
          >
            <Sparkles size={16} />
            AI Categorize
          </Button>
          <Button
            variant="primary"
            onClick={() => setCsvModalOpen(true)}
            disabled={!selectedAccountId}
          >
            <Upload size={16} />
            Import CSV
          </Button>
        </div>
      </div>

      {/* Account selector */}
      {accountsLoading ? (
        <div className="h-10 w-64 skeleton rounded-lg" />
      ) : accountOptions.length > 0 ? (
        <div className="flex items-center gap-4">
          <label
            className="text-sm font-medium"
            style={{ color: 'var(--text-secondary)' }}
          >
            Account
          </label>
          <Select
            options={accountOptions}
            value={selectedAccountId}
            onChange={(e) => {
              setSelectedAccountId(e.target.value)
              setPage(0)
            }}
          />
        </div>
      ) : (
        <EmptyState
          icon={FileSpreadsheet}
          title="No accounts"
          description="Create an account first to manage your transactions."
        />
      )}

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: 'var(--text-tertiary)' }}
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search transactions..."
            className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--bg-input)] py-2 pl-9 pr-3 text-sm outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary"
            style={{ color: 'var(--text-primary)' }}
          />
        </div>
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-input)] px-3 py-2 text-sm outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary [color-scheme:dark]"
          style={{ color: 'var(--text-primary)' }}
        />
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-input)] px-3 py-2 text-sm outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary [color-scheme:dark]"
          style={{ color: 'var(--text-primary)' }}
        />
        <div
          className="flex rounded-lg border p-0.5"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-input)' }}
        >
          {(['', 'income', 'expense'] as const).map((val) => (
            <button
              key={val}
              type="button"
              onClick={() => setTypeFilter(val)}
              className={cn(
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                typeFilter === val
                  ? val === 'income'
                    ? 'bg-success/15 text-success'
                    : val === 'expense'
                      ? 'bg-danger/15 text-danger'
                      : 'bg-[var(--bg-surface-secondary)] text-[var(--text-primary)]'
                  : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)]',
              )}
            >
              {val === '' ? 'All' : val === 'income' ? 'Income' : 'Expense'}
            </button>
          ))}
        </div>
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X size={14} />
            Clear
          </Button>
        )}
      </div>

      {/* Error */}
      {error && (
        <ErrorState
          message={error}
          onRetry={fetchTransactions}
        />
      )}

      {/* Loading */}
      {loading && <SkeletonTable rows={8} />}

      {/* Empty state */}
      {!loading && !error && filteredTransactions.length === 0 && (
        <Card>
          <EmptyState
            icon={FileSpreadsheet}
            title="No transactions found"
            description={
              !selectedAccountId
                ? 'Select an account to view transactions.'
                : hasActiveFilters
                  ? 'Try adjusting your filters.'
                  : 'Import a CSV file to get started.'
            }
          />
        </Card>
      )}

      {/* Transactions table */}
      {!loading && !error && filteredTransactions.length > 0 && (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            {/* Table header */}
            <div
              className="grid grid-cols-[140px_1fr_160px_100px_120px] gap-4 border-b px-6 py-3"
              style={{ borderColor: 'var(--border-default)' }}
            >
              <span
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Date
              </span>
              <span
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Description
              </span>
              <span
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Category
              </span>
              <span
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Type
              </span>
              <span
                className="text-right text-xs font-semibold uppercase tracking-wider"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Amount
              </span>
            </div>

            {/* Rows */}
            <div>
              {filteredTransactions.map((tx, idx) => (
                <div
                  key={tx.id}
                  className={cn(
                    'grid grid-cols-[140px_1fr_160px_100px_120px] gap-4 border-b px-6 py-3.5 transition-colors hover:bg-[var(--bg-surface-hover)]',
                    idx % 2 === 1 ? 'bg-[var(--bg-surface-secondary)]' : 'bg-[var(--bg-surface)]',
                  )}
                  style={{ borderColor: 'var(--border-default)' }}
                >
                  <span
                    className="text-sm"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    {formatDate(tx.transaction_date)}
                  </span>
                  <span
                    className="truncate text-sm font-medium"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {tx.description}
                  </span>
                  <span>
                    <Badge variant={tx.transaction_type === 'income' ? 'blue' : 'purple'}>
                      {tx.category ?? 'Uncategorized'}
                    </Badge>
                  </span>
                  <span>
                    <Badge variant={tx.transaction_type === 'income' ? 'green' : 'red'}>
                      {tx.transaction_type === 'income' ? 'Income' : 'Expense'}
                    </Badge>
                  </span>
                  <span
                    className={cn(
                      'text-right text-sm font-semibold tabular-nums',
                      tx.transaction_type === 'income' ? 'text-success' : 'text-danger',
                    )}
                  >
                    {tx.transaction_type === 'income' ? '+' : '-'}
                    {formatCurrency(Math.abs(tx.amount))}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* Pagination */}
      {totalCount > 0 && !loading && (
        <div className="flex items-center justify-between">
          <p
            className="text-sm"
            style={{ color: 'var(--text-secondary)' }}
          >
            Showing{' '}
            <span
              className="font-medium"
              style={{ color: 'var(--text-primary)' }}
            >
              {pageStart}–{pageEnd}
            </span>{' '}
            of{' '}
            <span
              className="font-medium"
              style={{ color: 'var(--text-primary)' }}
            >
              {totalCount}
            </span>{' '}
            transactions
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              <ChevronLeft size={16} />
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
            >
              Next
              <ChevronRight size={16} />
            </Button>
          </div>
        </div>
      )}

      {/* CSV Import Modal */}
      <Modal open={csvModalOpen} onClose={resetCsvModal} title="Import CSV">
        {!csvResult ? (
          <div className="space-y-4">
            <div
              className={cn(
                'flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors',
                csvFile
                  ? 'border-success/40 bg-success/5'
                  : 'border-[var(--border-default)] hover:border-[var(--border-strong)]',
              )}
              style={{ backgroundColor: csvFile ? undefined : 'var(--bg-input)' }}
            >
              {csvFile ? (
                <>
                  <FileSpreadsheet size={32} className="mb-3 text-success" />
                  <p
                    className="text-sm font-medium"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {csvFile.name}
                  </p>
                  <p
                    className="mt-1 text-xs"
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    {(csvFile.size / 1024).toFixed(1)} KB
                  </p>
                  <button
                    type="button"
                    onClick={() => setCsvFile(null)}
                    className="mt-3 text-xs font-medium text-primary transition-colors hover:text-primary-hover"
                  >
                    Choose a different file
                  </button>
                </>
              ) : (
                <>
                  <Upload size={32} className="mb-3" style={{ color: 'var(--text-tertiary)' }} />
                  <p
                    className="text-sm"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Drag & drop a CSV file here, or{' '}
                    <label className="cursor-pointer font-medium text-primary hover:text-primary-hover">
                      browse
                      <input
                        type="file"
                        accept=".csv"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0]
                          if (f) setCsvFile(f)
                        }}
                      />
                    </label>
                  </p>
                  <p
                    className="mt-1 text-xs"
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    Supports .csv files only
                  </p>
                </>
              )}
            </div>

            <div className="flex justify-end gap-3">
              <Button variant="ghost" onClick={resetCsvModal}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleCsvImport}
                disabled={!csvFile || csvLoading}
                loading={csvLoading}
              >
                <Upload size={16} />
                Import
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div
              className="rounded-xl p-4"
              style={{ backgroundColor: 'var(--bg-input)' }}
            >
              <p className="mb-3 text-sm font-medium text-success">
                Import complete
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div
                  className="rounded-lg p-3"
                  style={{ backgroundColor: 'var(--bg-surface-secondary)' }}
                >
                  <p
                    className="text-xs"
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    Rows Read
                  </p>
                  <p
                    className="mt-0.5 text-lg font-bold"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {csvResult.rows_read}
                  </p>
                </div>
                <div
                  className="rounded-lg p-3"
                  style={{ backgroundColor: 'var(--bg-surface-secondary)' }}
                >
                  <p
                    className="text-xs"
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    Imported
                  </p>
                  <p className="mt-0.5 text-lg font-bold text-success">
                    {csvResult.rows_imported}
                  </p>
                </div>
                <div
                  className="rounded-lg p-3"
                  style={{ backgroundColor: 'var(--bg-surface-secondary)' }}
                >
                  <p
                    className="text-xs"
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    Duplicates
                  </p>
                  <p className="mt-0.5 text-lg font-bold text-warning">
                    {csvResult.duplicate_rows}
                  </p>
                </div>
                <div
                  className="rounded-lg p-3"
                  style={{ backgroundColor: 'var(--bg-surface-secondary)' }}
                >
                  <p
                    className="text-xs"
                    style={{ color: 'var(--text-tertiary)' }}
                  >
                    Rejected
                  </p>
                  <p className="mt-0.5 text-lg font-bold text-danger">
                    {csvResult.rows_rejected}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  resetCsvModal()
                  handleCategorize()
                }}
              >
                <Sparkles size={16} />
                Categorize Now
              </Button>
              <Button variant="primary" onClick={resetCsvModal}>
                Done
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
