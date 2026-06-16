import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Environment, EnvironmentListResponse } from "@/lib/types";

interface UseEnvironmentsParams {
  project_id?: string | number;
  keyword?: string;
  page?: number;
  page_size?: number;
}

export function useEnvironments(params?: UseEnvironmentsParams) {
  return useQuery<EnvironmentListResponse>({
    queryKey: ["environments", params],
    queryFn: async () => {
      const { data } = await api.get<EnvironmentListResponse>("/environments/", { params });
      return data;
    },
  });
}

export function useCreateEnvironment() {
  const queryClient = useQueryClient();

  return useMutation<Environment, Error, Partial<Environment>>({
    mutationFn: async (payload) => {
      const { data } = await api.post<Environment>("/environments/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["environments"] });
    },
  });
}

export function useDeleteEnvironment() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string | number>({
    mutationFn: async (id) => {
      await api.delete(`/environments/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["environments"] });
    },
  });
}
