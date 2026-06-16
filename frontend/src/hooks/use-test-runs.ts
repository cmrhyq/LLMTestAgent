import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { TestRunListResponse, TestRunDetail } from "@/lib/types";

interface UseTestRunsParams {
  project_id?: string | number;
  status?: string;
  page?: number;
  page_size?: number;
}

export function useTestRuns(params?: UseTestRunsParams) {
  return useQuery<TestRunListResponse>({
    queryKey: ["test-runs", params],
    queryFn: async () => {
      const { data } = await api.get<TestRunListResponse>("/test/runs/", {
        params,
      });
      return data;
    },
  });
}

export function useTestRunDetail(id: string | number) {
  return useQuery<TestRunDetail>({
    queryKey: ["test-runs", id],
    queryFn: async () => {
      const { data } = await api.get<TestRunDetail>(`/test/runs/${id}`);
      return data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "running" || status === "pending") {
        return 3000;
      }
      return false;
    },
  });
}
