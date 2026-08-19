import { useState } from 'react'
import { apiClient } from '../api/client'
import { useAccounts } from '../hooks/useApi'
import { formatDate, cn } from '../utils/format'
import type { Account } from '../types/api'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Select from '../components/ui/Select'
import Modal from '../components/ui/Modal'
import Badge from '../components/ui/Badge'
import EmptyState from '../components/ui/EmptyState'
import { SkeletonCard } from '../components/ui/Skeleton'
import { useToast } from '../contexts/ToastContext'
import { Building2, Plus, CreditCard, PiggyBank, Wallet, Landmark } from 'lucide-react'
import type { AccountType } from '../types/api'

const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  current: 'Current Account',
  savings: 'Savings Account',
  credit_card: 'Credit Card',
  cash: 'Cash',
}

const ACCOUNT_TYPE_ICONS: Record<AccountType, React.ComponentType<{ size?: number; className?: string }>> = {
  current: Landmark,
  savings: PiggyBank,
  credit_card: CreditCard,
  cash: Wallet,
}

const ACCOUNT_TYPE_BADGE: Record<AccountType, 'blue' | 'green' | 'amber' | 'purple'> = {
  current: 'blue',
  savings: 'green',
  credit_card: 'amber',
  cash: 'purple',
}

const ACCOUNT_TYPE_ICON_COLOR: Record<AccountType, string> = {
  current: 'text-primary',
  savings: 'text-success',
  credit_card: 'text-warning',
  cash: 'text-accent-purple',
}

const ACCOUNT_TYPE_ICON_BG: Record<AccountType, string> = {
  current: 'bg-primary/10',
  savings: 'bg-success/10',
  credit_card: 'bg-warning/10',
  cash: 'bg-accent-purple/10',
}

const ACCOUNT_TYPE_OPTIONS = [
  { value: 'current', label: 'Current Account' },
  { value: 'savings', label: 'Savings Account' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'cash', label: 'Cash' },
]

export default function AccountsPage() {
  const { data: accounts, loading, error, refetch } = useAccounts()
  const { toast } = useToast()
  const [showModal, setShowModal] = useState(false)
  const [accountName, setAccountName] = useState('')
  const [accountType, setAccountType] = useState<AccountType>('current')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const handleCreate = async () => {
    if (!accountName.trim()) return
    setCreating(true)
    setCreateError(null)
    try {
      await apiClient.createAccount(accountName.trim(), accountType, 'GBP')
      refetch()
      setShowModal(false)
      setAccountName('')
      setAccountType('current')
      toast('success', 'Account created successfully')
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create account')
    } finally {
      setCreating(false)
    }
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setAccountName('')
    setAccountType('current')
    setCreateError(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Financial Accounts</h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>Manage your financial accounts</p>
        </div>
        <Button variant="primary" size="md" onClick={() => setShowModal(true)}>
          <Plus size={18} />
          Create Account
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : error ? (
        <Card>
          <p className="text-sm text-danger">{error}</p>
        </Card>
      ) : !accounts || accounts.length === 0 ? (
        <Card>
          <EmptyState
            icon={Building2}
            title="No accounts yet"
            description="Create your first account to start tracking finances."
            action={
              <Button variant="primary" size="sm" onClick={() => setShowModal(true)}>
                <Plus size={16} />
                Create Account
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map((account) => {
            const Icon = ACCOUNT_TYPE_ICONS[account.account_type] ?? Wallet
            return (
              <Card key={account.id} hover>
                <div className="mb-4 flex items-start justify-between">
                  <div
                    className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-xl',
                      ACCOUNT_TYPE_ICON_BG[account.account_type],
                    )}
                  >
                    <Icon size={20} className={ACCOUNT_TYPE_ICON_COLOR[account.account_type]} />
                  </div>
                  <Badge variant={ACCOUNT_TYPE_BADGE[account.account_type]}>
                    {ACCOUNT_TYPE_LABELS[account.account_type]}
                  </Badge>
                </div>

                <h3 className="mb-3 text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {account.account_name}
                </h3>

                <div className="space-y-2 border-t pt-3" style={{ borderColor: 'var(--border-default)' }}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Balance</span>
                    <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {account.current_balance != null ? formatCurrency(account.current_balance) : 'Not set'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Created</span>
                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{formatDate(account.created_at)}</span>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      <Modal open={showModal} onClose={handleCloseModal} title="Create Account" maxWidth="max-w-md">
        <div className="space-y-4">
          <Input
            label="Account Name"
            type="text"
            value={accountName}
            onChange={(e) => setAccountName(e.target.value)}
            placeholder="e.g. Main Current Account"
          />

          <Select
            label="Account Type"
            options={ACCOUNT_TYPE_OPTIONS}
            value={accountType}
            onChange={(e) => setAccountType(e.target.value as AccountType)}
          />

          <Input
            label="Currency"
            type="text"
            value="GBP"
            disabled
          />

          {createError && (
            <div className="rounded-xl border border-danger/20 bg-danger/10 px-4 py-3">
              <p className="text-sm text-danger">{createError}</p>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={handleCloseModal}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              loading={creating}
              disabled={!accountName.trim()}
            >
              Create
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

function formatCurrency(value: number): string {
  return `£${value.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
