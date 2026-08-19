import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "../api/client";
import { getStoredToken } from "../contexts/AuthContext";
import type {
  Account,
  Budget,
  Report,
  TransactionFilters,
  TransactionListResponse,
  TaxCalculation,
} from "../types/api";

interface UseQueryResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function useQuery<T>(fetcher: () => Promise<T>, deps: unknown[]): UseQueryResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);
  const mountedRef = useRef(true);

  const refetch = useCallback(() => {
    setTrigger((prev) => prev + 1);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    async function run() {
      if (!getStoredToken()) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const result = await fetcher();
        if (!cancelled && mountedRef.current) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled && mountedRef.current) {
          setError(err instanceof Error ? err.message : "An error occurred");
        }
      } finally {
        if (!cancelled && mountedRef.current) {
          setLoading(false);
        }
      }
    }

    run();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, trigger]);

  return { data, loading, error, refetch };
}

export function useAccounts(): UseQueryResult<Account[]> {
  return useQuery(() => apiClient.listAccounts(), []);
}

export function useTransactions(
  accountId: string | null,
  filters: TransactionFilters = {},
): UseQueryResult<TransactionListResponse> {
  return useQuery(
    () => {
      if (!accountId) {
        return Promise.resolve({ transactions: [], total_count: 0 });
      }
      return apiClient.listTransactions(accountId, filters);
    },
    [accountId, JSON.stringify(filters)],
  );
}

export function useBudgets(): UseQueryResult<Budget[]> {
  return useQuery(() => apiClient.listBudgets(), []);
}

export function useTaxCalculations(): UseQueryResult<TaxCalculation[]> {
  return useQuery(() => apiClient.listTaxCalculations(), []);
}

export function useReports(): UseQueryResult<Report[]> {
  return useQuery(() => apiClient.listReports(), []);
}
