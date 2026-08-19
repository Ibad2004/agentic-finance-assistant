export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export type AccountType = "current" | "savings" | "credit_card" | "cash";

export interface Account {
  id: string;
  account_name: string;
  account_type: AccountType;
  currency_code: string;
  current_balance: number | null;
  is_active: boolean;
  created_at: string;
}

export interface Transaction {
  id: string;
  transaction_date: string;
  description: string;
  amount: number;
  transaction_type: "income" | "expense";
  category: string | null;
  source: "csv" | "sample";
  is_reviewed: boolean;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total_count: number;
}

export interface TransactionFilters {
  limit?: number;
  offset?: number;
  start_date?: string;
  end_date?: string;
  category?: string;
  transaction_type?: "income" | "expense";
  min_amount?: number;
  max_amount?: number;
}

export interface Budget {
  id: string;
  category_id: string;
  category_name: string;
  budget_amount: number;
  period_start: string;
  period_end: string;
  actual_spending: number;
  remaining: number;
  percentage_used: number;
  status: "under_budget" | "near_limit" | "over_budget";
  transaction_count: number;
  created_at: string;
}

export interface BudgetCreateRequest {
  category_id: string;
  period_start: string;
  period_end: string;
  budget_amount: number;
}

export interface BudgetUpdateRequest {
  budget_amount?: number;
  period_start?: string;
  period_end?: string;
}

export interface TaxBandBreakdown {
  band_name: string;
  rate: number;
  taxable_amount: number;
  tax_due: number;
}

export interface TaxCalculation {
  id: string | null;
  user_id: string | null;
  tax_year: string;
  rules_version: string;
  calculated_at: string | null;
  total_income: number;
  total_allowances: number;
  taxable_income: number;
  income_tax_due: number;
  effective_tax_rate: number;
  marginal_tax_rate: number;
  band_breakdown: TaxBandBreakdown[];
  assumptions: string;
  limitations: string;
  calculation_details: Record<string, unknown> | null;
  is_estimate: boolean;
}

export type ReportType = "monthly_summary" | "expense_summary" | "tax_summary";

export interface Report {
  id: string;
  report_type: ReportType;
  period_start: string;
  period_end: string;
  file_format: string;
  storage_path: string;
  generated_at: string;
}

export interface ReportDetail extends Report {
  total_income: number;
  total_expenses: number;
  net_amount: number;
  transaction_count: number;
  category_breakdown: Record<string, number>;
}

export interface ImportIssue {
  row_number: number | null;
  field: string | null;
  code: string;
  message: string;
}

export interface CsvImportResult {
  rows_read: number;
  rows_imported: number;
  rows_rejected: number;
  duplicate_rows: number;
  possible_duplicate_rows: number;
  validation_errors: ImportIssue[];
  imported_transaction_ids: string[];
}

export interface CategorizationResult {
  saved_transaction_ids: string[];
  needs_review_transaction_ids: string[];
  failed_transactions: Array<{
    transaction_id: string | null;
    code: string;
  }>;
  sanitized_errors: string[];
  batches_processed: number;
}

export interface Category {
  id: string;
  name: string;
  category_type: "income" | "expense";
}

export interface ApiError {
  detail: string;
}
