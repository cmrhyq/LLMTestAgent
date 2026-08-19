import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { ParseOpenAPIResponse, UploadOpenAPIResponse } from "@/lib/types";

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
      queryClient.invalidateQueries({ queryKey: queryKeys.endpoints.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
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
