import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  ParseOpenAPIResponse,
  RunTestRequest,
  RunTestResponse,
  WorkflowStatus,
} from "@/lib/types";

export function useParseOpenAPI() {
  const queryClient = useQueryClient();

  return useMutation<ParseOpenAPIResponse, Error, FormData>({
    mutationFn: async (formData) => {
      const { data } = await api.post<ParseOpenAPIResponse>("/workflows/parse-openapi", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["endpoints"] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useRunTest() {
  const queryClient = useQueryClient();

  return useMutation<RunTestResponse, Error, RunTestRequest>({
    mutationFn: async (payload) => {
      const { data } = await api.post<RunTestResponse>("/workflows/run-test", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["test-runs"] });
    },
  });
}

export function useWorkflowStatus(runId: string | number, enabled: boolean) {
  return useQuery<WorkflowStatus>({
    queryKey: ["workflow-status", runId],
    queryFn: async () => {
      const { data } = await api.get<WorkflowStatus>(`/workflows/status/${runId}`);
      return data;
    },
    enabled: enabled && !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "running" || status === "pending") {
        return 2000;
      }
      return false;
    },
  });
}
