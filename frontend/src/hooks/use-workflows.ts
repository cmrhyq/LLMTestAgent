import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { UploadOpenAPIResponse } from "@/lib/types";
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
