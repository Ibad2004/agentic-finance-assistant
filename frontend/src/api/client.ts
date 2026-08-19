import { getStoredToken, clearStoredAuth } from "../contexts/AuthContext";
import type {
  Account,
  ApiError,
  Budget,
  BudgetCreateRequest,
  BudgetUpdateRequest,
  Category,
  CsvImportResult,
  CategorizationResult,
  Report,
  ReportDetail,
  ReportType,
  TaxCalculation,
  TokenResponse,
  TransactionFilters,
  TransactionListResponse,
  User,
} from "../types/api";

const DEFAULT_BASE_URL = "/api";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl ?? DEFAULT_BASE_URL;
  }

  private buildUrl(path: string, params?: Record<string, string | number | boolean | undefined | null>): string {
    const base = this.baseUrl === "/api" ? "" : this.baseUrl;
    let url = `${base}${path}`;
    if (params) {
      const searchParams = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null && value !== "") {
          searchParams.set(key, String(value));
        }
      }
      const qs = searchParams.toString();
      if (qs) {
        url += `?${qs}`;
      }
    }
    return url;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    params?: Record<string, string | number | boolean | undefined | null>,
  ): Promise<T> {
    const url = this.buildUrl(path, params);
    const token = getStoredToken();

    const headers: Record<string, string> = {
      ...((options.headers as Record<string, string>) ?? {}),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      clearStoredAuth();
      window.location.href = "/login";
      throw new Error("Session expired. Please log in again.");
    }

    if (!response.ok) {
      let errorDetail = `Request failed with status ${response.status}`;
      try {
        const body: ApiError = await response.json();
        errorDetail = body.detail ?? errorDetail;
      } catch {
        // response body wasn't JSON
      }
      throw new Error(errorDetail);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  // ── Auth ──

  async register(
    email: string,
    password: string,
    full_name?: string,
  ): Promise<User> {
    return this.request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: full_name ?? null }),
    });
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    const data = await this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    return data;
  }

  // ── Accounts ──

  async listAccounts(): Promise<Account[]> {
    return this.request<Account[]>("/accounts");
  }

  async createAccount(
    account_name: string,
    account_type: string,
    currency_code: string = "GBP",
  ): Promise<Account> {
    return this.request<Account>("/accounts", {
      method: "POST",
      body: JSON.stringify({ account_name, account_type, currency_code }),
    });
  }

  // ── Transactions ──

  async listTransactions(
    accountId: string,
    filters: TransactionFilters = {},
  ): Promise<TransactionListResponse> {
    const params: Record<string, string | number | boolean | undefined | null> = {};
    if (filters.limit !== undefined) params.limit = filters.limit;
    if (filters.offset !== undefined) params.offset = filters.offset;
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.category) params.category = filters.category;
    if (filters.transaction_type) params.transaction_type = filters.transaction_type;
    if (filters.min_amount !== undefined) params.min_amount = filters.min_amount;
    if (filters.max_amount !== undefined) params.max_amount = filters.max_amount;

    return this.request<TransactionListResponse>(
      `/accounts/${accountId}/transactions`,
      {},
      params,
    );
  }

  async importCsv(
    accountId: string,
    file: File,
  ): Promise<CsvImportResult> {
    const formData = new FormData();
    formData.append("file", file);
    return this.request<CsvImportResult>(
      `/accounts/${accountId}/transactions/import`,
      {
        method: "POST",
        body: formData,
      },
    );
  }

  async categorizeTransactions(
    accountId: string,
  ): Promise<CategorizationResult> {
    return this.request<CategorizationResult>(
      `/accounts/${accountId}/transactions/categorize`,
      {
        method: "POST",
      },
    );
  }

  // ── Budgets ──

  async listBudgets(): Promise<Budget[]> {
    return this.request<Budget[]>("/budgets");
  }

  async getBudget(id: string): Promise<Budget> {
    return this.request<Budget>(`/budgets/${id}`);
  }

  async createBudget(data: BudgetCreateRequest): Promise<Budget> {
    return this.request<Budget>("/budgets", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateBudget(id: string, data: BudgetUpdateRequest): Promise<Budget> {
    return this.request<Budget>(`/budgets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteBudget(id: string): Promise<void> {
    return this.request<void>(`/budgets/${id}`, {
      method: "DELETE",
    });
  }

  // ── Tax ──

  async estimateTax(
    total_income: number,
    custom_allowance?: number,
  ): Promise<TaxCalculation> {
    return this.request<TaxCalculation>("/tax/estimate", {
      method: "POST",
      body: JSON.stringify({
        total_income,
        custom_allowance: custom_allowance ?? null,
      }),
    });
  }

  async listTaxCalculations(): Promise<TaxCalculation[]> {
    return this.request<TaxCalculation[]>("/tax/calculations");
  }

  async getTaxCalculation(id: string): Promise<TaxCalculation> {
    return this.request<TaxCalculation>(`/tax/calculations/${id}`);
  }

  // ── Reports ──

  async generateReport(
    report_type: ReportType,
    period_start: string,
    period_end: string,
  ): Promise<ReportDetail> {
    return this.request<ReportDetail>("/reports/generate", {
      method: "POST",
      body: JSON.stringify({ report_type, period_start, period_end }),
    });
  }

  async listReports(): Promise<Report[]> {
    return this.request<Report[]>("/reports");
  }

  async getReport(id: string): Promise<Report> {
    return this.request<Report>(`/reports/${id}`);
  }

  // ── Assistant ──

  async chatWithAssistant(message: string): Promise<{ response: string }> {
    return this.request<{ response: string }>("/assistant/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  }

  // ── Categories ──

  async listCategories(): Promise<Category[]> {
    return this.request<Category[]>("/categories");
  }
}

export const apiClient = new ApiClient();
export default apiClient;
