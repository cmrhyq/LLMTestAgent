import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import api from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { ParseOpenAPIResponse } from "@/lib/types";

/** 上传并解析 OpenAPI 文档，把接口定义写入数据库。 */
export function useParseOpenAPI(space_id: number) {
  const queryClient = useQueryClient();

  return useMutation<ParseOpenAPIResponse, Error, FormData>({
    mutationFn: async (formData) => {
      const { data } = await api.post<ParseOpenAPIResponse>(
        `/spaces/parse/openapi/${space_id}`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.endpoints.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.spaces.all });
      toast.success(data.message || "文档解析成功");
    },
    onError: (error) => {
      toast.error(error.message || "文档解析失败");
    },
  });
}
