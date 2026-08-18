import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { ParseOpenAPIResponse, UploadOpenAPIResponse, WorkflowStatus } from "@/lib/types";

export function useParseOpenAPI() {
  const queryClient = useQueryClient();

  return useMutation<ParseOpenAPIResponse, Error, FormData>({
    mutationFn: async (formData) => {
      const { data } = await api.post<ParseOpenAPIResponse>("/workflows/parse/openapi", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["endpoints"] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      toast.success(data.message || "文档解析成功");
    },
    onError: (error) => {
      toast.error(error.message || "文档解析失败");
    },
  });
}

export function useUploadOpenAPI() {
  return useMutation<UploadOpenAPIResponse, Error, FormData>({
    mutationFn: async (formData) => {
      const { data } = await api.post<UploadOpenAPIResponse>(
        "/workflows/upload/openapi",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );
      return data;
    },
    onError: (error) => {
      toast.error(error.message || "文档上传失败");
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
