import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import { DashboardPage } from './pages/Dashboard'
import TransactionsPage from './pages/Transactions'
import { BudgetsPage } from './pages/Budgets'
import { TaxPage } from './pages/Tax'
import ReportsPage from './pages/Reports'
import AccountsPage from './pages/Accounts'
import AssistantPage from './pages/Assistant'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="budgets" element={<BudgetsPage />} />
          <Route path="tax" element={<TaxPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="accounts" element={<AccountsPage />} />
          <Route path="assistant" element={<AssistantPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
