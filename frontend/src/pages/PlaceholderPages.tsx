import {
  LayoutDashboard,
  ArrowLeftRight,
  Wallet,
  Calculator,
  FileText,
  Building2,
  BotMessageSquare,
} from 'lucide-react'

interface PlaceholderPageProps {
  title: string
  description: string
  icon: React.ComponentType<{ size?: number; className?: string }>
  accentColor: string
}

function PlaceholderPage({ title, description, icon: Icon, accentColor }: PlaceholderPageProps) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center">
        <div
          className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl"
          style={{ backgroundColor: `${accentColor}15` }}
        >
          <Icon size={32} className={accentColor} />
        </div>
        <h2 className="mb-2 text-2xl font-bold text-white">{title}</h2>
        <p className="max-w-sm text-sm text-slate-400">{description}</p>
      </div>
    </div>
  )
}

// DashboardPage has been moved to ./Dashboard.tsx

export function TransactionsPage() {
  return (
    <PlaceholderPage
      title="Transactions"
      description="View, search, and categorize all your financial transactions in one place."
      icon={ArrowLeftRight}
      accentColor="text-accent-cyan"
    />
  )
}

export function BudgetsPage() {
  return (
    <PlaceholderPage
      title="Budgets"
      description="Set spending limits, track progress, and get AI suggestions to optimize your budget."
      icon={Wallet}
      accentColor="text-success"
    />
  )
}

export function TaxPage() {
  return (
    <PlaceholderPage
      title="Tax"
      description="UK Income Tax estimation for the 2026/27 tax year powered by deterministic calculations."
      icon={Calculator}
      accentColor="text-warning"
    />
  )
}

export function ReportsPage() {
  return (
    <PlaceholderPage
      title="Reports"
      description="Generate detailed financial reports and export them as PDF or CSV."
      icon={FileText}
      accentColor="text-accent-purple"
    />
  )
}

export function AccountsPage() {
  return (
    <PlaceholderPage
      title="Accounts"
      description="Manage your linked bank accounts, savings, and investment portfolios."
      icon={Building2}
      accentColor="text-primary"
    />
  )
}

export function AssistantPage() {
  return (
    <PlaceholderPage
      title="AI Assistant"
      description="Ask your AI finance assistant anything about your spending, budgets, or tax situation."
      icon={BotMessageSquare}
      accentColor="text-accent-purple"
    />
  )
}
