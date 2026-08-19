import { useState, useEffect } from 'react'
import { apiClient } from '../api/client'
import { useBudgets } from '../hooks/useApi'
import { formatCurrency, formatDate, getStatusLabel, cn } from '../utils/format'
import type { Budget, BudgetCreateRequest } from '../types/api'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import ProgressBar from '../components/ui/ProgressBar'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { SkeletonCard } from '../components/ui/Skeleton'
import { useToast } from '../contexts/ToastContext'
import { Plus, Wallet, Edit2, Trash2 } from 'lucide-react'

function getProgressColor(percentage: number): 'green' | 'amber' | 'red' {
  if (percentage > 100) return 'red'
  if (percentage >= 80) return 'amber'
  return 'green'
}

function SummaryCard({
  label,
  value,
  icon: Icon,
  iconColor,
}: {
  label: string
  value: string
  icon: React.ComponentType<{ size?: number; className?: string }>
  iconColor: string
}) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{label}</p>
          <p className="mt-1 text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{value}</p>
        </div>
        <div
          className={cn(
            'flex h-11 w-11 items-center justify-center rounded-xl',
            iconColor,
          )}
        >
          <Icon size={22} />
        </div>
      </div>
    </Card>
  )
}

function BudgetCard({
  budget,
  onEdit,
  onDelete,
}: {
  budget: Budget
  onEdit: (budget: Budget) => void
  onDelete: (id: string) => void
}) {
  const progressColor = getProgressColor(budget.percentage_used)

  return (
    <Card hover>
      <div className="mb-4 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Wallet size={20} className="text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{budget.category_name}</h3>
            <p className="mt-0.5 text-xs" style={{ color: 'var(--text-secondary)' }}>
              {formatDate(budget.period_start)} — {formatDate(budget.period_end)}
            </p>
          </div>
        </div>
        <Badge variant={budget.status === 'under_budget' ? 'green' : budget.status === 'near_limit' ? 'amber' : 'red'}>
          {getStatusLabel(budget.status)}
        </Badge>
      </div>

      <div className="mb-3">
        <div className="flex items-baseline justify-between">
          <span className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
            {formatCurrency(budget.actual_spending)}
          </span>
          <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            / {formatCurrency(budget.budget_amount)}
          </span>
        </div>
      </div>

      <div className="mb-3">
        <ProgressBar
          value={budget.percentage_used}
          color={progressColor}
          height={8}
        />
      </div>

      <div className="mb-4 flex items-center justify-between text-xs" style={{ color: 'var(--text-secondary)' }}>
        <span>{budget.percentage_used.toFixed(1)}% used</span>
        <span>{budget.transaction_count} transaction{budget.transaction_count !== 1 ? 's' : ''}</span>
      </div>

      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          className="flex-1"
          onClick={() => onEdit(budget)}
        >
          <Edit2 size={14} />
          Edit
        </Button>
        <Button
          variant="danger"
          size="sm"
          className="flex-1"
          onClick={() => onDelete(budget.id)}
        >
          <Trash2 size={14} />
          Delete
        </Button>
      </div>
    </Card>
  )
}

function CreateBudgetModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: () => void
}) {
  const { toast } = useToast()
  const [categoryId, setCategoryId] = useState('')
  const [amount, setAmount] = useState('')
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [categories, setCategories] = useState<Array<{ value: string; label: string }>>([])
  const [loading, setLoading] = useState(false)
  const [categoriesLoading, setCategoriesLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setCategoryId('')
    setAmount('')
    setPeriodStart('')
    setPeriodEnd('')
    setError('')
    setLoading(false)

    let cancelled = false
    setCategoriesLoading(true)
    apiClient
      .listCategories()
      .then((cats) => {
        if (cancelled) return
        setCategories(
          cats
            .filter((c) => c.category_type === 'expense')
            .map((c) => ({ value: c.id, label: c.name }))
        )
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load categories')
      })
      .finally(() => {
        if (!cancelled) setCategoriesLoading(false)
      })
    return () => { cancelled = true }
  }, [open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!categoryId) {
      setError('Please select a category')
      return
    }
    const amountNum = parseFloat(amount)
    if (isNaN(amountNum) || amountNum <= 0) {
      setError('Budget amount must be greater than zero')
      return
    }
    if (!periodStart) {
      setError('Please select a start date')
      return
    }
    if (!periodEnd) {
      setError('Please select an end date')
      return
    }
    if (new Date(periodEnd) < new Date(periodStart)) {
      setError('End date must be on or after the start date')
      return
    }

    setLoading(true)
    try {
      const payload: BudgetCreateRequest = {
        category_id: categoryId,
        budget_amount: amountNum,
        period_start: periodStart,
        period_end: periodEnd,
      }
      await apiClient.createBudget(payload)
      toast('success', 'Budget created successfully')
      onCreated()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create budget')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Create Budget">
      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger">
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Select
          label="Category"
          placeholder={categoriesLoading ? 'Loading categories...' : 'Select a category'}
          options={categories}
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          disabled={categoriesLoading}
        />

        <Input
          label="Budget Amount (£)"
          type="number"
          step="0.01"
          min="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.00"
        />

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Start Date"
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
          />
          <Input
            label="End Date"
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
          />
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="secondary" className="flex-1" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" className="flex-1" loading={loading}>
            <Plus size={16} />
            Create Budget
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function EditBudgetModal({
  open,
  budget,
  onClose,
  onUpdated,
}: {
  open: boolean
  budget: Budget | null
  onClose: () => void
  onUpdated: () => void
}) {
  const { toast } = useToast()
  const [amount, setAmount] = useState('')
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || !budget) return
    setAmount(String(budget.budget_amount))
    setPeriodStart(budget.period_start.split('T')[0])
    setPeriodEnd(budget.period_end.split('T')[0])
    setError('')
    setLoading(false)
  }, [open, budget])

  const handleSubmit = async (e: React.FormEvent) => {
    if (!budget) return
    e.preventDefault()
    setError('')

    const amountNum = parseFloat(amount)
    if (isNaN(amountNum) || amountNum <= 0) {
      setError('Budget amount must be greater than zero')
      return
    }
    if (!periodStart || !periodEnd) {
      setError('Both dates are required')
      return
    }
    if (new Date(periodEnd) < new Date(periodStart)) {
      setError('End date must be on or after the start date')
      return
    }

    setLoading(true)
    try {
      await apiClient.updateBudget(budget.id, {
        budget_amount: amountNum,
        period_start: periodStart,
        period_end: periodEnd,
      })
      toast('success', 'Budget updated successfully')
      onUpdated()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update budget')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Edit Budget">
      {budget && (
        <p className="mb-4 text-sm" style={{ color: 'var(--text-secondary)' }}>{budget.category_name}</p>
      )}

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger">
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Budget Amount (£)"
          type="number"
          step="0.01"
          min="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Start Date"
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
          />
          <Input
            label="End Date"
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
          />
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="secondary" className="flex-1" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" className="flex-1" loading={loading}>
            <Edit2 size={16} />
            Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export function BudgetsPage() {
  const { data: budgets, loading, error, refetch } = useBudgets()
  const { toast } = useToast()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null)

  const totalBudget = budgets
    ? budgets.reduce((sum, b) => sum + b.budget_amount, 0)
    : 0
  const totalSpent = budgets
    ? budgets.reduce((sum, b) => sum + b.actual_spending, 0)
    : 0
  const totalRemaining = totalBudget - totalSpent
  const overallUsage = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this budget?')) return
    try {
      await apiClient.deleteBudget(id)
      toast('success', 'Budget deleted')
      refetch()
    } catch (err) {
      toast('error', err instanceof Error ? err.message : 'Failed to delete budget')
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Budgets</h2>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <ErrorState message={error} onRetry={refetch} />
    )
  }

  const isEmpty = !budgets || budgets.length === 0

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Budgets</h2>
        </div>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={18} />
          Create Budget
        </Button>
      </div>

      {!isEmpty && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard
            label="Total Budget"
            value={formatCurrency(totalBudget)}
            icon={Wallet}
            iconColor="bg-primary/10 text-primary"
          />
          <SummaryCard
            label="Total Spent"
            value={formatCurrency(totalSpent)}
            icon={Wallet}
            iconColor="bg-accent-purple/10 text-accent-purple"
          />
          <SummaryCard
            label="Remaining"
            value={formatCurrency(totalRemaining)}
            icon={Wallet}
            iconColor={cn(
              totalRemaining >= 0 ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger',
            )}
          />
          <SummaryCard
            label="Overall Usage"
            value={`${overallUsage.toFixed(1)}%`}
            icon={Wallet}
            iconColor="bg-accent-cyan/10 text-accent-cyan"
          />
        </div>
      )}

      {isEmpty ? (
        <EmptyState
          icon={Wallet}
          title="No budgets yet"
          description="Create your first budget to start tracking spending."
          action={
            <Button variant="primary" onClick={() => setShowCreateModal(true)}>
              <Plus size={18} />
              Create Budget
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {budgets!.map((budget) => (
            <BudgetCard
              key={budget.id}
              budget={budget}
              onEdit={(b) => setEditingBudget(b)}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <CreateBudgetModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={refetch}
      />

      <EditBudgetModal
        open={editingBudget !== null}
        budget={editingBudget}
        onClose={() => setEditingBudget(null)}
        onUpdated={refetch}
      />
    </div>
  )
}
